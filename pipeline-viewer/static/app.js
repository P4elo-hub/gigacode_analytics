/* global cytoscape */

const STORAGE_KEY = "pipeline-viewer-selection";
const DISMISS_STORAGE_KEY = "pipeline-viewer-dismissed";
const DRAFT_STORAGE_KEY = "pipeline-viewer-schema-draft";
const SCHEMA_API_VERSION = 6;
const SCHEMA_CLIS = ["qwen", "gigacode", "opencode"];
const PALETTE_DRAG_TYPE = "application/x-pipeline-agent";

const TIMING_STEP_COLORS = {
  "find-context": "#38bdf8",
  "write-feature": "#22c55e",
  "check-feature": "#a855f7",
  "resolve-gaps": "#f59e0b",
  "challenge-feature": "#ec4899",
  "resolve-challenges": "#f472b6",
  "check-feature-code": "#6366f1",
  "resolve-code-alignment": "#818cf8",
  "orchestrator-idle": "#64748b",
};

const RESULT_COLORS = {
  ok: "#22c55e",
  fail: "#ef4444",
  retry: "#eab308",
  active: "#3b82f6",
  pending: "#94a3b8",
  skipped: "#64748b",
  redo: "#e879f9",
  stale: "#57534e",
};

const ROUTING_STEP = "analyze-routing";
const ROUTING_SATELLITE_DY = 50;
const ROUTING_SAT_COLOR = "#4338ca";

const PACK_NODE_COLORS = {
  orchestrator: "#2563eb",
  step: "#475569",
  terminal: "#15803d",
  meta: "#64748b",
  cycle: "#0f766e",
};

const PACK_EDGE_COLORS = {
  main: "#94a3b8",
  branch: "#64748b",
  loop: "#6366f1",
};

function isRoutingStep(step) {
  return step === ROUTING_STEP;
}

function routingSatelliteId(hostStep) {
  return `routing-after-${hostStep}`;
}

function lastDomainStepBefore(timeline, index) {
  for (let i = index - 1; i >= 0; i -= 1) {
    if (!isRoutingStep(timeline[i]?.step)) {
      return timeline[i].step || "spec-orchestrator";
    }
  }
  return "spec-orchestrator";
}

function routingBurstsByHost(timeline) {
  const byHost = {};
  const rows = timeline || [];
  let i = 0;
  while (i < rows.length) {
    if (!isRoutingStep(rows[i].step)) {
      i += 1;
      continue;
    }
    const host = lastDomainStepBefore(rows, i);
    let last = rows[i];
    let visitRows = 0;
    while (i < rows.length && isRoutingStep(rows[i].step)) {
      last = rows[i];
      visitRows += 1;
      i += 1;
    }
    const prev = byHost[host] || { bursts: 0, visitRows: 0, last: null };
    prev.bursts += 1;
    prev.visitRows += visitRows;
    prev.last = last;
    byHost[host] = prev;
  }
  return byHost;
}

function routingLiveHost(data) {
  const current = data?.current;
  const next = data?.dispatch?.next_step || data?.divergence?.summary?.expected_step;
  if (current?.step !== ROUTING_STEP && next !== ROUTING_STEP) return null;
  const timeline = data?.timeline || [];
  for (let i = timeline.length - 1; i >= 0; i -= 1) {
    if (!isRoutingStep(timeline[i].step)) return timeline[i].step;
  }
  return "spec-orchestrator";
}

function satelliteVisual(host, data, burst, liveHost) {
  const running =
    data?.current?.status === "running" &&
    data?.current?.step === ROUTING_STEP &&
    liveHost === host;
  if (running) {
    return { state: "active", color: RESULT_COLORS.active, label: "analyze-routing" };
  }
  const expected =
    (data?.dispatch?.next_step || data?.divergence?.summary?.expected_step) ===
      ROUTING_STEP && liveHost === host;
  if (expected && data?.current?.status !== "running") {
    return { state: "next", color: ROUTING_SAT_COLOR, label: "analyze-routing" };
  }
  if (burst?.last) {
    const state = burst.last.result || "ok";
    const extra = burst.bursts > 1 ? `\n×${burst.bursts}` : "";
    return {
      state,
      color: RESULT_COLORS[state] || ROUTING_SAT_COLOR,
      label: `analyze-routing${extra}`,
    };
  }
  return { state: "pending", color: ROUTING_SAT_COLOR, label: "analyze-routing" };
}

function loadDismissedNotices() {
  try {
    const raw = sessionStorage.getItem(DISMISS_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

const state = {
  slug: "",
  pipeline: "spec",
  graphView: "target",
  staleCollapsed: true,
  screenMode: "run",
  packId: "spec",
  source: null,
  graph: null,
  pack: null,
  packBase: null,
  catalogPipelines: [],
  catalogAgents: [],
  catalogSkills: [],
  agentsByCli: {},
  dismissedNotices: loadDismissedNotices(),
};

let cy = null;
let nodeDetails = {};
let graphInteractionsBound = false;
let selectedNodeId = null;
let selectedElementId = null;
let selectedTimelineSeq = null;
let pendingRestartPlan = null;
let apiVersion = 0;

const RESTART_MIN_API_VERSION = 4;
const RESTARTABLE_STEPS = new Set([
  "find-context",
  "write-feature",
  "check-feature",
  "resolve-gaps",
  "challenge-feature",
  "resolve-challenges",
  "check-feature-code",
  "resolve-code-alignment",
]);
let restartableByPipeline = {};

function restartableStepsFor(pipeline) {
  const list = restartableByPipeline[pipeline];
  if (Array.isArray(list) && list.length) return new Set(list);
  return pipeline === "spec" ? RESTARTABLE_STEPS : new Set();
}

function noticeBody(id) {
  return document.getElementById(id)?.querySelector(".notice-body") || null;
}

function isNoticeDismissed(id, message) {
  return Boolean(message && state.dismissedNotices[id] === message);
}

function dismissNotice(id) {
  const body = noticeBody(id);
  const message = body?.textContent?.trim() || "";
  if (message) {
    state.dismissedNotices[id] = message;
    try {
      sessionStorage.setItem(DISMISS_STORAGE_KEY, JSON.stringify(state.dismissedNotices));
    } catch {
      /* ignore quota errors */
    }
  }
  document.getElementById(id)?.classList.add("hidden");
}

function setNoticeBanner(id, baseClass, statusClass, message, show) {
  const el = document.getElementById(id);
  const body = noticeBody(id);
  if (!el || !body) return;

  if (!show || !message) {
    el.classList.add("hidden");
    body.textContent = "";
    return;
  }

  if (isNoticeDismissed(id, message)) {
    el.classList.add("hidden");
    body.textContent = message;
    return;
  }

  const classes = ["notice-banner", baseClass, statusClass].filter(Boolean);
  if (el.id !== "app-error") classes.push("run-only");
  el.className = classes.join(" ");
  body.textContent = message;
  el.classList.remove("hidden");
}

function initNoticeDismissHandlers() {
  document.querySelectorAll(".notice-banner .notice-dismiss").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      const banner = event.currentTarget.closest(".notice-banner");
      if (banner?.id) dismissNotice(banner.id);
    });
  });
}

function showError(message) {
  setNoticeBanner("app-error", "app-error", "", message, Boolean(message));
}

function clearError() {
  setNoticeBanner("app-error", "app-error", "", "", false);
}

function staleViewerMessage(feature) {
  return (
    `Функция «${feature}» недоступна: на этом порту старый viewer (API v${apiVersion || "?"}). ` +
    "Остановите сервер (Ctrl+C в терминале) и запустите: ./pipeline-viewer/start.sh — " +
    "откройте URL из вывода терминала (должно быть «API v4»)."
  );
}

async function parseJsonResponse(res) {
  const text = await res.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { error: text.slice(0, 200) };
  }
}

function initCytoscape() {
  if (cy) return cy;
  if (typeof cytoscape !== "function") {
    showError("Cytoscape не загрузился. Перезапустите viewer и обновите страницу.");
    return null;
  }
  cy = cytoscape({
    container: document.getElementById("cy"),
    style: [
      {
        selector: "node",
        style: {
          label: "data(label)",
          "text-valign": "center",
          "text-halign": "center",
          "font-size": "12px",
          color: "#f8fafc",
          "text-wrap": "wrap",
          "text-max-width": "150px",
          width: 168,
          height: 52,
          "background-color": "data(color)",
          shape: "round-rectangle",
          "border-width": 2,
          "border-color": "#1e293b",
        },
      },
      {
        selector: 'node[kind = "step"]',
        style: {
          shape: "round-rectangle",
          width: 158,
          height: 62,
          "font-size": "12px",
          "corner-radius": 6,
        },
      },
      {
        selector: 'node[kind = "orchestrator"]',
        style: {
          width: 200,
          height: 58,
          "font-size": "13px",
          "font-weight": "bold",
          shape: "ellipse",
        },
      },
      {
        selector: 'node[kind = "terminal"]',
        style: {
          shape: "diamond",
          width: 96,
          height: 96,
          "font-size": "13px",
        },
      },
      {
        selector: 'node[kind = "meta"]',
        style: {
          width: 140,
          height: 44,
          "font-size": "11px",
          shape: "round-rectangle",
        },
      },
      {
        selector: 'node[askFlag = "true"]',
        style: {
          "border-style": "dashed",
          "border-color": "#fdba74",
          "border-width": 3,
        },
      },
      {
        selector: 'node[cycleFlag = "true"]',
        style: {
          "border-color": "#2dd4bf",
          "border-width": 3,
        },
      },
      {
        selector: 'node[kind = "routing-sat"]',
        style: {
          width: 124,
          height: 28,
          "font-size": "8px",
          shape: "ellipse",
          "background-color": "data(color)",
          "border-color": "#a5b4fc",
          "border-width": 1.5,
          color: "#eef2ff",
          "text-max-width": "118px",
        },
      },
      {
        selector: 'node[kind = "visit"]',
        style: {
          width: 188,
          height: 64,
          "font-size": "10px",
          shape: "round-rectangle",
        },
      },
      {
        selector: 'node[kind = "stale-bundle"]',
        style: {
          width: 228,
          height: 78,
          "font-size": "11px",
          shape: "round-rectangle",
          "border-color": "#a8a29e",
          "border-width": 3,
          "border-style": "dashed",
          color: "#d6d3d1",
        },
      },
      {
        selector: "node[state = 'active']",
        style: {
          "border-color": "#93c5fd",
          "border-width": 4,
        },
      },
      {
        selector: "node[state = 'next']",
        style: {
          "border-color": "#a855f7",
          "border-width": 4,
          "border-style": "dashed",
        },
      },
      {
        selector: "node.draft-added",
        style: {
          "border-style": "dashed",
          "border-color": "#67e8f9",
          "border-width": 3,
        },
      },
      {
        selector: "node.cli-missing",
        style: {
          "border-color": "#fbbf24",
          "border-width": 3,
        },
      },
      {
        selector: "node.selected",
        style: {
          "border-color": "#fbbf24",
          "border-width": 4,
        },
      },
      {
        selector: "node.expected",
        style: {
          "border-color": "#a855f7",
          "border-width": 4,
          "border-style": "dashed",
        },
      },
      {
        selector: "node.diverged",
        style: {
          "border-color": "#f97316",
          "border-width": 5,
        },
      },
      {
        selector: "node[state = 'redo']",
        style: {
          "border-color": "#f0abfc",
          "border-width": 4,
          "border-style": "dashed",
        },
      },
      {
        selector: "node[state = 'stale']",
        style: {
          "background-color": "#44403c",
          "border-color": "#78716c",
          "border-width": 3,
          "border-style": "dotted",
          color: "#a8a29e",
          opacity: 0.68,
        },
      },
      {
        selector: "node.stale-visit",
        style: {
          "background-color": "#44403c",
          "border-color": "#a8a29e",
          "border-width": 3,
          "border-style": "dashed",
          color: "#d6d3d1",
          opacity: 0.62,
        },
      },
      {
        selector: "edge.stale-edge",
        style: {
          "line-color": "#44403c",
          "target-arrow-color": "#44403c",
          "line-style": "dashed",
          opacity: 0.45,
        },
      },
      {
        selector: "edge",
        style: {
          width: 2,
          "line-color": "data(color)",
          "target-arrow-color": "data(color)",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          "control-point-step-size": 42,
          label: "data(label)",
          "font-size": "8px",
          color: "#94a3b8",
          "text-background-color": "#0f172a",
          "text-background-opacity": 0.72,
          "text-background-padding": "2px",
          "text-rotation": "autorotate",
          opacity: 0.92,
        },
      },
      {
        selector: 'edge[kind = "main"]',
        style: {
          width: 2.5,
          "curve-style": "straight",
          opacity: 1,
        },
      },
      {
        selector: 'edge[kind = "branch"]',
        style: {
          width: 2,
          "line-style": "dashed",
          "line-dash-pattern": [8, 5],
          "line-color": "#64748b",
          "target-arrow-color": "#64748b",
          opacity: 0.88,
        },
      },
      {
        selector: 'edge[kind = "routing-sat"]',
        style: {
          width: 1.5,
          "curve-style": "straight",
          "line-color": "#818cf8",
          "target-arrow-shape": "none",
          "source-arrow-shape": "none",
          opacity: 0.9,
          label: "",
        },
      },
      {
        selector: 'edge[kind = "loop"]',
        style: {
          width: 1.5,
          "line-style": "dotted",
          "line-color": "#6366f1",
          "target-arrow-color": "#6366f1",
          opacity: 0.38,
          "font-size": "7px",
        },
      },
      {
        selector: 'edge[kind = "loop"][traversed = "true"]',
        style: {
          opacity: 0.72,
          width: 2,
        },
      },
      {
        selector: "edge.schema-edge",
        style: {
          opacity: 0.95,
        },
      },
      {
        selector: 'edge.schema-edge[kind = "loop"]',
        style: {
          opacity: 0.78,
          width: 1.8,
        },
      },
      {
        selector: "edge[traversed = 'true']",
        style: {
          width: 3,
          opacity: 1,
        },
      },
      {
        selector: 'edge[kind = "routing-sat"]',
        style: {
          width: 1.5,
          "target-arrow-shape": "none",
          opacity: 0.9,
        },
      },
      {
        selector: 'edge[kind = "branch"][traversed = "true"]',
        style: {
          "line-color": "data(color)",
          "target-arrow-color": "data(color)",
        },
      },
    ],
    layout: { name: "preset" },
    minZoom: 0.35,
    maxZoom: 2,
    wheelSensitivity: 0.18,
    userPanningEnabled: true,
    panningEnabled: true,
    boxSelectionEnabled: false,
  });
  bindGraphWheelScroll(cy);
  bindGraphInteractions(cy);
  return cy;
}

