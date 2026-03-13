# Campus Planner Agent Demo

一个零依赖的本地 demo，按 PRD 实现了：

- `POST /api/v1/agent/plan_itinerary` mock Agent 接口
- 左图右文的 Web 前端
- 课表冲突、办公时间窗、路线可视化与时间轴联动

## Run

```bash
python3 -m backend.server
```

然后打开 [http://127.0.0.1:8000](http://127.0.0.1:8000)。

## Test

```bash
python3 -m unittest discover -s tests
```
