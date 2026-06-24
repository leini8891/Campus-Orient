const form = document.getElementById("planner-form");
const notesInput = document.getElementById("notes-input");
const dateInput = document.getElementById("date-input");
const statusChip = document.getElementById("status-chip");
const summaryHeadline = document.getElementById("summary-headline");
const summarySubheadline = document.getElementById("summary-subheadline");
const summaryBadge = document.getElementById("summary-badge");
const nextStepTitle = document.getElementById("next-step-title");
const nextStepMeta = document.getElementById("next-step-meta");
const finishTime = document.getElementById("finish-time");
const finishMeta = document.getElementById("finish-meta");
const deadlineTitle = document.getElementById("deadline-title");
const deadlineNote = document.getElementById("deadline-note");
const alertsContainer = document.getElementById("alerts");
const timelineContainer = document.getElementById("timeline");
const timelineCount = document.getElementById("timeline-count");
const timelineToggle = document.getElementById("timeline-toggle");
const skillsList = document.getElementById("skills-list");
const knowledgeList = document.getElementById("knowledge-list");
const materialScore = document.getElementById("material-score");
const materialPrimaryHeading = document.getElementById("material-primary-heading");
const materialSecondaryHeading = document.getElementById("material-secondary-heading");
const materialReadyList = document.getElementById("material-ready-list");
const materialMissingList = document.getElementById("material-missing-list");
const materialNote = document.getElementById("material-note");
const fallbackTitle = document.getElementById("fallback-title");
const fallbackCopy = document.getElementById("fallback-copy");
const fallbackPreview = document.getElementById("fallback-preview");
const fallbackList = document.getElementById("fallback-list");
const thoughtProcess = document.getElementById("thought-process");
const mapCaption = document.getElementById("map-caption");
const routeLayer = document.getElementById("route-layer");
const nodeLayer = document.getElementById("node-layer");
const intentOptions = [...document.querySelectorAll("[data-query]")];
const presetButtons = [...document.querySelectorAll("[data-preset]")];
const calendarUploadInput = document.getElementById("calendar-upload");
const knowledgeUploadInput = document.getElementById("knowledge-upload");
const calendarStatus = document.getElementById("calendar-status");
const knowledgeStatus = document.getElementById("knowledge-status");
const syncCards = document.getElementById("sync-cards");
const syncSummary = document.getElementById("sync-summary");
const googleSyncButton = document.getElementById("google-sync-button");
const icsExportButton = document.getElementById("ics-export-button");
const materialsCount = document.getElementById("materials-count");
const materialsFillCoreButton = document.getElementById("materials-fill-core");
const materialsClearButton = document.getElementById("materials-clear");
const materialInputs = [...document.querySelectorAll('input[name="available_materials"]')];
const coreMaterialInputs = materialInputs.filter((input) => input.dataset.group === "core");
window.__plannerStartId = "blk365_singapore";
window.__plannerEndId = "kent_ridge_hall";
window.__syncCandidates = [];
window.__selectedIntentQuery = intentOptions[0]?.dataset.query || "";
window.__lastTimeline = [];
window.__timelineExpanded = false;
window.__selectedPreset = "standard_day";

const DEMO_PRESETS = {
  standard_day: {
    query: "我今天要办理宿舍入住，看看今天能不能办完",
    current_location: "blk365_singapore",
    current_time: "09:40",
    date: "2026-03-13",
    notes: "",
    materials: [],
  },
  late_arrival: {
    query: "我今天要办理宿舍入住，看看今天能不能办完",
    current_location: "blk365_singapore",
    current_time: "12:20",
    date: "2026-03-13",
    notes: "我中午才到学校，想知道今天还赶不赶得上。",
    materials: [],
  },
  core_materials_ready: {
    query: "我今天要办理宿舍入住，帮我检查缺哪些材料会卡住",
    current_location: "blk365_singapore",
    current_time: "09:40",
    date: "2026-03-13",
    notes: "我想先确认第一步能不能直接开始。",
    materials: [
      "录取通知书",
      "护照或身份证件",
      "住宿预约邮件",
      "临时学生证",
      "手机号码",
      "住宿确认邮件",
    ],
  },
};