function bindGraphWheelScroll(graph) {
  const scrollEl = document.getElementById("graph-scroll");
  const container = graph.container();
  if (!scrollEl || !container) return;

  container.addEventListener(
    "wheel",
    (event) => {
      const zoomGesture = event.ctrlKey || event.metaKey;
      if (zoomGesture) return;

      event.preventDefault();
      event.stopPropagation();
      scrollEl.scrollTop += event.deltaY;
      scrollEl.scrollLeft += event.deltaX;
    },
    { passive: false, capture: true }
  );
}

function divergencesForStep(stepId) {
  const byStep = state.graph?.divergence?.by_step;
  if (byStep && byStep[stepId]) {
    return byStep[stepId];
  }
  return (state.graph?.divergence?.items || []).filter(
    (item) => (item.related_steps || []).includes(stepId)
  );
}

function visitsForStep(stepId) {
  return (state.graph?.timeline || []).filter((row) => row.step === stepId);
}

function formatNodeLabel(node) {
  const lines = [];
  lines.push(node.label || node.id);
  if (node.subagent) lines.push(`(${node.subagent})`);
  if (node.ask) lines.push("ask");
  if (node.visit_count > 0) lines.push(`×${node.visit_count}`);
  return lines.join("\n");
}

function contextualizeDivergence(item, stepId) {
  const copy = { ...item };
  if (item.kind === "stopped_early") {
    if (stepId === item.expected_step) {
      copy.title = "Dispatch ждёт этот шаг";
      copy.detail =
        `Оркестратор должен был вызвать этот шаг следующим, но сессия уже idle.\n\n${item.detail || ""}`;
    } else if (stepId === item.actual_step) {
      copy.title = "Пайплайн остановился после этого шага";
      copy.detail =
        `Это последний зафиксированный шаг, хотя dispatch считает пайплайн незавершённым.\n\n${item.detail || ""}`;
    }
  } else if (item.kind === "order_violation") {
    if (stepId === item.from_step) {
      copy.title = "Отсюда — нестандартный переход";
      copy.detail = `Из этого шага перешли в \`${item.to_step}\` (см. timeline).\n\n${item.detail || ""}`;
    } else if (stepId === item.to_step) {
      copy.title = "Сюда — нестандартный переход";
      copy.detail = `Пришли из \`${item.from_step}\`, хотя на графе такого ребра нет.\n\n${item.detail || ""}`;
    }
  }
  return copy;
}

function renderStepDivergenceCards(stepId, items) {
  const box = document.getElementById("step-divergence");
  box.innerHTML = "";
  const summary = state.graph?.divergence?.summary;

  if (!items.length) {
    if (summary?.expected_step === stepId && summary?.must_continue) {
      box.classList.remove("hidden");
      box.innerHTML =
        `<h3>Dispatch</h3>` +
        `<div class="divergence-card ok">` +
        `<strong>Следующий шаг по dispatch</strong>` +
        `<p class="divergence-detail">${summary.dispatch_reason || "Оркестратор должен вызвать этот шаг."}</p>` +
        `</div>`;
      return;
    }
    box.classList.add("hidden");
    return;
  }

  box.classList.remove("hidden");
  const heading = document.createElement("h3");
  heading.textContent = "Расхождения по этому шагу";
  box.appendChild(heading);
  for (const raw of items) {
    const item = contextualizeDivergence(raw, stepId);
    const card = document.createElement("div");
    card.className = `divergence-card ${item.severity || "warn"}`;
    const ts = item.ts ? `<span class="divergence-ts">${item.ts}</span>` : "";
    const explain = item.explain
      ? `<p class="divergence-explain">${item.explain}</p>`
      : "";
    const detail = item.detail
      ? `<p class="divergence-detail">${item.detail.replace(/\n/g, "<br>")}</p>`
      : "";
    const hint = item.hint ? `<p class="divergence-hint">→ ${item.hint}</p>` : "";
    card.innerHTML = `${ts}<strong>${item.title || item.kind}</strong>${explain}${detail}${hint}`;
    box.appendChild(card);
  }
}

function renderStepVisits(stepId) {
  const box = document.getElementById("step-visits");
  const visits = visitsForStep(stepId);
  box.innerHTML = "";
  if (!visits.length) {
    box.classList.add("hidden");
    return;
  }
  box.classList.remove("hidden");
  const heading = document.createElement("h3");
  heading.textContent = `Проходы этого шага (${visits.length})`;
  box.appendChild(heading);
  const list = document.createElement("ol");
  list.className = "visit-list";
  for (const row of visits) {
    const li = document.createElement("li");
    const displayState = rowDisplayState(row);
    li.className = displayState;
    if (row.divergence_kinds?.length) li.classList.add("diverged");
    const sub = row.subagent ? ` → ${row.subagent}` : "";
    const ts = formatLocalDateTime(row.ts);
    const staleTag = displayState === "stale" ? " · устарел" : "";
    li.textContent = `#${row.seq} · pass ${row.pass} · ${ts}${sub}${staleTag}`;
    list.appendChild(li);
  }
  box.appendChild(list);
}

function clearNodePanel() {
  document.getElementById("step-detail").textContent = isSchemaMode()
    ? "Кликните клетку или перетащите агента слева. YAML не пишется."
    : "Кликните узел на графе.";
  document.getElementById("step-visits").classList.add("hidden");
  document.getElementById("step-divergence").classList.add("hidden");
  document.getElementById("restart-actions").classList.add("hidden");
  setSchemaNodeActionsVisible(false);
}

function updateRestartActions(stepId) {
  const wrap = document.getElementById("restart-actions");
  if (!stepId || !restartableStepsFor(state.pipeline).has(stepId)) {
    wrap.classList.add("hidden");
    return;
  }
  wrap.classList.remove("hidden");
}

function fillModalList(id, items) {
  const ul = document.getElementById(id);
  ul.innerHTML = "";
  if (!items?.length) {
    const li = document.createElement("li");
    li.textContent = "—";
    ul.appendChild(li);
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = item;
    ul.appendChild(li);
  }
}

function resetRestartConfirmBtn() {
  const btn = document.getElementById("restart-confirm-btn");
  btn.disabled = false;
  btn.textContent = "Удалить и перезапустить";
  btn.dataset.mode = "apply";
}

function closeRestartModal() {
  document.getElementById("restart-modal").classList.add("hidden");
  document.getElementById("restart-result").classList.add("hidden");
  pendingRestartPlan = null;
  resetRestartConfirmBtn();
}

async function openRestartModal() {
  if (!selectedNodeId || !state.slug) return;
  if (apiVersion < RESTART_MIN_API_VERSION) {
    showError(staleViewerMessage("Перезапустить с этого шага"));
    return;
  }
  const params = new URLSearchParams({
    slug: state.slug,
    from_step: selectedNodeId,
    pipeline: state.pipeline,
  });
  if (selectedTimelineSeq) params.set("from_seq", String(selectedTimelineSeq));

  try {
    const res = await fetch(`/api/restart-plan?${params}`);
    const plan = await parseJsonResponse(res);
    if (!res.ok) {
      if (res.status === 404) {
        showError(staleViewerMessage("Перезапустить с этого шага"));
        return;
      }
      showError(plan.error || "Не удалось построить план перезапуска");
      return;
    }
    pendingRestartPlan = plan;
    clearError();

    const seqHint = plan.from_seq ? ` (проход #${plan.from_seq})` : "";
    document.getElementById("restart-modal-summary").textContent =
      `Slug: ${plan.slug} · перезапуск с «${plan.from_step}»${seqHint}`;

    const warnEl = document.getElementById("restart-modal-warnings");
    warnEl.innerHTML = (plan.warnings || [])
      .map((w) => `<p>⚠ ${w}</p>`)
      .join("");

    fillModalList("restart-modal-remove", plan.remove_paths);
    fillModalList("restart-modal-keep", plan.keep_paths);
    document.getElementById("restart-modal-commands").textContent = restartCliBlock(plan);

    document.getElementById("restart-result").classList.add("hidden");
    resetRestartConfirmBtn();
    document.getElementById("restart-modal").classList.remove("hidden");
  } catch (err) {
    showError(err.message || String(err));
  }
}

async function confirmRestart() {
  const btn = document.getElementById("restart-confirm-btn");
  if (btn.dataset.mode === "close") {
    closeRestartModal();
    return;
  }
  if (!pendingRestartPlan || !state.slug) return;
  btn.disabled = true;
  btn.textContent = "Удаляю…";

  try {
    const res = await fetch("/api/restart", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        slug: state.slug,
        from_step: pendingRestartPlan.from_step,
        from_seq: pendingRestartPlan.from_seq,
        pipeline: state.pipeline,
        confirm: true,
      }),
    });
    const payload = await parseJsonResponse(res);
    if (!res.ok) {
      if (res.status === 404 || res.status === 501) {
        showError(staleViewerMessage("Перезапустить с этого шага"));
        return;
      }
      showError(payload.error || "Перезапуск не выполнен");
      return;
    }

    const resultEl = document.getElementById("restart-result");
    resultEl.classList.remove("hidden");
    const plan = payload.plan || pendingRestartPlan || {};
    const cliBlock = payload.result?.cli_block || restartCliBlock(plan);
    resultEl.textContent = [
      "Готово.",
      `Удалено файлов: ${(payload.result?.removed || []).length}`,
      "",
      "В Qwen/GigaCode:",
      cliBlock,
    ].join("\n");

    btn.disabled = false;
    btn.textContent = "Закрыть";
    btn.dataset.mode = "close";
  } catch (err) {
    showError(err.message || String(err));
    resetRestartConfirmBtn();
  }
}

function showNodePanel(nodeId) {
  const detail = nodeDetails[nodeId];
  const el = document.getElementById("step-detail");
  const node = (state.graph?.nodes || []).find((n) => n.id === nodeId);
  const visitN = node?.visit_count || visitsForStep(nodeId).length;

  if (!detail && !node) {
    el.textContent = `Нет данных для «${nodeId}».`;
    document.getElementById("step-visits").classList.add("hidden");
    document.getElementById("step-divergence").classList.add("hidden");
    return;
  }

  let text = detail?.body || detail?.hint || nodeId;
  if (visitN > 0) {
    text = `[${visitN} проход(ов)]\n\n${text}`;
  }
  if (detail?.artifact_path) {
    text += `\n\n---\nФайл: ${detail.artifact_path}`;
  }
  el.textContent = text;

  renderStepVisits(nodeId);
  renderStepDivergenceCards(nodeId, divergencesForStep(nodeId));
  highlightTimelineRow(nodeId, selectedTimelineSeq);
  updateRestartActions(nodeId);
}

function showTooltip(text, x, y) {
  const tip = document.getElementById("tooltip");
  if (!text) {
    tip.classList.add("hidden");
    return;
  }
  tip.textContent = text;
  tip.classList.remove("hidden");
  const panel = document.getElementById("graph-panel").getBoundingClientRect();
  tip.style.left = `${Math.min(x - panel.left + 12, panel.width - 330)}px`;
  tip.style.top = `${Math.max(y - panel.top - 8, 8)}px`;
}

function hideTooltip() {
  document.getElementById("tooltip").classList.add("hidden");
}

function restartCliBlock(planOrRestart) {
  if (planOrRestart?.cli_block) return planOrRestart.cli_block;
  const c = planOrRestart?.cli_commands || {};
  const slug = c.slug || planOrRestart?.slug || state.slug || "";
  const slash = c.slash_command || planOrRestart?.next_command || "";
  const orch = c.orchestrator_command || (slug ? `продолжи ${slug}` : "");
  const sub = c.next_subagent || planOrRestart?.next_subagent || "";
  const lines = [`Фича: ${slug}`, "", slash, "", orch];
  if (sub) lines.push("", `→ ${sub}`);
  return lines.join("\n");
}

function renderSessionOutcomeBanner(data) {
  const outcome = data?.outcome;
  if (outcome?.ready) {
    setNoticeBanner(
      "session-outcome",
      "session-outcome",
      "status-ok",
      `✓ Spec готов — ${outcome.verdict || "PASS"}`,
      true
    );
    return;
  }

  const cur = data?.current;
  if (cur?.status === "running") {
    setNoticeBanner(
      "session-outcome",
      "session-outcome",
      "status-active",
      `Сейчас: ${cur.step || "?"} → ${cur.subagent || "?"}` +
        (cur.note ? ` — ${cur.note}` : ""),
      true
    );
    return;
  }
  if (cur?.status === "next") {
    setNoticeBanner(
      "session-outcome",
      "session-outcome",
      "status-next",
      `Следующий по run-log: ${cur.step || "?"} → ${cur.subagent || "?"}`,
      true
    );
    return;
  }

  const last = lastActivePass(data);
  if (!last || !data?.slug) {
    setNoticeBanner("session-outcome", "session-outcome", "", "", false);
    return;
  }

  const result = last.result || "ok";
  const step = last.step || "?";
  const seq = last.seq ? `#${last.seq}` : "";
  const note = last.note ? ` — ${last.note}` : "";

  if (result === "fail" || result === "retry") {
    setNoticeBanner(
      "session-outcome",
      "session-outcome",
      "status-fail",
      `Последний актуальный проход ${seq} ${step}: ${result}. ` +
        "Сессия остановилась — это fail шага, не сбой viewer. Повторите шаг в CLI." +
        note,
      true
    );
    return;
  }

  setNoticeBanner("session-outcome", "session-outcome", "", "", false);
}

