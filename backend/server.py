from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from backend.calendar_sync import sync_calendar_events
from backend.planner import plan_itinerary


ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"


class AgentHandler(BaseHTTPRequestHandler):
    server_version = "StudentAssistant/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/v1/health":
            self._send_json({"status": "ok"})
            return

        if parsed.path == "/":
            self._serve_file(STATIC_DIR / "index.html")
            return

        if parsed.path.startswith("/static/"):
            relative = parsed.path.removeprefix("/static/")
            target = (STATIC_DIR / relative).resolve()
            if STATIC_DIR not in target.parents and target != STATIC_DIR:
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            self._serve_file(target)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/v1/agent/plan_itinerary", "/api/v1/calendar/sync"}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(
                {"status": "error", "message": "Invalid JSON body."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        if parsed.path == "/api/v1/agent/plan_itinerary":
            response = plan_itinerary(payload)
        else:
            response = sync_calendar_events(
                events=payload.get("events", []),
                provider=payload.get("provider", "google"),
                output_dir=payload.get("output_dir"),
            )
        self._send_json(response)

    def log_message(self, format: str, *args: object) -> None:
        del format, args

    def _serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type, _ = mimetypes.guess_type(path.name)
        content_type = content_type or "application/octet-stream"
        data = path.read_bytes()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), AgentHandler)
    print(f"Serving Student Assistant on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