function setStatus(label, tone) {
  statusChip.textContent = label;
  statusChip.className = `status-chip ${tone}`;
}

function setSummaryBadge(label, tone) {
  summaryBadge.textContent = label;
  summaryBadge.className = `summary-badge ${tone}`;
}

function activateIntent(option) {
  intentOptions.forEach((item) => item.classList.remove("active"));
  option.classList.add("active");
  window.__selectedIntentQuery = option.dataset.query || "";
}

function activateIntentByQuery(query) {
  const matched = intentOptions.find((option) => option.dataset.query === query);
  if (matched) {
    activateIntent(matched);
  } else if (intentOptions[0]) {
    activateIntent(intentOptions[0]);
  }
}

function collectSelectedMaterials() {
  return materialInputs.filter((input) => input.checked).map((input) => input.value);
}

function setSelectedMaterials(values) {
  const selected = new Set(values);
  materialInputs.forEach((input) => {
    input.checked = selected.has(input.value);
  });
  updateMaterialsSelectionState();
}

function updateMaterialsSelectionState() {
  const selectedCount = collectSelectedMaterials().length;
  const selectedCoreCount = coreMaterialInputs.filter((input) => input.checked).length;

  if (selectedCount === 0) {
    materialsCount.textContent = "还没勾选";
  } else {
    materialsCount.textContent = `已选 ${selectedCount} 项`;
  }

  materialsFillCoreButton.textContent = selectedCoreCount === coreMaterialInputs.length
    ? "常见 6 项已勾选"
    : "一键勾选常见 6 项";
  materialsClearButton.disabled = selectedCount === 0;
}

function fillCoreMaterials() {
  coreMaterialInputs.forEach((input) => {
    input.checked = true;
  });
  updateMaterialsSelectionState();
}

function clearMaterials() {
  materialInputs.forEach((input) => {
    input.checked = false;
  });
  updateMaterialsSelectionState();
}

function activatePreset(presetKey) {
  presetButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.preset === presetKey);
  });
  window.__selectedPreset = presetKey;
}

function applyPreset(presetKey) {
  const preset = DEMO_PRESETS[presetKey];
  if (!preset) return;
  activatePreset(presetKey);
  document.getElementById("location-input").value = preset.current_location;
  document.getElementById("time-input").value = preset.current_time;
  dateInput.value = preset.date;
  notesInput.value = preset.notes;
  activateIntentByQuery(preset.query);
  setSelectedMaterials(preset.materials);
}

function readFilePayload(file) {
  if (!file) return Promise.resolve(null);
  return file.text().then((content) => ({
    file_name: file.name,
    content,
  }));
}

function updateUploadStatuses() {
  const calendarFile = calendarUploadInput.files[0];
  const knowledgeFiles = [...knowledgeUploadInput.files];
  calendarStatus.textContent = calendarFile
    ? `已上传课表或日程：${calendarFile.name}`
    : "还没上传课表，会继续使用页面里的示例安排。";
  knowledgeStatus.textContent = knowledgeFiles.length
    ? `已上传补充资料：${knowledgeFiles.map((file) => file.name).join(", ")}`
    : "还没上传补充资料，会继续使用内置入住资料。";
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

function syncCalendar(payload) {
  return fetch("/api/v1/calendar/sync", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  }).then((response) => {
    if (!response.ok) {
      throw new Error(`Calendar sync failed with ${response.status}`);
    }
    return response.json();
  });
}