function renderDivergenceBanner(summary) {
  if (!summary || summary.status === "n/a") {
    setNoticeBanner("divergence-banner", "divergence-banner", "", "", false);
    return;
  }
  if (summary.status === "ok" && !summary.must_continue) {
    setNoticeBanner("divergence-banner", "divergence-banner", "", "", false);
    return;
  }
  if (summary.status === "ok" && summary.must_continue) {
    setNoticeBanner(
      "divergence-banner",
      "divergence-banner",
      `status-${summary.status}`,
      `Dispatch: следующий шаг → ${summary.expected_step}` +
        (summary.expected_subagent ? ` (${summary.expected_subagent})` : ""),
      true
    );
    return;
  }
  setNoticeBanner(
    "divergence-banner",
    "divergence-banner",
    `status-${summary.status}`,
    summary.message || "Обнаружено расхождение с dispatch",
    true
  );
}

function validationBannerClass(validation) {
  if (!validation) return "ok";
  if (validation.error) return "block";
  const advice = validation.advice || [];
  if (!validation.ok || advice.some((a) => a.severity === "block")) return "block";
  if (advice.some((a) => a.severity === "warn")) return "warn";
  return "ok";
}

function renderValidationBanner(validation) {
  if (!validation) {
    setNoticeBanner("validation-banner", "validation-banner", "", "", false);
    return;
  }
  if (validation.error) {
    setNoticeBanner(
      "validation-banner",
      "validation-banner",
      "status-block",
      `Workflow validate: ${validation.error}`,
      true
    );
    return;
  }

  const advice = (validation.advice || []).filter((a) => a.severity !== "ok");
  const klass = validationBannerClass(validation);
  if (klass === "ok" && validation.ready) {
    setNoticeBanner(
      "validation-banner",
      "validation-banner",
      "status-ok",
      "✓ Workflow OK — spec готов (PASS / PASS WITH GAPS)",
      true
    );
    return;
  }

  const blocks = (validation.advice || []).filter((a) => a.severity === "block");
  const warns = (validation.advice || []).filter((a) => a.severity === "warn");
  if (blocks.length) {
    setNoticeBanner(
      "validation-banner",
      "validation-banner",
      `status-${klass}`,
      `Workflow BLOCK (${blocks.length}): ${blocks[0].title} — ${blocks[0].workflow_fix}`,
      true
    );
    return;
  }
  if (warns.length) {
    setNoticeBanner(
      "validation-banner",
      "validation-banner",
      `status-${klass}`,
      `Workflow WARN: ${warns[0].title} — ${warns[0].workflow_fix}`,
      true
    );
    return;
  }
  if (validation.must_continue) {
    setNoticeBanner(
      "validation-banner",
      "validation-banner",
      `status-${klass}`,
      `Workflow OK · продолжай: ${validation.next_step} → ${validation.next_subagent}`,
      true
    );
    return;
  }
  setNoticeBanner(
    "validation-banner",
    "validation-banner",
    `status-${klass}`,
    advice.length ? advice[0].title : "Workflow validate: OK",
    true
  );
}

function renderValidationPanel(validation) {
  const panel = document.getElementById("validation-panel");
  const summaryEl = document.getElementById("validation-summary");
  const listEl = document.getElementById("validation-advice");
  if (!panel || !summaryEl || !listEl) return;

  if (!validation) {
    panel.classList.add("hidden");
    summaryEl.textContent = "";
    listEl.innerHTML = "";
    return;
  }

  panel.classList.remove("hidden");
  summaryEl.textContent =
    `OK: ${validation.ok ? "да" : "нет"} · ready: ${validation.ready ? "да" : "нет"} · ` +
    `must_continue: ${validation.must_continue ? "да" : "нет"} · ` +
    `next: ${validation.next_step || "—"} → ${validation.next_subagent || "—"}`;

  listEl.innerHTML = "";
  for (const item of validation.advice || []) {
    const li = document.createElement("li");
    const sev = item.severity || "ok";
    li.innerHTML =
      `<span class="severity severity-${sev}">${sev}</span> ` +
      `<strong>${item.title || item.id || "advice"}</strong>` +
      (item.detail ? `<div>${item.detail}</div>` : "") +
      (item.workflow_fix ? `<div><em>Fix:</em> ${item.workflow_fix}</div>` : "");
    listEl.appendChild(li);
  }
}

function renderDispatchPanel(data) {
  const el = document.getElementById("dispatch");
  const dispatch = data.dispatch;
  const summary = data.divergence?.summary;
  if (!dispatch && !summary) {
    el.textContent = data.pipeline === "calibration" ? "Dispatch только для Spec tab" : "—";
    return;
  }
  const lines = [];
  if (summary?.must_continue) {
    lines.push("⚠ Пайплайн не завершён — оркестратор должен продолжить сам.");
  } else if (dispatch?.ready) {
    lines.push("✓ Spec готов (PASS / PASS WITH GAPS).");
  }
  if (summary?.expected_step) {
    lines.push(
      `Следующий шаг: ${summary.expected_step}` +
        (summary.expected_subagent ? ` → ${summary.expected_subagent}` : "")
    );
  }
  if (summary?.dispatch_reason || dispatch?.next_reason) {
    lines.push(`Почему: ${summary?.dispatch_reason || dispatch?.next_reason}`);
  }
  if (summary) {
    lines.push(
      `Режим: ${summary.orchestrator_mode || "—"} · must_continue: ${
        summary.must_continue ? "да" : "нет"
      }`
    );
  }
  el.textContent = lines.join("\n\n") || "—";
}

function highlightTimelineRow(stepId, seq) {
  document.querySelectorAll("#timeline li").forEach((li) => {
    const matchStep = stepId && li.dataset.step === stepId;
    const matchSeq = seq && li.dataset.seq === String(seq);
    li.classList.toggle("selected", seq ? matchSeq : matchStep);
  });
}

function setGraphViewTabs() {
  document.querySelectorAll("#graph-view-tabs .tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === state.graphView);
  });
  const isTiming = state.graphView === "timing";
  document.querySelector(".legend-target")?.classList.toggle(
    "hidden",
    state.graphView === "actual" || isTiming
  );
  document.querySelector(".legend-actual")?.classList.toggle("hidden", state.graphView !== "actual");
  document.getElementById("graph-scroll")?.classList.toggle("hidden-for-timing", isTiming);
  document.getElementById("timing-panel")?.classList.toggle("hidden", !isTiming);
  document.getElementById("legend")?.classList.toggle("hidden", isTiming);
  document.getElementById("stale-toggle")?.classList.toggle("hidden", isTiming || state.graphView !== "actual");
}

function targetEdgeLabel(edge) {
  const kind = edge.kind || "main";
  const label = edge.label || "";
  if (kind === "branch" && label.length > 28) return `${label.slice(0, 26)}…`;
  return label;
}

