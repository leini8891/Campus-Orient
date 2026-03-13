const form = document.getElementById("planner-form");
const statusChip = document.getElementById("status-chip");
const thoughtProcess = document.getElementById("thought-process");
const alertsContainer = document.getElementById("alerts");
const timelineContainer = document.getElementById("timeline");
const timelineCount = document.getElementById("timeline-count");
const skillsList = document.getElementById("skills-list");
const materialsList = document.getElementById("materials-list");
const mapCaption = document.getElementById("map-caption");
const routeLayer = document.getElementById("route-layer");
const nodeLayer = document.getElementById("node-layer");

function setStatus(label, tone) {
  statusChip.textContent = label;
  statusChip.className = `status-chip ${tone}`;
}

function fetchPlan(payload) {
  return fetch("/api/v1/agent/plan_itinerary", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  }).then((response) => {
    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }
    return response.json();
  });
}

function renderAlerts(alerts) {
  alertsContainer.innerHTML = "";
  alerts.forEach((alert) => {
    const item = document.createElement("div");
    item.className = "alert";
    item.textContent = alert;
    alertsContainer.appendChild(item);
  });
}

function renderSkills(skills) {
  skillsList.innerHTML = "";
  skills.forEach((skill) => {
    const item = document.createElement("li");
    item.textContent = skill;
    skillsList.appendChild(item);
  });
}

function renderMaterials(timeline) {
  const uniqueMaterials = new Set();
  timeline.forEach((item) => {
    (item.materials || []).forEach((material) => uniqueMaterials.add(material));
  });

  materialsList.innerHTML = "";
  [...uniqueMaterials].forEach((material) => {
    const item = document.createElement("li");
    item.textContent = material;
    materialsList.appendChild(item);
  });
}

function timelineTypeClass(item) {
  if (item.type === "destination") return "destination";
  if (item.is_fixed) return "fixed";
  return "task";
}

function renderTimeline(timeline) {
  timelineContainer.innerHTML = "";
  timelineCount.textContent = `${timeline.length} steps`;

  timeline.forEach((item, index) => {
    const card = document.createElement("article");
    card.className = `timeline-item ${timelineTypeClass(item)}`;
    card.style.animationDelay = `${index * 80}ms`;

    const materials = (item.materials || [])
      .map((material) => `<span class="mini-chip">${material}</span>`)
      .join("");

    const meta = item.window ? `窗口 ${item.window}` : item.is_fixed ? "固定日程" : "灵活办理";
    card.innerHTML = `
      <div class="timeline-head">
        <div class="timeline-time">${item.time_est}</div>
        <div class="timeline-meta">${meta}</div>
      </div>
      <h3 class="timeline-title">${item.action}</h3>
      <div class="timeline-location">${item.location_name} · 预计结束 ${item.end_time}</div>
      <p class="timeline-notes">${item.notes || ""}</p>
      <div class="chip-row">${materials}</div>
    `;
    timelineContainer.appendChild(card);
  });
}

function buildNodeType(locationId, timeline) {
  if (locationId === "blk365_singapore") return "start";
  if (locationId === "kent_ridge_hall") return "end";

  const entry = timeline.find((item) => item.location_id === locationId);
  if (!entry) return "task";
  return entry.is_fixed ? "fixed" : "task";
}

function renderMap(response) {
  const { location_catalog: catalog, route_paths: paths, timeline } = response;
  routeLayer.innerHTML = "";
  nodeLayer.innerHTML = "";

  paths.forEach((path) => {
    const from = catalog[path.from];
    const to = catalog[path.to];
    const curveX = (from.x + to.x) / 2;
    const curveY = Math.min(from.y, to.y) - 6;
    const segment = document.createElementNS("http://www.w3.org/2000/svg", "path");
    segment.setAttribute(
      "d",
      `M ${from.x} ${from.y} Q ${curveX} ${curveY} ${to.x} ${to.y}`
    );
    segment.setAttribute("class", "route-segment");
    routeLayer.appendChild(segment);
  });

  Object.values(catalog).forEach((location) => {
    const type = buildNodeType(location.id, timeline);
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", location.x);
    circle.setAttribute("cy", location.y);
    circle.setAttribute("r", "2.3");
    circle.setAttribute("class", `node-dot ${type}`);
    nodeLayer.appendChild(circle);

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", location.x + 2.8);
    label.setAttribute("y", location.y - 2.6);
    label.setAttribute("class", "node-label");
    label.textContent = location.short_name;
    nodeLayer.appendChild(label);
  });

  const startId = response.current_location || "blk365_singapore";
  const finishTime = timeline[timeline.length - 1]?.time_est || "--:--";
  mapCaption.textContent = `路线已更新：从 ${catalog[startId].short_name} 出发，预计 ${finishTime} 抵达 ${catalog.kent_ridge_hall.short_name}。`;
}

function renderResponse(response) {
  thoughtProcess.textContent = response.agent_thought_process;
  renderAlerts(response.alerts || []);
  renderTimeline(response.timeline || []);
  renderSkills(response.skills_used || []);
  renderMaterials(response.timeline || []);
  renderMap(response);

  if (response.status === "success") {
    setStatus("Plan Ready", "success");
  } else if (response.status === "blocked") {
    setStatus("Blocked", "blocked");
  } else {
    setStatus("Error", "error");
  }
}

async function submitPlan(event) {
  if (event) {
    event.preventDefault();
  }

  const payload = {
    user_id: "student_001",
    query: document.getElementById("query-input").value.trim(),
    current_location: document.getElementById("location-input").value,
    current_time: document.getElementById("time-input").value,
  };

  setStatus("Thinking...", "loading");
  thoughtProcess.textContent = "Agent 正在读取课表、比对部门窗口，并计算最顺路的办理顺序。";

  try {
    const response = await fetchPlan(payload);
    renderResponse(response);
  } catch (error) {
    console.error(error);
    setStatus("Request Failed", "error");
    thoughtProcess.textContent = "本地 Agent 请求失败，请检查服务是否已启动。";
    renderAlerts(["当前无法连接本地规划服务。"]);
  }
}

form.addEventListener("submit", submitPlan);
window.addEventListener("load", () => {
  setStatus("Ready", "ready");
  submitPlan();
});