function renderAlerts(alerts) {
  alertsContainer.innerHTML = "";
  if (!alerts.length) {
    const item = document.createElement("div");
    item.className = "alert muted";
    item.textContent = "今天还没有额外提醒。";
    alertsContainer.appendChild(item);
    return;
  }

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

function renderKnowledgeHits(hits) {
  knowledgeList.innerHTML = "";
  if (!hits.length) {
    const item = document.createElement("li");
    item.className = "placeholder-item";
    item.textContent = "当前没有额外证据片段。";
    knowledgeList.appendChild(item);
    return;
  }

  hits.forEach((hit) => {
    const item = document.createElement("li");
    item.textContent = hit.snippet || hit.title || "";
    knowledgeList.appendChild(item);
  });
}

function timelineTypeClass(item) {
  if (item.type === "destination") return "destination";
  if (item.is_fixed) return "fixed";
  return "task";
}

function renderTimeline(timeline) {
  window.__lastTimeline = timeline;
  timelineContainer.innerHTML = "";
  const shouldCondense = timeline.length > 3;
  const visibleTimeline =
    shouldCondense && !window.__timelineExpanded ? timeline.slice(0, 3) : timeline;
  timelineCount.textContent = shouldCondense && !window.__timelineExpanded
    ? `先看 ${visibleTimeline.length} / ${timeline.length} 步`
    : `共 ${timeline.length} 步`;
  timelineToggle.hidden = !shouldCondense;
  timelineToggle.textContent = window.__timelineExpanded ? "收起步骤" : `展开全部 ${timeline.length} 步`;

  if (!timeline.length) {
    timelineToggle.hidden = true;
    const card = document.createElement("article");
    card.className = "timeline-item empty";
    card.innerHTML = `
      <h3 class="timeline-title">还没有可执行方案</h3>
      <p class="timeline-notes">选一个任务后，这里会给出今天的办理顺序和每一步的预计时间。</p>
    `;
    timelineContainer.appendChild(card);
    return;
  }

  visibleTimeline.forEach((item, index) => {
    const card = document.createElement("article");
    card.className = `timeline-item ${timelineTypeClass(item)}`;
    card.style.animationDelay = `${index * 70}ms`;

    const materials = (item.materials || [])
      .map((material) => `<span class="mini-chip">${material}</span>`)
      .join("");
    const readiness = item.material_status_label
      ? `<div class="timeline-readiness ${item.material_status_tone || "pending"}">${item.material_status_label}</div>`
      : "";
    const materialHint = item.missing_materials?.length
      ? `<p class="timeline-warning">还缺：${item.missing_materials.join("、")}</p>`
      : item.ready_materials?.length && item.material_status_tone === "ready"
        ? `<p class="timeline-ok">材料已确认：${item.ready_materials.join("、")}</p>`
        : "";

    const meta = item.window ? `窗口 ${item.window}` : item.is_fixed ? "固定安排" : "灵活办理";
    card.innerHTML = `
      <div class="timeline-head">
        <div class="timeline-time">${item.time_est}</div>
        <div class="timeline-side">
          <div class="timeline-meta">${meta}</div>
          ${readiness}
        </div>
      </div>
      <h3 class="timeline-title">${item.action}</h3>
      <div class="timeline-location">${item.location_name} · 预计结束 ${item.end_time}</div>
      <p class="timeline-notes">${item.notes || ""}</p>
      ${materialHint}
      <div class="chip-row">${materials}</div>
    `;
    timelineContainer.appendChild(card);
  });
}

function renderMaterialItems(target, items, placeholder) {
  target.innerHTML = "";
  if (!items.length) {
    const node = document.createElement("li");
    node.className = "placeholder-item";
    node.textContent = placeholder;
    target.appendChild(node);
    return;
  }

  items.forEach((item) => {
    const node = document.createElement("li");
    if (typeof item === "string") {
      node.textContent = item;
    } else {
      node.textContent = item.label;
      if (item.tone) {
        node.classList.add(item.tone);
      }
    }
    target.appendChild(node);
  });
}

function buildMaterialPreviewItems(materials, availableSet, hasSelection) {
  return materials.map((item) => {
    if (availableSet.has(item)) {
      return { label: `已确认 · ${item}`, tone: "ready" };
    }
    if (hasSelection) {
      return { label: `还没确认 · ${item}`, tone: "pending" };
    }
    return { label: `待确认 · ${item}`, tone: "muted" };
  });
}

function renderMaterialStatus(status, nextStep) {
  materialPrimaryHeading.textContent = "第一步就会用";
  materialSecondaryHeading.textContent = "后面还会用";

  if (!status) {
    materialScore.textContent = "待确认";
    renderMaterialItems(materialReadyList, [], "这里会先显示第一步就要确认的材料");
    renderMaterialItems(materialMissingList, [], "这里会补充后续步骤还会用到的材料");
    materialNote.textContent = "先选一个任务，我会把材料提醒压成更适合出发前确认的样子。";
    return;
  }

  const required = status.required || [];
  if (!required.length) {
    materialScore.textContent = "无需材料";
    renderMaterialItems(materialReadyList, [], "第一步暂时没有额外材料要求");
    renderMaterialItems(materialMissingList, [], "后续步骤也没有明确材料要求");
    materialNote.textContent = "当前任务暂时没有明确材料要求。";
    return;
  }

  const availableSet = new Set(status.available || []);
  const primaryMaterials = nextStep?.materials?.length ? nextStep.materials : required.slice(0, 3);
  const primaryMaterialSet = new Set(primaryMaterials);
  const secondaryMaterials = required.filter((item) => !primaryMaterialSet.has(item));
  const primaryReadyCount = primaryMaterials.filter((item) => availableSet.has(item)).length;
  const primaryMissingCount = primaryMaterials.length - primaryReadyCount;
  const secondaryPreview = secondaryMaterials.slice(0, 4);
  const hiddenSecondaryCount = Math.max(secondaryMaterials.length - secondaryPreview.length, 0);

  materialScore.textContent = primaryMaterials.length
    ? status.has_selection
      ? `${primaryReadyCount}/${primaryMaterials.length} 先就绪`
      : `先看 ${primaryMaterials.length} 项`
    : status.completion_label || "待确认";

  const primaryItems = buildMaterialPreviewItems(primaryMaterials, availableSet, status.has_selection);
  const secondaryItems = buildMaterialPreviewItems(
    secondaryPreview,
    availableSet,
    status.has_selection
  );
  if (hiddenSecondaryCount) {
    secondaryItems.push({
      label: `另外还有 ${hiddenSecondaryCount} 项会在后续步骤用到`,
      tone: "more",
    });
  }
  renderMaterialItems(
    materialReadyList,
    primaryItems,
    "当前还没有识别出第一步的关键材料"
  );
  renderMaterialItems(
    materialMissingList,
    secondaryItems,
    "看起来后续步骤暂时不需要额外材料"
  );

  if (!status.has_selection) {
    materialNote.textContent = `先确认第一步这 ${primaryMaterials.length || required.length} 项，就能判断你现在能不能直接出发。完整流程一共会用到 ${required.length} 项材料。`;
    return;
  }

  if (primaryMissingCount > 0) {
    materialNote.textContent = `第一步还差 ${primaryMissingCount} 项，建议先补齐再出发。完整流程里另外还有 ${secondaryMaterials.length} 项会在后面陆续用到。`;
    return;
  }

  if (secondaryMaterials.length) {
    materialNote.textContent = `第一步材料已经齐了，可以先出发。后面还有 ${secondaryMaterials.length} 项会在后续节点用到。`;
    return;
  }

  materialNote.textContent = "关键材料已经齐了，你现在可以直接出发。";
}

function renderFallback(view, response) {
  fallbackPreview.innerHTML = "";
  fallbackList.innerHTML = "";

  if (response.status === "blocked" && view.recovery_plan) {
    fallbackTitle.textContent = "下一套可执行方案";
    fallbackCopy.textContent = view.recovery_plan.headline;
    (view.recovery_plan.timeline_preview || []).forEach((step) => {
      const item = document.createElement("article");
      item.className = "preview-step";
      const readiness = step.material_status_label
        ? `<span class="preview-badge ${step.material_status_tone || "pending"}">${step.material_status_label}</span>`
        : "";
      const warning = step.missing_materials?.length
        ? `<div class="preview-warning">还缺：${step.missing_materials.join("、")}</div>`
        : "";
      item.innerHTML = `
        <div class="preview-time">${step.time_est}</div>
        <div class="preview-main">
          <div class="preview-title-row">
            <h3>${step.action}</h3>
            ${readiness}
          </div>
          <div class="preview-meta">${step.location_name} · 预计结束 ${step.end_time}</div>
          ${warning}
        </div>
      `;
      fallbackPreview.appendChild(item);
    });
    [
      `建议日期：${view.recovery_plan.date}`,
      `建议开始时间：${view.recovery_plan.display_start_time}`,
      `第一步：${view.recovery_plan.first_action_time} 去 ${view.recovery_plan.first_location_name} 办理 ${view.recovery_plan.first_action}`,
      `预计完成：${view.recovery_plan.finish_time}`,
    ].forEach((item) => {
      const node = document.createElement("li");
      node.textContent = item;
      fallbackList.appendChild(node);
    });
    return;
  }

  if (response.status === "blocked") {
    fallbackTitle.textContent = "今天先别硬冲";
    fallbackCopy.textContent = "当前条件下没有更稳的替代方案，建议换日期或补充更多限制后再重算。";
    return;
  }

  fallbackTitle.textContent = "如果中途卡住";
  if (view.material_status?.has_selection && view.material_status.missing?.length) {
    fallbackCopy.textContent = "路线本身能走通，但你还缺关键材料。先补齐下面这些，再按时间线出发会更稳。";
    view.material_status.missing.forEach((item) => {
      const node = document.createElement("li");
      node.textContent = `先补齐：${item}`;
      fallbackList.appendChild(node);
    });
    return;
  }

  fallbackCopy.textContent = "今天这套方案已经能走通。如果中途被课程或别的安排打断，再回来重算即可。";
  (response.alerts || []).slice(0, 2).forEach((item) => {
    const node = document.createElement("li");
    node.textContent = item;
    fallbackList.appendChild(node);
  });
}

function renderSummary(view, response) {
  summaryHeadline.textContent = view.headline || "先选一个常见任务";
  summarySubheadline.textContent =
    view.subheadline || "系统会告诉你今天能不能办完，以及现在先去哪。";
  finishTime.textContent = view.finish_time || "--:--";
  finishMeta.textContent = view.finish_note || "还没有今天的办理结果。";
  deadlineTitle.textContent = view.deadline_title || "关键提醒";
  deadlineNote.textContent = view.constraint_note || "先生成一条方案再看。";

  if (view.next_step) {
    nextStepTitle.textContent = view.next_step.action;
    const readiness = view.next_step.material_status_label
      ? ` · ${view.next_step.material_status_label}`
      : "";
    nextStepMeta.textContent = `${view.next_step.time_est} · ${view.next_step.location_name} · 预计结束 ${view.next_step.end_time}${readiness}`;
  } else {
    nextStepTitle.textContent = "等待规划";
    nextStepMeta.textContent = "生成后会告诉你下一步地点和时间。";
  }

  if (response.status === "success") {
    setSummaryBadge(view.badge || "今天办得完", "success");
  } else if (response.status === "blocked") {
    setSummaryBadge(view.badge || "建议改期", "blocked");
  } else if (response.status === "needs_input") {
    setSummaryBadge(view.badge || "等待任务", "idle");
  } else {
    setSummaryBadge("请求失败", "error");
  }
}

function renderSyncCards(candidates) {
  window.__syncCandidates = candidates;
  syncCards.innerHTML = "";

  if (!candidates.length) {
    const card = document.createElement("article");
    card.className = "sync-card";
    card.innerHTML = `
      <h3>这条路线暂时不用额外提醒</h3>
      <div class="sync-meta">当前规划没有需要单独加入日历的灵活节点，或者这些节点已经是固定安排。</div>
    `;
    syncCards.appendChild(card);
    googleSyncButton.disabled = true;
    icsExportButton.disabled = true;
    return;
  }

  candidates.forEach((candidate) => {
    const card = document.createElement("article");
    card.className = "sync-card";
    card.innerHTML = `
      <h3>${candidate.event_title}</h3>
      <div class="sync-meta">${candidate.date} ${candidate.start_time}-${candidate.end_time}</div>
      <div class="sync-meta">${candidate.location || "N/A"}</div>
    `;
    syncCards.appendChild(card);
  });

  googleSyncButton.disabled = false;
  icsExportButton.disabled = false;
}

function renderSyncSummary(result) {
  if (!result) {
    syncSummary.textContent = "如果你想把灵活节点变成提醒，可以导出 ICS 或同步到 Google Calendar。";
    return;
  }

  const synced = (result.synced_events || []).length;
  const failed = (result.failed_events || []).length;
  const skipped = (result.skipped_events || []).length;
  const reasons = (result.reasons || []).join(" | ");
  syncSummary.textContent = `成功 ${synced} 项，跳过 ${skipped} 项，失败 ${failed} 项。${reasons || ""} ${result.suggested_next_action || ""}`.trim();
}

function buildNodeType(locationId, timeline) {
  if (locationId === window.__plannerStartId) return "start";
  if (locationId === window.__plannerEndId) return "end";

  const entry = timeline.find((item) => item.location_id === locationId);
  if (!entry) return "task";
  return entry.is_fixed ? "fixed" : "task";
}

function renderMap(response) {
  const { location_catalog: catalog, route_paths: paths, timeline } = response;
  if (!catalog || Object.keys(catalog).length === 0) {
    routeLayer.innerHTML = "";
    nodeLayer.innerHTML = "";
    mapCaption.textContent = "生成后会在这里显示路线预览。";
    return;
  }

  routeLayer.innerHTML = "";
  nodeLayer.innerHTML = "";
  window.__plannerStartId = response.start_location || response.current_location;
  window.__plannerEndId =
    response.destination_location || timeline[timeline.length - 1]?.location_id || window.__plannerStartId;

  paths.forEach((path) => {
    const from = catalog[path.from];
    const to = catalog[path.to];
    if (!from || !to) return;
    const curveX = (from.x + to.x) / 2;
    const curveY = Math.min(from.y, to.y) - 6;
    const segment = document.createElementNS("http://www.w3.org/2000/svg", "path");
    segment.setAttribute("d", `M ${from.x} ${from.y} Q ${curveX} ${curveY} ${to.x} ${to.y}`);
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

  const startId = window.__plannerStartId;
  const endId = window.__plannerEndId;
  const endTime = timeline[timeline.length - 1]?.end_time || "--:--";
  if (!paths.length || !catalog[startId] || !catalog[endId]) {
    mapCaption.textContent = "当前还没有可渲染的路线。";
    return;
  }
  mapCaption.textContent = `路线预览：从 ${catalog[startId].short_name} 出发，预计 ${endTime} 抵达 ${catalog[endId].short_name}。`;
}

function renderResponse(response) {
  const view = response.product_view || {};
  window.__timelineExpanded = false;
  renderSummary(view, response);
  renderAlerts(response.alerts || []);
  renderTimeline(response.timeline || []);
  renderMaterialStatus(view.material_status || null, view.next_step || null);
  renderFallback(view, response);
  renderSyncCards(response.calendar_sync_candidates || []);
  renderSyncSummary(null);
  thoughtProcess.textContent = response.agent_thought_process
    || "如果你觉得路线不对，这里会解释系统为什么这么安排今天的顺序。";
  renderKnowledgeHits(response.knowledge_hits || []);
  renderSkills(response.skills_used || []);
  renderMap(response);

  if (response.status === "success") {
    setStatus("方案已生成", "success");
  } else if (response.status === "blocked") {
    setStatus("建议改期", "blocked");
  } else if (response.status === "needs_input") {
    setStatus("等你补充", "ready");
  } else {
    setStatus("请求失败", "error");
  }
}

async function handleCalendarAction(provider) {
  if (!window.__syncCandidates.length) {
    return;
  }

  const actionLabel = provider === "google" ? "同步中" : "导出中";
  setStatus(actionLabel, "loading");
  syncSummary.textContent = provider === "google"
    ? "准备同步到 Google Calendar..."
    : "正在导出 ICS 文件...";

  try {
    const result = await syncCalendar({
      provider,
      events: window.__syncCandidates,
    });
    renderSyncSummary(result);
    if (result.status === "success") {
      setStatus(provider === "google" ? "已同步" : "ICS 已导出", "success");
    } else if (result.status === "partial") {
      setStatus("部分成功", "blocked");
    } else {
      setStatus("同步失败", "error");
    }
  } catch (error) {
    console.error(error);
    setStatus("同步失败", "error");
    syncSummary.textContent = "无法完成日历操作，请检查本地服务和凭据后重试。";
  }
}

async function submitPlan(event) {
  if (event) {
    event.preventDefault();
  }

  const [calendarUpload, knowledgeUploads] = await Promise.all([
    readFilePayload(calendarUploadInput.files[0]),
    Promise.all([...knowledgeUploadInput.files].map((file) => readFilePayload(file))),
  ]);

  const noteText = notesInput.value.trim();
  const baseQuery = window.__selectedIntentQuery || "我今天要办理宿舍入住，看看今天能不能办完";
  const payload = {
    user_id: "student_001",
    query: noteText ? `${baseQuery}。补充说明：${noteText}` : baseQuery,
    current_location: document.getElementById("location-input").value,
    current_time: document.getElementById("time-input").value,
    date: dateInput.value,
    available_materials: collectSelectedMaterials(),
  };

  if (calendarUpload) payload.calendar_upload = calendarUpload;
  if (knowledgeUploads.length) payload.knowledge_uploads = knowledgeUploads.filter(Boolean);

  setStatus("计算中", "loading");
  summaryHeadline.textContent = "正在判断今天能不能顺利办完";
  summarySubheadline.textContent = "我在检查时间窗、固定安排，还有你已经勾选的材料。";

  try {
    const response = await fetchPlan(payload);
    renderResponse(response);
  } catch (error) {
    console.error(error);
    setStatus("请求失败", "error");
    setSummaryBadge("请求失败", "error");
    summaryHeadline.textContent = "本地服务暂时不可用";
    summarySubheadline.textContent = "请确认本地后端已经启动，然后重试。";
    renderAlerts(["当前无法连接本地规划服务。"]);
  }
}

intentOptions.forEach((option) => {
  option.addEventListener("click", () => {
    activateIntent(option);
    submitPlan();
  });
});
presetButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const presetKey = button.dataset.preset;
    applyPreset(presetKey);
    submitPlan();
  });
});

form.addEventListener("submit", submitPlan);
calendarUploadInput.addEventListener("change", updateUploadStatuses);
knowledgeUploadInput.addEventListener("change", updateUploadStatuses);
googleSyncButton.addEventListener("click", () => handleCalendarAction("google"));
icsExportButton.addEventListener("click", () => handleCalendarAction("ics"));
timelineToggle.addEventListener("click", () => {
  window.__timelineExpanded = !window.__timelineExpanded;
  renderTimeline(window.__lastTimeline || []);
});
materialsFillCoreButton.addEventListener("click", fillCoreMaterials);
materialsClearButton.addEventListener("click", clearMaterials);
materialInputs.forEach((input) => {
  input.addEventListener("change", updateMaterialsSelectionState);
});

window.addEventListener("load", () => {
  applyPreset(window.__selectedPreset);
  setStatus("已就绪", "ready");
  updateUploadStatuses();
  googleSyncButton.disabled = true;
  icsExportButton.disabled = true;
  submitPlan();
});