function parseUtcDate(ts) {
  if (!ts) return null;
  const raw = String(ts).trim();
  const normalized = /Z$|[+-]\d{2}:\d{2}$/.test(raw) ? raw : `${raw}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

function localTimeZoneLabel() {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
    const parts = new Intl.DateTimeFormat(undefined, { timeZoneName: "short" }).formatToParts(
      new Date()
    );
    const short = parts.find((part) => part.type === "timeZoneName")?.value || "";
    if (tz && short && !short.includes(tz)) return `${tz} (${short})`;
    return tz || short || "";
  } catch {
    return "";
  }
}

function formatLocalDateTime(ts) {
  const date = parseUtcDate(ts);
  if (!date) return ts || "—";
  return new Intl.DateTimeFormat(undefined, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

function formatLocalTime(ts) {
  const date = parseUtcDate(ts);
  if (!date) return "";
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

function formatDurationSec(seconds) {
  const total = Number(seconds);
  if (!Number.isFinite(total) || total < 0) return "—";
  if (total < 60) return `${Math.round(total)} с`;
  const minutes = Math.floor(total / 60);
  const secs = Math.round(total % 60);
  if (minutes < 60) return secs ? `${minutes} мин ${secs} с` : `${minutes} мин`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} ч ${rest} мин` : `${hours} ч`;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatLocalRange(startTs, endTs) {
  if (!startTs && !endTs) return "—";
  if (startTs && endTs) {
    return `${formatLocalDateTime(startTs)} → ${formatLocalTime(endTs)}`;
  }
  return formatLocalDateTime(startTs || endTs);
}

function staleReasonText(row) {
  if (row?.stale_reason) return row.stale_reason;
  const result = row?.result || "fail";
  const by = row?.superseded_by ? ` (#${row.superseded_by})` : "";
  return (
    `Хук записал «${result}», позже этот же шаг завершился ok${by}. ` +
    "Работа не отменялась — ложный fail/retry по тексту ответа."
  );
}

const HOOK_PAIR_WINDOW_MS = 15000;

function isSessionSyncRow(row) {
  return (row?.source || "") === "session-sync";
}

function isWorkRow(row) {
  if (!row) return false;
  if (isSessionSyncRow(row)) return true;
  if (row.duration_sec != null) return true;
  if (row.call_id) return true;
  return String(row.note || "").startsWith("sync:");
}

function isHookStampRow(row) {
  if (!row || isWorkRow(row)) return false;
  const src = row.source || "run-log";
  return src === "run-log" || src === "merged" || src === "";
}

function syncWorkLabel(note) {
  const text = String(note || "").trim();
  if (!text) return "";
  return text.replace(/^sync:[^\s·]+(?:\s*·\s*)?/i, "").trim();
}

function durationPassForInvocation(inv, timingPasses, used) {
  if (!timingPasses?.length) return null;
  const t = parseUtcDate(inv.ts);
  let best = null;
  let bestIdx = -1;
  let bestDist = Infinity;
  for (let index = 0; index < timingPasses.length; index += 1) {
    const pass = timingPasses[index];
    if (used.has(index)) continue;
    if (pass.step !== inv.step) continue;
    if (inv.callId && pass.call_id && pass.call_id === inv.callId) {
      used.add(index);
      return pass;
    }
    const start = parseUtcDate(pass.start_ts);
    const end = parseUtcDate(pass.end_ts) || start;
    if (!t || !start) continue;
    if (t.getTime() < start.getTime() - 8000) continue;
    if (t.getTime() > end.getTime() + 120000) continue;
    const dist = Math.abs(end.getTime() - t.getTime());
    if (dist < bestDist) {
      best = pass;
      bestIdx = index;
      bestDist = dist;
    }
  }
  if (bestIdx >= 0) used.add(bestIdx);
  return best;
}

function groupAgentInvocations(timeline, timingPasses) {
  const rows = timeline || [];
  const used = new Set();
  const clusters = [];

  // Hook + session-sync (often source=merged after spawn join) are the same
  // agent call a second apart. Pair same-step rows in a 15s window.
  rows.forEach((row, index) => {
    if (used.has(index)) return;
    const t = parseUtcDate(row.ts);
    const cluster = [row];
    used.add(index);
    rows.forEach((other, j) => {
      if (used.has(j) || other.step !== row.step) return;
      const otherT = parseUtcDate(other.ts);
      if (!t || !otherT) return;
      if (Math.abs(otherT.getTime() - t.getTime()) <= HOOK_PAIR_WINDOW_MS) {
        cluster.push(other);
        used.add(j);
      }
    });
    clusters.push(cluster);
  });

  clusters.sort((a, b) => {
    const ta = a.reduce((min, row) => (row.ts && row.ts < min ? row.ts : min), a[0]?.ts || "");
    const tb = b.reduce((min, row) => (row.ts && row.ts < min ? row.ts : min), b[0]?.ts || "");
    return (ta || "").localeCompare(tb || "");
  });

  const usedPasses = new Set();
  const invocations = clusters.map((cluster, index) => {
    const hook = cluster.find(isHookStampRow);
    const sync = cluster.find(isWorkRow);
    const timed = cluster.find((row) => row.duration_sec != null);
    const step = hook?.step || sync?.step || cluster[0]?.step || "";
    const hookResult = hook?.result || "";
    const agentResult = sync || (timed && timed.result === "ok")
      ? "ok"
      : hookResult || cluster[0]?.result || "ok";
    const inv = {
      step,
      subagent: hook?.subagent || sync?.subagent || cluster[0]?.subagent || "",
      ts: sync?.ended_at || sync?.ts || timed?.ended_at || hook?.ts || cluster[0]?.ts,
      startTs: sync?.started_at || timed?.started_at || hook?.spawn_ts || hook?.ts || cluster[0]?.ts,
      endTs: sync?.ended_at || timed?.ended_at || sync?.ts || hook?.ts,
      seconds: sync?.duration_sec ?? timed?.duration_sec,
      callId: sync?.call_id || timed?.call_id || hook?.call_id || "",
      work: syncWorkLabel(sync?.note || timed?.note || ""),
      hook: hook || null,
      hookResult,
      agentResult,
      seq: hook?.seq || sync?.seq || cluster[0]?.seq,
      source: sync ? "session-sync" : hook?.source || cluster[0]?.source || "run-log",
    };
    if (inv.seconds == null) {
      const matched = durationPassForInvocation(inv, timingPasses, usedPasses);
      if (matched) {
        inv.seconds = matched.seconds;
        if (!inv.startTs) inv.startTs = matched.start_ts;
        if (!inv.endTs) inv.endTs = matched.end_ts;
        if (!inv.work) inv.work = matched.note || "";
        if (!inv.subagent) inv.subagent = matched.subagent || "";
        inv.source = matched.source || inv.source;
      }
    }
    const next = clusters[index + 1];
    if (next) {
      const nextHook = next.find(isHookStampRow) || next[0];
      const nextSync = next.find(isSessionSyncRow);
      inv.nextStep = nextHook?.step || nextSync?.step || next[0]?.step || "";
      inv.nextSubagent = nextHook?.subagent || nextSync?.subagent || "";
    } else {
      inv.nextStep = "";
      inv.nextSubagent = "";
    }
    return inv;
  });
  const lastByStep = {};
  for (const inv of invocations) {
    const prev = lastByStep[inv.step];
    inv.retriedAfterFail = Boolean(
      prev && (prev.agentResult === "fail" || prev.agentResult === "retry")
    );
    lastByStep[inv.step] = inv;
  }
  return invocations;
}

function timingStepColor(stepId) {
  return TIMING_STEP_COLORS[stepId] || "#94a3b8";
}

function nestRoutingUnderAgents(invocations) {
  const groups = [];
  for (const inv of invocations) {
    if (isRoutingStep(inv.step)) {
      const last = groups[groups.length - 1];
      if (last) last.routings.push(inv);
      else groups.push({ inv, routings: [], routingOnly: true });
    } else {
      groups.push({ inv, routings: [], routingOnly: false });
    }
  }
  return groups;
}

function renderTimingHook(inv) {
  if (!inv.hook) return "";
  const mismatch = inv.hookResult && inv.hookResult !== inv.agentResult;
  const led = inv.nextStep
    ? `повёл к: ${inv.nextStep}${inv.nextSubagent ? ` → ${inv.nextSubagent}` : ""}`
    : "повёл к: конец прогона / дальше по dispatch";
  const note = (inv.hook.note || "").trim();
  return (
    `<div class="timing-hook${mismatch ? " is-mismatch" : ""}">` +
    `<div class="timing-hook-title">хук SubagentStop · записал «${escapeHtml(inv.hookResult || "ok")}»</div>` +
    `<div class="timing-hook-led">${escapeHtml(led)}</div>` +
    (note ? `<p class="timing-hook-note">${escapeHtml(note)}</p>` : "") +
    `</div>`
  );
}

function renderTimingInvocation(inv, nested) {
  const failed = inv.agentResult === "fail" || inv.agentResult === "retry";
  const cls = [
    nested ? "timing-routing" : "timing-pass",
    failed ? `is-${inv.agentResult}` : "",
  ]
    .filter(Boolean)
    .join(" ");
  let status = "";
  if (failed) {
    status =
      `<span class="timing-badge is-${inv.agentResult}">` +
      `${inv.agentResult === "retry" ? "агент: retry" : "агент: упал"}</span>`;
  }
  if (inv.retriedAfterFail) {
    status += `<span class="timing-badge is-retry">retry после сбоя</span>`;
  }
  const sub = inv.subagent
    ? `<span class="timing-pass-sub">${escapeHtml(inv.subagent)}</span>`
    : "";
  const title = nested ? "analyze-routing" : inv.step || "?";
  const work = inv.work ? `<p class="timing-work">${escapeHtml(inv.work)}</p>` : "";
  return (
    `<li class="${cls}">` +
    `<div class="timing-pass-head">` +
    `<code>${escapeHtml(title)}</code>${sub}${status}` +
    `<span class="timing-pass-dur">${escapeHtml(formatDurationSec(inv.seconds))}</span>` +
    `</div>` +
    `<div class="timing-pass-when">${escapeHtml(formatLocalRange(inv.startTs, inv.endTs))}</div>` +
    work +
    renderTimingHook(inv) +
    `</li>`
  );
}

function renderTimingGroup(group) {
  const innerRoutings = group.routings
    .map((inv) => renderTimingInvocation(inv, true))
    .join("");
  const nested = innerRoutings
    ? `<ol class="timing-routings">${innerRoutings}</ol>`
    : "";
  const html = renderTimingInvocation(group.inv, group.routingOnly);
  const close = html.lastIndexOf("</li>");
  if (close < 0) return html + nested;
  return html.slice(0, close) + nested + html.slice(close);
}

function renderTimingsPanel(timings, timeline) {
  const summaryEl = document.getElementById("timing-summary");
  const chartEl = document.getElementById("timing-chart");
  const notesEl = document.getElementById("timing-notes");
  const passesEl = document.getElementById("timing-passes");
  const passesWrap = document.getElementById("timing-passes-wrap");
  if (!summaryEl || !chartEl) return;

  if (!timings || timings.error) {
    summaryEl.innerHTML = `<p>Нет данных о длительности${timings?.error ? `: ${timings.error}` : ""}.</p>`;
    chartEl.innerHTML = "";
    if (notesEl) notesEl.innerHTML = "";
    if (passesEl) passesEl.innerHTML = "";
    return;
  }

  const steps = timings.steps || [];
  const tz = localTimeZoneLabel();
  const range =
    timings.started_at && timings.ended_at
      ? `${formatLocalDateTime(timings.started_at)} → ${formatLocalDateTime(timings.ended_at)}`
      : "—";
  const src = timings.primary_source || "—";
  const invocations = groupAgentInvocations(timeline, timings.passes || []);
  const groups = nestRoutingUnderAgents(invocations);
  const failedN = invocations.filter(
    (inv) => inv.agentResult === "fail" || inv.agentResult === "retry"
  ).length;
  summaryEl.innerHTML =
    `<p><strong>Σ ${escapeHtml(timings.total_label || "—")}</strong> активной работы subagent` +
    (timings.wall_sec ? ` · на timeline ${Math.round(timings.wall_sec / 60)} мин` : "") +
    `<br><span class="timing-range">${escapeHtml(range)}` +
    (tz ? ` · ${escapeHtml(tz)}` : "") +
    `</span>` +
    `<br><span class="timing-range">источник: ${escapeHtml(src)}</span></p>` +
    `<p class="timing-stale-hint">Строка — вызов агента шага` +
    (groups.length ? ` (${groups.length})` : "") +
    `. Под ним — analyze-routing, как овал на «Факт». Фиолетовое — хук: что записал и к кому повёл.` +
    (failedN ? ` Красным/жёлтым — агент упал или retry.` : "") +
    `</p>`;

  if (!steps.length) {
    chartEl.innerHTML = "<p class='timing-meta'>Run-log пуст — сначала прогоните пайплайн.</p>";
  } else {
    const maxPct = Math.max(...steps.map((s) => s.percent || 0), 1);
    chartEl.innerHTML = steps
      .map((step) => {
        const width = Math.max(2, Math.round(((step.percent || 0) / maxPct) * 100));
        const color = timingStepColor(step.id);
        const passes =
          step.passes > 1 ? ` · ${step.passes} прохода` : step.passes === 1 ? " · 1 проход" : "";
        const conf = step.confidence === "estimate" ? " ~" : "";
        return (
          `<div class="timing-row">` +
          `<div class="timing-label">${step.label || step.id}</div>` +
          `<div class="timing-bar-track">` +
          `<div class="timing-bar-fill" style="width:${width}%;background:${color}"></div>` +
          `</div>` +
          `<div class="timing-meta">${conf}${step.minutes} мин · ${step.percent}%${passes}</div>` +
          `</div>`
        );
      })
      .join("");
  }

  if (notesEl) {
    notesEl.innerHTML = (timings.notes || [])
      .map((note) => `<li>${escapeHtml(note)}</li>`)
      .join("");
  }

  if (passesEl && passesWrap) {
    if (!invocations.length && !(timings.passes || []).length) {
      passesWrap.classList.add("hidden");
      passesEl.innerHTML = "";
    } else {
      passesWrap.classList.remove("hidden");
      const items = groups.length
        ? groups
        : (timings.passes || []).map((pass) => ({
            inv: {
              step: pass.step,
              subagent: pass.subagent,
              startTs: pass.start_ts,
              endTs: pass.end_ts,
              seconds: pass.seconds,
              work: pass.note || "",
              agentResult: "ok",
              hookResult: "",
              hook: null,
              source: pass.source,
              retriedAfterFail: false,
              nextStep: "",
              nextSubagent: "",
            },
            routings: [],
            routingOnly: false,
          }));
      passesEl.innerHTML = items.map(renderTimingGroup).join("");
    }
  }
}

function staleTimelineRows(timeline) {
  return (timeline || []).filter((row) => rowDisplayState(row) === "stale");
}

function rowDisplayState(row) {
  if (row.display_state === "stale") return "stale";
  return row.display_state || row.result || "ok";
}

function lastActivePass(data) {
  if (data?.last_pass) return data.last_pass;
  const timeline = data?.timeline || [];
  for (let i = timeline.length - 1; i >= 0; i -= 1) {
    if (rowDisplayState(timeline[i]) !== "stale") return timeline[i];
  }
  return timeline.length ? timeline[timeline.length - 1] : null;
}

function rebuildTimelineMeta(timeline) {
  const stepPass = {};
  timeline.forEach((row, index) => {
    row.seq = index + 1;
    const step = row.step || "";
    if (step) {
      stepPass[step] = (stepPass[step] || 0) + 1;
      row.pass = stepPass[step];
    }
  });
}

function markSupersededPasses(timeline) {
  const byStep = new Map();
  for (const row of timeline) {
    const step = row.step || "";
    if (!step) continue;
    if (!byStep.has(step)) byStep.set(step, []);
    byStep.get(step).push(row);
  }
  for (const rows of byStep.values()) {
    if (rows.length < 2) continue;
    rows.sort((a, b) => (a.seq || 0) - (b.seq || 0) || (a.ts || "").localeCompare(b.ts || ""));
    const latest = rows[rows.length - 1];
    const latestOk = latest.result !== "fail" && latest.result !== "retry";
    if (!latestOk) continue;
    for (let i = 0; i < rows.length - 1; i += 1) {
      const row = rows[i];
      if (row.result === "fail" || row.result === "retry") {
        if (row.display_state !== "stale") {
          row.display_state = "stale";
          row.superseded_by = latest.seq;
        }
      }
    }
  }
}

function normalizeTimelineDisplay(data) {
  const restart = data?.restart;
  let timeline = data?.timeline || [];
  if (!timeline.length && !data?.run_log_tail?.length) return;

  // Server timeline already merges spawn + run-log; tail is fallback only when empty.
  if (!timeline.length) {
    for (const row of data.run_log_tail || []) {
      timeline.push({ ...row, source: row.source || "run-log" });
    }
  }
  timeline.sort((a, b) => (a.ts || "").localeCompare(b.ts || ""));

  const markerTs = restart?.created_at || "";
  const redoSteps = new Set(restart?.redo_steps || []);

  if (restart?.active && markerTs && redoSteps.size) {
    for (const row of timeline) {
      const step = row.step || "";
      const ts = row.ts || "";
      if (redoSteps.has(step) && ts && ts < markerTs) {
        row.display_state = "stale";
      } else if (!row.display_state) {
        row.display_state = row.result || "ok";
      }
    }

    const postByStep = new Map();
    for (const row of timeline) {
      const step = row.step || "";
      const ts = row.ts || "";
      if (!redoSteps.has(step) || !ts || ts < markerTs) continue;
      if (!postByStep.has(step)) postByStep.set(step, []);
      postByStep.get(step).push(row);
    }
    for (const rows of postByStep.values()) {
      rows.sort((a, b) => (a.ts || "").localeCompare(b.ts || ""));
      const latest = rows[rows.length - 1];
      const latestOk = latest.result !== "fail" && latest.result !== "retry";
      if (latestOk && rows.length > 1) {
        for (let i = 0; i < rows.length - 1; i++) {
          rows[i].display_state = "stale";
        }
      }
      for (const row of rows) {
        if (!row.display_state) row.display_state = row.result || "ok";
      }
    }
  }

  for (const row of timeline) {
    if (!row.display_state) row.display_state = row.result || "ok";
  }

  rebuildTimelineMeta(timeline);
  markSupersededPasses(timeline);
  data.timeline = timeline;

  if (restart?.active && markerTs && data.nodes) {
    for (const node of data.nodes) {
      if (!redoSteps.has(node.id)) continue;
      const passes = timeline.filter(
        (r) => r.step === node.id && (r.ts || "") >= markerTs
      );
      if (!passes.length) continue;
      passes.sort((a, b) => (a.ts || "").localeCompare(b.ts || ""));
      const latest = passes[passes.length - 1];
      const res = latest.result || "ok";
      if (res === "fail") {
        node.state = "fail";
        node.color = RESULT_COLORS.fail;
      } else if (res === "retry") {
        node.state = "retry";
        node.color = RESULT_COLORS.retry;
      } else {
        node.state = "ok";
        node.color = RESULT_COLORS.ok;
      }
    }
  }
}

function focusActualGraphOnLatest(graph) {
  const nodes = graph.nodes().filter((n) => {
    const kind = n.data("kind");
    return kind === "visit" || kind === "stale-bundle";
  });
  if (!nodes.length) return;
  graph.fit(nodes, 48);
  const zoom = graph.zoom();
  if (zoom > 1) {
    graph.zoom(1);
    graph.center(nodes);
  } else if (zoom < 0.72) {
    graph.zoom(0.72);
    graph.center(nodes);
  }
}

function buildActualDisplaySequence(timeline, collapsed) {
  const staleRows = staleTimelineRows(timeline);
  if (!staleRows.length || !collapsed) {
    return timeline.map((row) => ({ type: "visit", row }));
  }

  const items = [];
  let bundleInserted = false;
  for (const row of timeline) {
    if (rowDisplayState(row) === "stale") {
      if (!bundleInserted) {
        items.push({ type: "bundle", rows: staleRows });
        bundleInserted = true;
      }
      continue;
    }
    items.push({ type: "visit", row });
  }
  return items;
}

function updateStaleToggleUi(data) {
  const btn = document.getElementById("stale-toggle");
  if (!btn) return;
  const staleCount = staleTimelineRows(data?.timeline).length;
  const show = state.graphView === "actual" && staleCount > 0;
  btn.classList.toggle("hidden", !show);
  if (!show) return;
  btn.textContent = state.staleCollapsed
    ? `Развернуть отменённые (${staleCount})`
    : `Свернуть отменённые (${staleCount})`;
}

function setStaleCollapsed(collapsed) {
  state.staleCollapsed = collapsed;
  saveSelection();
  if (state.graph) {
    updateStaleToggleUi(state.graph);
    updateGraphViewHint(state.graph);
    renderGraph(state.graph);
  }
}

function updateGraphViewHint(data) {
  const el = document.getElementById("graph-view-hint");
  if (!el) return;
  const timeline = data?.timeline || [];
  const n = timeline.length;
  if (state.graphView === "timing") {
    el.textContent = "Строка — агент шага · под ним routing, как овал на «Факт»";
  } else if (state.graphView === "actual") {
    const staleCount = staleTimelineRows(timeline).length;
    const activeCount = n - staleCount;
    if (!n) {
      el.textContent = "Нет телеметрии для фактического графа";
    } else if (staleCount && state.staleCollapsed) {
      el.textContent =
        `${activeCount} актуальных · ${staleCount} отменённых (свёрнуты в блок)`;
    } else if (staleCount) {
      el.textContent =
        `${n} проходов · ${staleCount} отменённых · ${activeCount} актуальных`;
    } else {
      el.textContent = `${n} шагов — реальный порядок вызовов subagent`;
    }
  } else if (state.pipeline === "spec") {
    el.textContent =
      "Квадрат — шаг агента · овал — analyze-routing после этого шага";
  } else {
    el.textContent = "Шаги spec; hook/validate — в «Инфраструктура» справа";
  }
}

function updateInfraPanel() {
  const panel = document.getElementById("infra-panel");
  if (!panel) return;
  panel.classList.toggle("hidden", state.pipeline !== "spec");
}

function buildTargetElements(data) {
  const elements = [];
  const spec = data.pipeline === "spec";
  const bursts = spec ? routingBurstsByHost(data.timeline || []) : {};
  const liveHost = spec ? routingLiveHost(data) : null;
  const satelliteHosts = new Set(spec ? Object.keys(bursts) : []);
  if (liveHost) satelliteHosts.add(liveHost);

  const nodeById = {};
  for (const node of data.nodes || []) {
    nodeById[node.id] = node;
    if (spec && node.id === ROUTING_STEP) continue;
    const pos = node.position || { x: 0, y: 0 };
    elements.push({
      group: "nodes",
      data: {
        id: node.id,
        stepId: node.id,
        label: formatNodeLabel(node),
        color: node.color,
        state: node.state,
        kind: node.kind,
        ask: Boolean(node.ask),
      },
      position: pos,
    });
  }

  for (const host of satelliteHosts) {
    const parent = nodeById[host];
    if (!parent?.position) continue;
    const burst = bursts[host];
    const visual = satelliteVisual(host, data, burst, liveHost);
    elements.push({
      group: "nodes",
      data: {
        id: routingSatelliteId(host),
        stepId: ROUTING_STEP,
        hostStep: host,
        label: visual.label,
        color: visual.color,
        state: visual.state,
        kind: "routing-sat",
        seq: burst?.last?.seq || null,
      },
      position: {
        x: parent.position.x,
        y: parent.position.y + ROUTING_SATELLITE_DY,
      },
    });
    elements.push({
      group: "edges",
      data: {
        id: `e-sat-${host}`,
        source: host,
        target: routingSatelliteId(host),
        label: "",
        color: "#818cf8",
        kind: "routing-sat",
        traversed: burst ? "true" : "false",
      },
    });
  }

  for (const edge of data.edges || []) {
    if (edge.from === ROUTING_STEP || edge.to === ROUTING_STEP) continue;
    const kind = edge.kind || "main";
    const source = satelliteHosts.has(edge.from)
      ? routingSatelliteId(edge.from)
      : edge.from;
    elements.push({
      group: "edges",
      data: {
        id: edge.id,
        source,
        target: edge.to,
        label: targetEdgeLabel(edge),
        color: edge.color,
        kind,
        traversed: edge.traversed ? "true" : "false",
      },
    });
  }
  return elements;
}

function buildActualGraphElements(data) {
  const timeline = data.timeline || [];
  const sequence = buildActualDisplaySequence(timeline, state.staleCollapsed);
  const elements = [];
  const centerX = 360;
  const startY = 56;
  const domainStepY = 112;
  const satDy = 42;
  let y = startY;
  let prevNodeId = null;
  let currentHostId = null;
  let currentHostY = null;
  let routingBuf = [];

  function pushEdge(source, target, meta) {
    if (!source) return;
    let edgeColor = "#64748b";
    if (meta.stale) edgeColor = "#44403c";
    else if (meta.diverged) edgeColor = "#f97316";
    elements.push({
      group: "edges",
      data: {
        id: `e-${source}-${target}`,
        source,
        target,
        label: meta.diverged && !meta.stale ? "≠ schema" : "",
        color: edgeColor,
        stale: meta.stale ? "true" : "false",
        traversed: "true",
        kind: meta.kind || "main",
      },
    });
  }

  function flushRouting(meta) {
    if (!routingBuf.length) return;
    const last = routingBuf[routingBuf.length - 1];
    const displayState = rowDisplayState(last);
    const satId = currentHostId
      ? `routing-after-visit-${currentHostId}`
      : `routing-start-${last.seq}`;
    const satY = currentHostY != null ? currentHostY + satDy : y;
    elements.push({
      group: "nodes",
      data: {
        id: satId,
        stepId: ROUTING_STEP,
        seq: last.seq,
        hostStep: currentHostId,
        label: "analyze-routing",
        color: RESULT_COLORS[displayState] || ROUTING_SAT_COLOR,
        state: displayState,
        kind: "routing-sat",
      },
      position: { x: centerX, y: satY },
    });
    pushEdge(prevNodeId, satId, { ...meta, kind: "routing-sat", diverged: false });
    prevNodeId = satId;
    routingBuf = [];
    if (currentHostY == null) y += 56;
  }

  sequence.forEach((item) => {
    const edgeMeta = { stale: false, diverged: false };

    if (item.type === "bundle") {
      flushRouting(edgeMeta);
      const count = item.rows.length;
      const fromSeq = item.rows[0]?.seq;
      const toSeq = item.rows[item.rows.length - 1]?.seq;
      const nodeId = "stale-collapsed";
      elements.push({
        group: "nodes",
        data: {
          id: nodeId,
          stepId: nodeId,
          label:
            `Отменённые шаги\n${count} проходов (#${fromSeq}–#${toSeq})\n` +
            "▸ нажмите, чтобы развернуть",
          color: RESULT_COLORS.stale,
          state: "stale",
          kind: "stale-bundle",
          staleCount: count,
        },
        position: { x: centerX, y },
      });
      edgeMeta.stale = true;
      pushEdge(prevNodeId, nodeId, edgeMeta);
      prevNodeId = nodeId;
      currentHostId = null;
      currentHostY = null;
      y += domainStepY;
      return;
    }

    const row = item.row;
    if (isRoutingStep(row.step)) {
      routingBuf.push(row);
      return;
    }

    flushRouting(edgeMeta);
    const nodeId = `visit-${row.seq}`;
    const step = row.step || "?";
    const sub = row.subagent ? `\n${row.subagent}` : "";
    const ts = formatLocalTime(row.ts);
    const pass = row.pass ? ` · pass ${row.pass}` : "";
    const displayState = rowDisplayState(row);
    const staleLine =
      displayState === "stale"
        ? row.result === "fail" || row.result === "retry"
          ? `\n⛔ ${row.result} · устарел`
          : "\n⛔ устарел"
        : "";
    const label = `#${row.seq} ${step}${pass}\n${ts}${sub}${staleLine}`;
    edgeMeta.diverged = (row.divergence_kinds || []).includes("order_violation");
    edgeMeta.stale = displayState === "stale";

    elements.push({
      group: "nodes",
      data: {
        id: nodeId,
        stepId: step,
        seq: row.seq,
        label,
        color: RESULT_COLORS[displayState] || RESULT_COLORS.ok,
        state: displayState,
        kind: "visit",
        staleReason: displayState === "stale" ? staleReasonText(row) : "",
      },
      position: { x: centerX, y },
    });
    pushEdge(prevNodeId, nodeId, edgeMeta);
    prevNodeId = nodeId;
    currentHostId = nodeId;
    currentHostY = y;
    y += domainStepY;
  });
  flushRouting({ stale: false, diverged: false });
  return elements;
}

function renderTimeline(data) {
  const list = document.getElementById("timeline");
  list.innerHTML = "";
  const timeline = data.timeline || data.history || [];
  if (!timeline.length) {
    const li = document.createElement("li");
    li.textContent = "Проходов нет — запустите пайплайн";
    list.appendChild(li);
    return;
  }
  for (const row of timeline) {
    const li = document.createElement("li");
    li.dataset.step = row.step || "";
    li.dataset.seq = String(row.seq || "");
    const displayState = rowDisplayState(row);
    li.className = displayState;
    if (row.divergence_kinds?.length) li.classList.add("diverged");
    if (row.seq === selectedTimelineSeq || (row.step === selectedNodeId && !selectedTimelineSeq)) {
      li.classList.add("selected");
    }
    const sub = row.subagent ? ` → ${row.subagent}` : "";
    const ts = formatLocalDateTime(row.ts);
    const pass = row.pass ? `pass ${row.pass}` : "";
    const staleTag =
      displayState === "stale"
        ? row.result === "fail" || row.result === "retry"
          ? ` · ${row.result} · устарел`
          : " · устарел"
        : "";
    let line = `#${row.seq || "?"} · ${pass} · ${row.step}${sub} · ${ts}${staleTag}`;
    if (displayState === "stale") {
      line += `\n${staleReasonText(row)}`;
    }
    li.textContent = line;
    li.addEventListener("click", () => {
      selectedElementId = null;
      selectedNodeId = row.step;
      selectedTimelineSeq = row.seq;
      highlightNode(selectedNodeId, selectedTimelineSeq);
      showNodePanel(selectedNodeId);
    });
    list.appendChild(li);
  }
}

function applyActualGraphHighlights(graph, data) {
  graph.nodes().removeClass("stale-visit diverged");
  graph.edges().removeClass("stale-edge");
  const bundle = graph.getElementById("stale-collapsed");
  if (bundle.length) bundle.addClass("stale-visit");

  if (state.staleCollapsed) {
    graph.edges().forEach((edge) => {
      if (edge.data("stale") === "true") edge.addClass("stale-edge");
    });
    return;
  }

  const timeline = data.timeline || [];
  for (const row of timeline) {
    const node = graph.getElementById(`visit-${row.seq}`);
    if (!node.length) continue;
    if (rowDisplayState(row) === "stale") node.addClass("stale-visit");
    if (row.divergence_kinds?.length) node.addClass("diverged");
  }
  graph.edges().forEach((edge) => {
    if (edge.data("stale") === "true") edge.addClass("stale-edge");
  });
}

function applyDivergenceHighlights(graph, data) {
  graph.nodes().removeClass("expected diverged");
  const summary = data.divergence?.summary;
  if (!summary || data.pipeline !== "spec") return;

  const expectedStep = summary.expected_step;
  const cur = data.current;
  const alreadyRunning =
    cur?.status === "running" && cur?.step === expectedStep;
  if (expectedStep && summary.must_continue && !alreadyRunning) {
    if (expectedStep === ROUTING_STEP) {
      const host = routingLiveHost(data);
      const sat = host ? graph.getElementById(routingSatelliteId(host)) : graph.collection();
      if (sat.length) sat.addClass("expected");
    } else {
      const expectedNode = graph.getElementById(expectedStep);
      if (expectedNode.length) expectedNode.addClass("expected");
    }
  }

  const items = data.divergence?.items || [];
  const divergedSteps = new Set();
  for (const item of items) {
    if (item.actual_step) divergedSteps.add(item.actual_step);
    if (item.to_step) divergedSteps.add(item.to_step);
    if (item.step) divergedSteps.add(item.step);
  }
  for (const stepId of divergedSteps) {
    const node = graph.getElementById(stepId);
    if (node.length) node.addClass("diverged");
    else graph.nodes(`[stepId = "${stepId}"]`).addClass("diverged");
  }

  const current = data.current;
  if (current?.node_id && items.some((i) => i.kind === "live_subagent_mismatch")) {
    const node = graph.getElementById(current.node_id);
    if (node.length) node.addClass("diverged");
  }
}

function resizeGraphCanvas(graph, viewMode) {
  const cyEl = document.getElementById("cy");
  const nodes = graph.nodes();
  if (!nodes.length) {
    cyEl.style.height = "100%";
    return;
  }
  let minY = Infinity;
  let maxY = -Infinity;
  nodes.forEach((node) => {
    const y = node.position("y");
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
  });
  const pad = viewMode === "actual" ? 120 : 160;
  const needed = maxY - minY + pad;
  cyEl.style.height = `${Math.max(needed, 420)}px`;
  graph.resize();
}

function highlightNode(nodeId, timelineSeq) {
  const graph = cy;
  if (!graph) return;
  graph.nodes().removeClass("selected");
  if (!nodeId && !timelineSeq && !selectedElementId) return;

  if (selectedElementId) {
    const el = graph.getElementById(selectedElementId);
    if (el.length) {
      el.addClass("selected");
      return;
    }
  }

  if (state.graphView === "actual") {
    if (nodeId === "stale-collapsed") {
      const el = graph.getElementById("stale-collapsed");
      if (el.length) el.addClass("selected");
      return;
    }
    if (timelineSeq) {
      const el = graph.getElementById(`visit-${timelineSeq}`);
      if (el.length) {
        el.addClass("selected");
        return;
      }
      graph.nodes(`[seq = "${timelineSeq}"]`).addClass("selected");
    } else if (nodeId) {
      graph.nodes(`[stepId = "${nodeId}"]`).addClass("selected");
    }
    return;
  }

  if (nodeId) {
    const el = graph.getElementById(nodeId);
    if (el.length) el.addClass("selected");
    else graph.nodes(`[stepId = "${nodeId}"]`).addClass("selected");
  }
}

function bindGraphInteractions(graph) {
  if (graphInteractionsBound) return;
  graphInteractionsBound = true;

  graph.on("tap", "node", (evt) => {
    const node = evt.target;
    if (isSchemaMode()) {
      selectedElementId = node.id();
      selectedNodeId = node.id();
      selectedTimelineSeq = null;
      highlightNode(selectedNodeId, null);
      showPackNodeSummary(selectedNodeId);
      hideTooltip();
      return;
    }
    if (node.data("kind") === "stale-bundle") {
      setStaleCollapsed(false);
      hideTooltip();
      return;
    }
    const stepId = node.data("stepId") || node.id();
    selectedElementId = node.id();
    selectedNodeId = stepId;
    selectedTimelineSeq = node.data("seq") || null;
    highlightNode(selectedNodeId, selectedTimelineSeq);
    showNodePanel(selectedNodeId);
    highlightTimelineRow(selectedNodeId, selectedTimelineSeq);
    hideTooltip();
  });

  function tooltipForNode(nodeId, cyNode) {
    if (state.screenMode === "schema") {
      const node = packNodeById(nodeId);
      return node ? packNodeTooltip(node) : nodeId;
    }
    const stepId = cyNode?.data("stepId") || nodeId;
    const detail = nodeDetails[stepId];
    const node = (state.graph?.nodes || []).find((n) => n.id === stepId);
    let text = detail?.tooltip || detail?.hint || stepId;
    if (cyNode?.data("kind") === "stale-bundle") {
      text = `Отменённые шаги · ${cyNode.data("staleCount")} проходов · клик — развернуть`;
    } else if (cyNode?.data("kind") === "routing-sat") {
      const host = cyNode.data("hostStep");
      text = host
        ? `analyze-routing после ${host}`
        : "analyze-routing";
    } else if (cyNode?.data("kind") === "visit") {
      text = `#${cyNode.data("seq")} ${stepId} · ${text}`;
      const reason = cyNode.data("staleReason");
      if (reason) text += `\n${reason}`;
    } else if (node?.visit_count > 0) {
      text = `${node.visit_count} проход(ов) · ${text}`;
    }
    const issues = divergencesForStep(stepId).length;
    if (issues > 0) {
      text += " · ⚠ замеч.";
    }
    return text;
  }

  graph.on("mouseover", "node", (evt) => {
    const node = evt.target;
    showTooltip(
      tooltipForNode(node.id(), node),
      evt.originalEvent.clientX,
      evt.originalEvent.clientY
    );
  });

  graph.on("mousemove", "node", (evt) => {
    const node = evt.target;
    showTooltip(
      tooltipForNode(node.id(), node),
      evt.originalEvent.clientX,
      evt.originalEvent.clientY
    );
  });

  graph.on("mouseout", "node", () => hideTooltip());

  graph.on("dragfree", "node", () => {
    if (!isSchemaMode()) return;
    captureSchemaPositions();
  });

  graph.on("tap", (evt) => {
    if (evt.target === graph) {
      selectedNodeId = null;
      selectedElementId = null;
      selectedTimelineSeq = null;
      highlightNode(null, null);
      clearNodePanel();
      highlightTimelineRow(null, null);
    }
  });
}

function loadSelection() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveSelection() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      slug: state.slug,
      pipeline: state.pipeline,
      graphView: state.graphView,
      staleCollapsed: state.staleCollapsed,
      screenMode: state.screenMode,
      packId: state.packId,
    })
  );
}

function isSchemaMode() {
  return state.screenMode === "schema";
}

function emptyPackDraft() {
  return { positions: {}, extraNodes: [], deletedIds: [] };
}

function loadDraftStore() {
  try {
    const parsed = JSON.parse(localStorage.getItem(DRAFT_STORAGE_KEY) || "{}");
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return { packs: {} };
    if (!parsed.packs || typeof parsed.packs !== "object") return { packs: {} };
    return parsed;
  } catch {
    return { packs: {} };
  }
}

function saveDraftStore(store) {
  localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(store));
}

function getPackDraft(packId) {
  const store = loadDraftStore();
  const raw = store.packs?.[packId];
  if (!raw || typeof raw !== "object") return emptyPackDraft();
  return {
    positions: raw.positions && typeof raw.positions === "object" ? raw.positions : {},
    extraNodes: Array.isArray(raw.extraNodes) ? raw.extraNodes : [],
    deletedIds: Array.isArray(raw.deletedIds) ? raw.deletedIds : [],
  };
}

function setPackDraft(packId, draft) {
  const store = loadDraftStore();
  store.packs = store.packs || {};
  store.packs[packId] = {
    positions: draft.positions || {},
    extraNodes: draft.extraNodes || [],
    deletedIds: draft.deletedIds || [],
  };
  saveDraftStore(store);
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function kebabAgentId(name) {
  const slug = String(name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "agent";
}

function missingClisFor(agent) {
  const by = state.agentsByCli || {};
  const clis = Object.keys(by).length ? Object.keys(by) : SCHEMA_CLIS;
  if (!clis.some((cli) => Array.isArray(by[cli]))) return [];
  return clis.filter((cli) => !(by[cli] || []).includes(agent));
}

function applyDraftToPack(basePack, draft) {
  const pack = cloneJson(basePack || { graph: { nodes: [], edges: [] } });
  pack.graph = pack.graph || {};
  const deleted = new Set(draft.deletedIds || []);
  const nodes = (pack.graph.nodes || []).filter((node) => node && !deleted.has(node.id));
  const existing = new Set(nodes.map((node) => node.id));
  for (const extra of draft.extraNodes || []) {
    if (!extra?.id || existing.has(extra.id)) continue;
    nodes.push({
      id: extra.id,
      label: extra.label || extra.id,
      kind: extra.kind || "step",
      subagent: extra.subagent || extra.id,
      draft: true,
    });
    existing.add(extra.id);
    deleted.delete(extra.id);
  }
  pack.graph.nodes = nodes;
  pack.graph.edges = (pack.graph.edges || []).filter(
    (edge) => edge && existing.has(edge.from) && existing.has(edge.to)
  );
  return pack;
}

function uniqueSchemaNodeId(base) {
  const used = new Set((state.pack?.graph?.nodes || []).map((node) => node.id));
  if (!used.has(base)) return base;
  let i = 2;
  while (used.has(`${base}-${i}`)) i += 1;
  return `${base}-${i}`;
}

function schemaCanvasPosition(clientX, clientY) {
  const graph = initCytoscape();
  const container = graph?.container() || document.getElementById("cy");
  const rect = container.getBoundingClientRect();
  const pan = graph ? graph.pan() : { x: 0, y: 0 };
  const zoom = graph ? graph.zoom() : 1;
  return {
    x: (clientX - rect.left - pan.x) / zoom,
    y: (clientY - rect.top - pan.y) / zoom,
  };
}

function captureSchemaPositions() {
  if (!cy || !isSchemaMode()) return;
  const draft = getPackDraft(state.packId);
  draft.positions = draft.positions || {};
  cy.nodes().forEach((node) => {
    const pos = node.position();
    draft.positions[node.id()] = { x: pos.x, y: pos.y };
  });
  setPackDraft(state.packId, draft);
}

function setSchemaNodeActionsVisible(show) {
  const el = document.getElementById("schema-node-actions");
  if (el) el.classList.toggle("hidden", !show);
}

function showPaletteNotice(text) {
  const el = document.getElementById("palette-notice");
  if (!el) return;
  el.textContent = text || "";
  el.classList.toggle("hidden", !text);
}

function packPositions(pack) {
  const graph = pack?.graph || {};
  const nodes = graph.nodes || [];
  const layout = layoutPackPositions(nodes, graph.edges || [], graph.orchestrator || nodes[0]?.id || "");
  const saved = getPackDraft(state.packId).positions || {};
  const positions = {};
  for (const node of nodes) {
    positions[node.id] = saved[node.id] || layout[node.id] || { x: 80, y: 80 };
  }
  return positions;
}

function packNodeClasses(node) {
  const classes = [];
  if (node.draft) classes.push("draft-added");
  if (node.subagent && missingClisFor(node.subagent).length) classes.push("cli-missing");
  return classes.join(" ");
}

function packNodeById(nodeId) {
  return (state.pack?.graph?.nodes || []).find((node) => node.id === nodeId) || null;
}

function formatPackNodeLabel(node) {
  const lines = [node.label || node.id];
  if (node.cycle) lines.push("cycle");
  else if (node.ask) lines.push("ask");
  if (node.kind === "meta") lines.push("meta");
  return lines.join("\n");
}

function packNodeTooltip(node) {
  const lines = [node.label || node.id, `id: ${node.id}`, `kind: ${node.kind || "step"}`];
  if (node.subagent) lines.push(`subagent: ${node.subagent}`);
  else if (node.kind === "orchestrator") lines.push("оркестратор");
  if (node.draft) lines.push("черновик: клетка с палитры, не в YAML");
  const missing = node.subagent ? missingClisFor(node.subagent) : [];
  if (missing.length) lines.push(`нет в CLI: ${missing.join(", ")}`);
  if (node.ask) lines.push("ask: пауза на этой клетке; apply без смены шага");
  if (node.cycle && typeof node.cycle === "object") {
    const cycle = node.cycle;
    lines.push("cycle: составная клетка (внутренности — фаза 4)");
    if (cycle.assemble) lines.push(`assemble: ${cycle.assemble}`);
    if (cycle.close) lines.push(`close: ${cycle.close}`);
    if (cycle.param) lines.push(`param: ${cycle.param}`);
  }
  return lines.join("\n");
}

function packEdgeLabel(edge) {
  return edge.label || edge.condition_label || edge.condition || "";
}

function packNodeColor(node) {
  if (node.cycle) return PACK_NODE_COLORS.cycle;
  return PACK_NODE_COLORS[node.kind] || PACK_NODE_COLORS.step;
}

function layoutPackPositions(nodes, edges, orchestratorId) {
  const ids = nodes.map((node) => node.id);
  const idSet = new Set(ids);
  const mainOut = Object.fromEntries(ids.map((id) => [id, []]));
  const anyOut = Object.fromEntries(ids.map((id) => [id, []]));
  for (const edge of edges) {
    if (!idSet.has(edge.from) || !idSet.has(edge.to)) continue;
    anyOut[edge.from].push(edge.to);
    if ((edge.kind || "main") === "main") mainOut[edge.from].push(edge.to);
  }

  const rank = {};
  if (idSet.has(orchestratorId)) rank[orchestratorId] = 0;
  const mainQueue = idSet.has(orchestratorId) ? [orchestratorId] : [];
  const mainSeen = new Set();
  while (mainQueue.length) {
    const id = mainQueue.shift();
    if (mainSeen.has(id)) continue;
    mainSeen.add(id);
    for (const to of mainOut[id] || []) {
      rank[to] = Math.max(rank[to] || 0, (rank[id] || 0) + 1);
      mainQueue.push(to);
    }
  }

  const restQueue = ids.filter((id) => rank[id] !== undefined);
  while (restQueue.length) {
    const id = restQueue.shift();
    for (const to of anyOut[id] || []) {
      if (rank[to] === undefined) {
        rank[to] = (rank[id] || 0) + 1;
        restQueue.push(to);
      }
    }
  }
  for (const id of ids) {
    if (rank[id] === undefined) rank[id] = 0;
  }

  const mainChain = [];
  const chainSeen = new Set();
  let cursor = idSet.has(orchestratorId) ? orchestratorId : ids[0];
  while (cursor && !chainSeen.has(cursor)) {
    chainSeen.add(cursor);
    mainChain.push(cursor);
    cursor = (mainOut[cursor] || [])[0];
  }
  const mainSet = new Set(mainChain);

  const byRank = {};
  for (const id of ids) {
    (byRank[rank[id]] ||= []).push(id);
  }
  for (const row of Object.values(byRank)) {
    row.sort((a, b) => {
      const aMain = mainSet.has(a) ? 0 : 1;
      const bMain = mainSet.has(b) ? 0 : 1;
      if (aMain !== bMain) return aMain - bMain;
      return ids.indexOf(a) - ids.indexOf(b);
    });
  }

  const colW = 230;
  const rowH = 118;
  const originX = 280;
  const originY = 72;
  const positions = {};
  const maxRank = Math.max(0, ...Object.keys(byRank).map(Number));
  for (let r = 0; r <= maxRank; r += 1) {
    const row = byRank[r] || [];
    row.forEach((id, index) => {
      const onMain = mainSet.has(id);
      const extraIndex = onMain ? 0 : mainSet.has(row[0]) ? index : index + 1;
      positions[id] = {
        x: originX + colW * extraIndex,
        y: originY + r * rowH,
      };
    });
  }
  return positions;
}

function buildPackGraphElements(pack) {
  const graph = pack?.graph || {};
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  const positions = packPositions(pack);
  const elements = [];

  for (const node of nodes) {
    const kind = node.kind || "step";
    elements.push({
      group: "nodes",
      data: {
        id: node.id,
        label: formatPackNodeLabel(node),
        color: packNodeColor(node),
        kind,
        askFlag: node.ask ? "true" : "false",
        cycleFlag: node.cycle ? "true" : "false",
      },
      position: positions[node.id] || { x: 80, y: 80 },
      grabbable: true,
      classes: packNodeClasses(node),
    });
  }

  const usedEdgeIds = new Set();
  edges.forEach((edge, index) => {
    const kind = edge.kind || "main";
    let id = edge.id || `e-${edge.from}-${edge.to}-${index}`;
    if (usedEdgeIds.has(id)) id = `${id}-${index}`;
    usedEdgeIds.add(id);
    elements.push({
      group: "edges",
      data: {
        id,
        source: edge.from,
        target: edge.to,
        label: packEdgeLabel(edge),
        color: PACK_EDGE_COLORS[kind] || PACK_EDGE_COLORS.main,
        kind,
      },
      classes: "schema-edge",
    });
  });
  return elements;
}

function showPackNodeSummary(nodeId) {
  const el = document.getElementById("step-detail");
  const node = packNodeById(nodeId);
  if (!el) return;
    if (!node) {
    el.textContent = `Нет клетки «${nodeId}».`;
    setSchemaNodeActionsVisible(false);
    return;
  }
  const lines = [
    `id: ${node.id}`,
    `label: ${node.label || node.id}`,
    `kind: ${node.kind || "step"}`,
  ];
  if (node.subagent != null) lines.push(`subagent: ${node.subagent}`);
  if (node.draft) lines.push("черновик: с палитры, не в YAML");
  const missing = node.subagent ? missingClisFor(node.subagent) : [];
  if (missing.length) lines.push(`нет в CLI: ${missing.join(", ")} — клетку всё равно можно держать`);
  if (node.ask) lines.push("ask: true — пауза; apply без смены шага");
  if (node.cycle && typeof node.cycle === "object") {
    lines.push("cycle: составная клетка");
    for (const key of ["persistent", "assemble", "param", "folder", "out", "item_file", "close"]) {
      if (node.cycle[key] != null && node.cycle[key] !== "") {
        lines.push(`  ${key}: ${node.cycle[key]}`);
      }
    }
    if (!node.cycle.calls) lines.push("  calls: (нет — runtime подставит каталог)");
  }
  el.textContent = lines.join("\n");
  setSchemaNodeActionsVisible(true);
}

function renderPackSummary(pack) {
  const el = document.getElementById("pack-summary");
  const badge = document.getElementById("pack-badge");
  const graph = pack?.graph || {};
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  const draft = getPackDraft(state.packId);
  const extra = (draft.extraNodes || []).length;
  const removed = (draft.deletedIds || []).length;
  const draftBits = [];
  if (extra) draftBits.push(`+${extra} с палитры`);
  if (removed) draftBits.push(`−${removed} удалено`);
  const text = [
    `id: ${pack?.id || "—"}`,
    `label: ${graph.label || "—"}`,
    `оркестратор: ${graph.orchestrator || "—"}`,
    `клеток: ${nodes.length} · стрелок: ${edges.length}`,
    extra || removed ? `черновик: ${draftBits.join(", ")}` : "черновик: координаты в браузере",
  ].join("\n");
  if (el) el.textContent = text;
  if (badge) {
    const mark = extra || removed ? " · черновик" : "";
    badge.textContent = `${pack?.id || "—"} · ${nodes.length} клеток${mark}`;
  }
}

function renderPackGraph(pack, opts = {}) {
  const empty = document.getElementById("empty-state");
  const nodes = pack?.graph?.nodes || [];
  const noGraph = !nodes.length;
  empty.classList.toggle("hidden", !noGraph);
  document.getElementById("cy").style.visibility = noGraph ? "hidden" : "visible";

  state.pack = pack;
  renderPackSummary(pack);

  const graph = initCytoscape();
  if (!graph) return;
  graph.autoungrabify(false);

  const elements = buildPackGraphElements(pack);
  graph.elements().remove();
  if (!elements.length) {
    setSchemaNodeActionsVisible(false);
    return;
  }
  graph.add(elements);
  graph.nodes().grabify();
  resizeGraphCanvas(graph, "target");
  if (!opts.skipFit) {
    graph.fit(graph.nodes(), 48);
    const zoom = graph.zoom();
    if (zoom > 1) {
      graph.zoom(1);
      graph.center(graph.nodes());
    } else if (zoom < 0.62) {
      graph.zoom(0.62);
      graph.center(graph.nodes());
    }
  }
  captureSchemaPositions();

  if (selectedNodeId && packNodeById(selectedNodeId)) {
    highlightNode(selectedNodeId, null);
    showPackNodeSummary(selectedNodeId);
  } else {
    selectedNodeId = null;
    selectedElementId = null;
    setSchemaNodeActionsVisible(false);
    const el = document.getElementById("step-detail");
    if (el) el.textContent = "Кликните клетку или перетащите агента слева. YAML не пишется.";
  }
}

let packLoadSeq = 0;

async function loadPackGraph() {
  const seq = ++packLoadSeq;
  const packId = state.packId;
  const empty = document.getElementById("empty-state");
  const emptyText = document.getElementById("schema-empty-text");
  if (emptyText) emptyText.textContent = "Загрузка схемы пака…";
  try {
    const res = await fetch(`/api/pack?pipeline=${encodeURIComponent(packId)}`);
    const data = await parseJsonResponse(res);
    if (seq !== packLoadSeq || state.packId !== packId) return;
    if (!res.ok) {
      throw new Error(data.error || `HTTP ${res.status}`);
    }
    clearError();
    state.packBase = data;
    renderPackGraph(applyDraftToPack(data, getPackDraft(packId)));
  } catch (err) {
    if (seq !== packLoadSeq || state.packId !== packId) return;
    state.pack = null;
    state.packBase = null;
    if (cy) cy.elements().remove();
    document.getElementById("cy").style.visibility = "hidden";
    empty.classList.remove("hidden");
    if (emptyText) emptyText.textContent = err.message || String(err);
    renderPackSummary(null);
    setSchemaNodeActionsVisible(false);
    showError(`Схема пака: ${err.message || err}`);
  }
}

function addDraftAgentNode(agentName, position) {
  if (!state.packBase && !state.pack) {
    showPaletteNotice("Сначала дождитесь загрузки пака.");
    return;
  }
  const agent = String(agentName || "").trim();
  if (!agent) return;
  const missing = missingClisFor(agent);
  const id = uniqueSchemaNodeId(kebabAgentId(agent));
  const node = {
    id,
    label: agent,
    kind: "step",
    subagent: agent,
  };
  const draft = getPackDraft(state.packId);
  draft.extraNodes = [...(draft.extraNodes || []).filter((item) => item.id !== id), node];
  draft.deletedIds = (draft.deletedIds || []).filter((item) => item !== id);
  draft.positions = { ...(draft.positions || {}), [id]: position };
  setPackDraft(state.packId, draft);

  if (!state.pack) {
    state.pack = applyDraftToPack(state.packBase || { id: state.packId, graph: { nodes: [], edges: [] } }, draft);
  } else {
    state.pack.graph = state.pack.graph || { nodes: [], edges: [] };
    state.pack.graph.nodes = state.pack.graph.nodes || [];
    if (!state.pack.graph.nodes.some((item) => item.id === id)) {
      state.pack.graph.nodes.push({ ...node, draft: true });
    }
  }

  const graph = initCytoscape();
  const empty = document.getElementById("empty-state");
  empty.classList.add("hidden");
  document.getElementById("cy").style.visibility = "visible";
  graph.autoungrabify(false);
  const displayNode = { ...node, draft: true };
  graph.add({
    group: "nodes",
    data: {
      id,
      label: formatPackNodeLabel(displayNode),
      color: packNodeColor(displayNode),
      kind: "step",
      askFlag: "false",
      cycleFlag: "false",
    },
    position,
    grabbable: true,
    classes: packNodeClasses(displayNode),
  });
  graph.getElementById(id).grabify();
  selectedNodeId = id;
  selectedElementId = id;
  highlightNode(id, null);
  showPackNodeSummary(id);
  renderPackSummary(state.pack);
  resizeGraphCanvas(graph, "target");
  captureSchemaPositions();
  if (missing.length) {
    showPaletteNotice(
      `Агента «${agent}» нет в ${missing.join(", ")}. Клетка создана (черновик, диск не пишется).`
    );
  } else {
    showPaletteNotice("");
  }
}

function deleteSchemaNode(nodeId) {
  if (!nodeId || !isSchemaMode()) return;
  const draft = getPackDraft(state.packId);
  const extraIds = new Set((draft.extraNodes || []).map((node) => node.id));
  if (extraIds.has(nodeId)) {
    draft.extraNodes = (draft.extraNodes || []).filter((node) => node.id !== nodeId);
  } else {
    draft.deletedIds = Array.from(new Set([...(draft.deletedIds || []), nodeId]));
  }
  if (draft.positions) delete draft.positions[nodeId];
  setPackDraft(state.packId, draft);

  if (state.pack?.graph) {
    state.pack.graph.nodes = (state.pack.graph.nodes || []).filter((node) => node.id !== nodeId);
    state.pack.graph.edges = (state.pack.graph.edges || []).filter(
      (edge) => edge.from !== nodeId && edge.to !== nodeId
    );
  }
  if (cy) {
    const node = cy.getElementById(nodeId);
    if (node.length) {
      node.connectedEdges().remove();
      node.remove();
    }
  }
  if (selectedNodeId === nodeId) {
    selectedNodeId = null;
    selectedElementId = null;
    highlightNode(null, null);
    clearNodePanel();
  }
  renderPackSummary(state.pack);
  captureSchemaPositions();
}

function agentFromDragEvent(event) {
  const dt = event.dataTransfer;
  if (!dt) return "";
  return (dt.getData(PALETTE_DRAG_TYPE) || dt.getData("text/plain") || "").trim();
}

function setPaletteDropReady(on) {
  document.getElementById("graph-panel")?.classList.toggle("drop-ready", Boolean(on));
}

function bindSchemaPalette() {
  const list = document.getElementById("palette-agents");
  const filter = document.getElementById("palette-filter");
  const skillsEl = document.getElementById("palette-skills");
  const skillsCount = document.getElementById("palette-skills-count");
  const dropRoot = document.getElementById("graph-panel");
  if (!list || !dropRoot) return;

  function renderAgents() {
    const query = (filter?.value || "").trim().toLowerCase();
    list.innerHTML = "";
    const agents = state.catalogAgents.filter((name) => !query || name.toLowerCase().includes(query));
    if (!agents.length) {
      const empty = document.createElement("p");
      empty.className = "sidebar-hint";
      empty.textContent = state.catalogAgents.length ? "Нет совпадений." : "Каталог агентов пуст.";
      list.appendChild(empty);
      return;
    }
    for (const name of agents) {
      const missing = missingClisFor(name);
      const card = document.createElement("div");
      card.className = `palette-card${missing.length ? " is-partial" : ""}`;
      card.draggable = true;
      card.dataset.agent = name;
      card.setAttribute("role", "listitem");
      const title = document.createElement("span");
      title.className = "palette-card-name";
      title.textContent = name;
      card.appendChild(title);
      const clis = document.createElement("span");
      clis.className = "palette-clis";
      const present = Object.keys(state.agentsByCli).length
        ? Object.keys(state.agentsByCli)
        : SCHEMA_CLIS;
      for (const cli of present) {
        const badge = document.createElement("span");
        const isMissing = missing.includes(cli);
        badge.className = `palette-cli${isMissing ? " is-missing" : ""}`;
        badge.textContent = isMissing ? `нет ${cli}` : cli;
        clis.appendChild(badge);
      }
      card.appendChild(clis);
      if (missing.length) {
        card.title = `Нет в ${missing.join(", ")}. Клетку всё равно можно поставить.`;
      } else {
        card.title = "Перетащите на холст — клетка kind=step";
      }
      card.addEventListener("dragstart", (event) => {
        try {
          event.dataTransfer.setData(PALETTE_DRAG_TYPE, name);
        } catch {
          /* some browsers only allow text/plain */
        }
        event.dataTransfer.setData("text/plain", name);
        event.dataTransfer.effectAllowed = "copy";
      });
      list.appendChild(card);
    }
  }

  if (skillsEl) {
    skillsEl.innerHTML = "";
    for (const skill of state.catalogSkills) {
      const li = document.createElement("li");
      li.textContent = skill;
      skillsEl.appendChild(li);
    }
  }
  if (skillsCount) skillsCount.textContent = state.catalogSkills.length ? `(${state.catalogSkills.length})` : "";

  filter?.addEventListener("input", renderAgents);
  renderAgents();

  dropRoot.addEventListener("dragenter", (event) => {
    if (!isSchemaMode()) return;
    event.preventDefault();
    setPaletteDropReady(true);
  });
  dropRoot.addEventListener("dragover", (event) => {
    if (!isSchemaMode()) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
    setPaletteDropReady(true);
  });
  dropRoot.addEventListener("dragleave", (event) => {
    if (!dropRoot.contains(event.relatedTarget)) setPaletteDropReady(false);
  });
  dropRoot.addEventListener("drop", (event) => {
    if (!isSchemaMode()) return;
    event.preventDefault();
    setPaletteDropReady(false);
    const agent = agentFromDragEvent(event);
    if (!agent) return;
    addDraftAgentNode(agent, schemaCanvasPosition(event.clientX, event.clientY));
  });
}

function bindSchemaDraftActions() {
  document.getElementById("schema-delete-node")?.addEventListener("click", () => {
    if (selectedNodeId) deleteSchemaNode(selectedNodeId);
  });
  document.addEventListener("keydown", (event) => {
    if (!isSchemaMode()) return;
    if (event.key !== "Delete" && event.key !== "Backspace") return;
    if (event.target?.closest?.("input, textarea, select, [contenteditable]")) return;
    if (!selectedNodeId) return;
    event.preventDefault();
    deleteSchemaNode(selectedNodeId);
  });
}

function fillPackTabs() {
  const nav = document.getElementById("pack-tabs");
  if (!nav) return;
  nav.innerHTML = "";
  const pipelines = state.catalogPipelines.length
    ? state.catalogPipelines
    : [
        { id: "spec", label: "Spec pipeline" },
        { id: "calibration", label: "Calibration" },
      ];
  state.catalogPipelines = pipelines;
  for (const item of pipelines) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "tab";
    btn.dataset.pack = item.id;
    btn.textContent = item.id;
    btn.title = item.label || item.id;
    btn.addEventListener("click", () => {
      if (state.packId === item.id) return;
      captureSchemaPositions();
      state.packId = item.id;
      setActivePackTab();
      saveSelection();
      loadPackGraph();
    });
    nav.appendChild(btn);
  }
  const known = new Set(pipelines.map((item) => item.id));
  if (!known.has(state.packId)) {
    state.packId = pipelines[0]?.id || "spec";
  }
  setActivePackTab();
}

function setActivePackTab() {
  document.querySelectorAll("#pack-tabs .tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.pack === state.packId);
  });
}

function applyScreenModeChrome() {
  const schema = isSchemaMode();
  document.body.classList.toggle("screen-schema", schema);
  document.body.classList.toggle("screen-run", !schema);
  document.querySelectorAll("#screen-mode-tabs .tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.screen === state.screenMode);
  });
  const heading = document.getElementById("step-heading");
  const hint = document.getElementById("step-hint");
  if (heading) heading.textContent = schema ? "Клетка" : "Выбранный шаг";
  if (hint) {
    hint.textContent = schema
      ? "Перетащите агента слева. Двигать и Delete — черновик, YAML не пишется."
      : "Клик по узлу на графе. Жёлтая/оранжевая рамка — есть замечания.";
  }
  if (schema) {
    document.getElementById("legend")?.classList.remove("hidden");
    document.getElementById("graph-scroll")?.classList.remove("hidden-for-timing");
    document.getElementById("timing-panel")?.classList.add("hidden");
  } else {
    setGraphViewTabs();
  }
  if (cy) cy.autoungrabify(false);
}

function setScreenMode(mode) {
  const next = mode === "schema" ? "schema" : "run";
  const changed = state.screenMode !== next;
  state.screenMode = next;
  saveSelection();
  if (changed && next === "run") captureSchemaPositions();
  applyScreenModeChrome();
  if (next === "schema") {
    disconnectStream();
    selectedTimelineSeq = null;
    if (changed) {
      selectedNodeId = null;
      selectedElementId = null;
    }
    loadPackGraph();
    return;
  }
  if (cy) cy.autoungrabify(false);
  connectStream();
}

function streamUrl() {
  const params = new URLSearchParams({
    slug: state.slug,
    pipeline: state.pipeline,
  });
  return `/api/stream?${params}`;
}

function setConnection(status, text) {
  const el = document.getElementById("connection");
  el.textContent = text;
  el.className = `badge conn ${status} run-only`;
}

function setActiveTab(pipeline) {
  document.querySelectorAll("#pipeline-tabs .tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.pipeline === pipeline);
  });
  updateInfraPanel();
}

function renderGraph(data) {
  if (isSchemaMode()) return;
  const empty = document.getElementById("empty-state");
  const noSlug = !data.slug;
  const nodes = data.nodes || [];

  empty.classList.toggle("hidden", !noSlug);
  document.getElementById("cy").style.visibility = noSlug ? "hidden" : "visible";

  const runEl = document.getElementById("run-id");
  if (data.pipeline === "calibration") {
    const cal = data.calibration_run_id ? `cal ${data.calibration_run_id}` : "cal —";
    const agent = data.run_id ? ` · agent ${data.run_id}` : "";
    runEl.textContent = cal + agent;
  } else if (data.history_aggregate && (data.agent_run_ids || []).length > 1) {
    const runs = (data.agent_run_ids || []).join("→");
    runEl.textContent = `runs ${runs} · live ${data.run_id || "?"}`;
  } else {
    runEl.textContent = data.run_id || "—";
  }

  normalizeTimelineDisplay(data);
  state.graph = data;

  if (noSlug) {
    document.getElementById("timeline").innerHTML = "";
    document.getElementById("stats").textContent = "—";
    clearNodePanel();
    renderTimingsPanel(null);

    if (cy) cy.elements().remove();
    return;
  }

  setGraphViewTabs();
  updateGraphViewHint(data);

  if (state.graphView === "timing") {
    renderTimingsPanel(data.timings, data.timeline);
    renderDispatchPanel(data);
    renderSessionOutcomeBanner(data);
    renderDivergenceBanner(data.divergence?.summary);
    renderValidationBanner(data.validation);
    renderValidationPanel(data.pipeline === "spec" ? data.validation : null);
    updateInfraPanel();
    renderTimeline(data);
    document.getElementById("stats").textContent = JSON.stringify(
      {
        pipeline: data.pipeline_label || data.pipeline,
        timings: data.timings,
        history_sources: data.history_sources,
        updated_at: data.updated_at,
      },
      null,
      2
    );
    return;
  }

  const graph = initCytoscape();
  if (!graph) return;
  graph.autoungrabify(false);

  if (data.error && nodes.length === 0) {
    document.getElementById("dispatch").textContent = data.error;
  }

  nodeDetails = {};
  for (const node of nodes) {
    if (node.detail) nodeDetails[node.id] = node.detail;
  }

  updateStaleToggleUi(data);

  const elements =
    state.graphView === "actual"
      ? buildActualGraphElements(data)
      : buildTargetElements(data);

  graph.elements().remove();
  if (elements.length) {
    graph.add(elements);
    resizeGraphCanvas(graph, state.graphView);
    if (state.graphView === "actual") {
      focusActualGraphOnLatest(graph);
    } else {
      graph.fit(graph.nodes(), 48);
      const zoom = graph.zoom();
      if (zoom > 1) {
        graph.zoom(1);
        graph.center(graph.nodes());
      } else if (zoom < 0.72) {
        graph.zoom(0.72);
        graph.center(graph.nodes());
      }
    }
  }

  if (state.graphView === "target") {
    applyDivergenceHighlights(graph, data);
  } else {
    applyActualGraphHighlights(graph, data);
  }

  if (selectedNodeId && nodeDetails[selectedNodeId]) {
    highlightNode(selectedNodeId, selectedTimelineSeq);
    showNodePanel(selectedNodeId);
    highlightTimelineRow(selectedNodeId, selectedTimelineSeq);
  }

  renderDispatchPanel(data);
  renderSessionOutcomeBanner(data);
  renderDivergenceBanner(data.divergence?.summary);
  renderValidationBanner(data.validation);
  renderValidationPanel(data.pipeline === "spec" ? data.validation : null);
  updateInfraPanel();
  renderTimeline(data);

  const cur = data.current;
  document.getElementById("stats").textContent = JSON.stringify(
    {
      pipeline: data.pipeline_label || data.pipeline,
      current: cur,
      visit_counts: data.visit_counts,
      stats: data.stats,
      history_sources: data.history_sources,
      manifest: data.manifest,
      updated_at: data.updated_at,
    },
    null,
    2
  );
}

function disconnectStream() {
  if (state.source) {
    state.source.close();
    state.source = null;
  }
}

function connectStream() {
  disconnectStream();
  if (isSchemaMode()) return;
  if (!state.slug) {
    renderGraph({ slug: "", nodes: [], edges: [], history: [] });
    setConnection("idle", "нет задачи");
    return;
  }
  saveSelection();
  setConnection("", "подключение…");

  const source = new EventSource(streamUrl());
  state.source = source;

  source.onopen = () => {
    if (state.source !== source || isSchemaMode()) return;
    setConnection("live", "live");
  };

  source.onmessage = (event) => {
    if (state.source !== source || isSchemaMode()) return;
    try {
      const data = JSON.parse(event.data);
      renderGraph(data);
      clearError();
      setConnection("live", `live · ${data.updated_at || ""}`);
    } catch (err) {
      console.error(err);
      showError(`Ошибка разбора данных: ${err.message}`);
    }
  };

  source.onerror = () => {
    if (state.source !== source || isSchemaMode()) return;
    setConnection("reconnecting", "переподключение…");
    disconnectStream();
    setTimeout(() => {
      if (isSchemaMode()) return;
      connectStream();
    }, 2000);
  };
}

function fillSlugSelect(payload, config, saved) {
  const select = document.getElementById("slug-select");
  select.innerHTML = "";

  if (!payload.slugs || payload.slugs.length === 0) {
    select.innerHTML = '<option value="">— нет задач —</option>';
    return "";
  }

  const withLogs = payload.slugs.filter((s) => s.has_agent_logs);
  const withoutLogs = payload.slugs.filter((s) => !s.has_agent_logs);

  function addGroup(label, items) {
    if (!items.length) return;
    const group = document.createElement("optgroup");
    group.label = label;
    for (const item of items) {
      const opt = document.createElement("option");
      opt.value = item.slug;
      opt.textContent = item.slug;
      group.appendChild(opt);
    }
    select.appendChild(group);
  }

  addGroup("С телеметрией (agent-logs)", withLogs);
  addGroup("Только Feature-writing", withoutLogs);

  const slugSet = new Set(payload.slugs.map((s) => s.slug));
  let preferred =
    saved.slug ||
    config.default_slug ||
    (withLogs[0] && withLogs[0].slug) ||
    payload.slugs[0].slug;

  if (!slugSet.has(preferred)) {
    preferred = (withLogs[0] || payload.slugs[0]).slug;
  }

  select.value = preferred;
  return preferred;
}

async function apiUnavailableMessage(status) {
  const port = window.location.port || "8765";
  if (status === 404) {
    return (
      `На порту ${port} старый viewer (нет /api/config). ` +
      `Остановите: lsof -i :${port} → kill PID. ` +
      `Запустите: ./pipeline-viewer/start.sh или python3 pipeline-viewer/server.py — ` +
      `откройте URL из терминала (может быть :8767, не :8765).`
    );
  }
  return (
    `API недоступен (HTTP ${status}). Запустите из корня workspace: ` +
    `python3 pipeline-viewer/server.py — откройте URL из вывода терминала.`
  );
}

async function init() {
  try {
    clearError();
    initCytoscape();

    const healthRes = await fetch("/api/health");
    if (!healthRes.ok) {
      throw new Error(await apiUnavailableMessage(healthRes.status));
    }
    const health = await healthRes.json();
    apiVersion = health.version || 0;
    if (!apiVersion || apiVersion < 2) {
      throw new Error(await apiUnavailableMessage(404));
    }
    if (apiVersion < RESTART_MIN_API_VERSION) {
      showError(staleViewerMessage("перезапуск с шага и актуальный dispatch"));
    } else if (apiVersion < 5) {
      showError(staleViewerMessage("workflow validate в API графа (v5)"));
    }

    const saved = loadSelection();
    const [configRes, slugsRes, catalogRes] = await Promise.all([
      fetch("/api/config"),
      fetch("/api/slugs"),
      fetch("/api/catalog"),
    ]);

    if (!configRes.ok || !slugsRes.ok) {
      const st = !configRes.ok ? configRes.status : slugsRes.status;
      throw new Error(await apiUnavailableMessage(st));
    }

    const config = await configRes.json();
    const payload = await slugsRes.json();
    const catalog = catalogRes.ok ? await catalogRes.json() : { pipelines: [] };

    state.pipeline = saved.pipeline || config.default_pipeline || "spec";
    state.graphView = ["actual", "timing"].includes(saved.graphView) ? saved.graphView : "target";
    state.staleCollapsed = saved.staleCollapsed !== false;
    state.screenMode = saved.screenMode === "schema" ? "schema" : "run";
    state.packId = typeof saved.packId === "string" && saved.packId ? saved.packId : "spec";
    state.catalogPipelines = Array.isArray(catalog.pipelines) ? catalog.pipelines : [];
    state.catalogAgents = Array.isArray(catalog.agents) ? catalog.agents : [];
    state.catalogSkills = Array.isArray(catalog.skills) ? catalog.skills : [];
    state.agentsByCli =
      catalog.agents_by_cli && typeof catalog.agents_by_cli === "object" ? catalog.agents_by_cli : {};
    fillPackTabs();
    bindSchemaPalette();
    bindSchemaDraftActions();
    setActiveTab(state.pipeline);
    setGraphViewTabs();
    applyScreenModeChrome();
    state.slug = fillSlugSelect(payload, config, saved);

    if (apiVersion < SCHEMA_API_VERSION && isSchemaMode()) {
      showError(staleViewerMessage("вкладка «Схема» (GET /api/pack)"));
    }

    document.getElementById("stale-toggle")?.addEventListener("click", () => {
      setStaleCollapsed(!state.staleCollapsed);
    });

    document.querySelectorAll("#graph-view-tabs .tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (isSchemaMode()) return;
        const view = btn.dataset.view || "target";
        state.graphView = ["actual", "timing"].includes(view) ? view : "target";
        setGraphViewTabs();
        saveSelection();
        if (state.graph) {
          updateStaleToggleUi(state.graph);
          updateGraphViewHint(state.graph);
          renderGraph(state.graph);
        }
      });
    });

    if (config.restartable_steps_by_pipeline && typeof config.restartable_steps_by_pipeline === "object") {
      restartableByPipeline = config.restartable_steps_by_pipeline;
    }
    if (config.restartable_steps?.length) {
      RESTARTABLE_STEPS.clear();
      for (const step of config.restartable_steps) RESTARTABLE_STEPS.add(step);
      if (!Array.isArray(restartableByPipeline.spec) || !restartableByPipeline.spec.length) {
        restartableByPipeline = { ...restartableByPipeline, spec: [...config.restartable_steps] };
      }
    }

    initNoticeDismissHandlers();

    document.querySelectorAll("#screen-mode-tabs .tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        setScreenMode(btn.dataset.screen === "schema" ? "schema" : "run");
      });
    });

    document.getElementById("restart-btn").addEventListener("click", openRestartModal);
    document.getElementById("restart-confirm-btn").addEventListener("click", confirmRestart);
    document.querySelectorAll("#restart-modal [data-close]").forEach((el) => {
      el.addEventListener("click", closeRestartModal);
    });

    document.getElementById("slug-select").addEventListener("change", (e) => {
      state.slug = e.target.value;
      if (!isSchemaMode()) connectStream();
    });

    document.querySelectorAll("#pipeline-tabs .tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.pipeline = btn.dataset.pipeline;
        setActiveTab(state.pipeline);
        updateRestartActions(selectedNodeId);
        if (!isSchemaMode()) connectStream();
      });
    });

    if (isSchemaMode()) {
      loadPackGraph();
    } else {
      connectStream();
    }
  } catch (err) {
    console.error(err);
    showError(err.message || String(err));
    setConnection("reconnecting", "ошибка загрузки");
    document.getElementById("slug-select").innerHTML =
      '<option value="">— ошибка загрузки —</option>';
  }
}

init();
