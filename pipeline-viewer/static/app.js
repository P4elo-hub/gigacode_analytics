/* global cytoscape */

const STORAGE_KEY = "pipeline-viewer-selection";
const DISMISS_STORAGE_KEY = "pipeline-viewer-dismissed";
const DRAFT_STORAGE_KEY = "pipeline-viewer-schema-draft";
const SCHEMA_API_VERSION = 7;
const SAVE_STORAGE_KEY = "pipeline-viewer-schema-applied";
const INIT_TEMPLATES = ["routing-state", "full-dispatch", "orchestrator-only"];
const PROTECTED_PACKS = new Set(["calibration"]);
const SCHEMA_CLIS = ["qwen", "gigacode", "opencode"];
const PALETTE_DRAG_TYPE = "application/x-pipeline-agent";

const TIMING_PALETTE = [
  "#38bdf8",
  "#22c55e",
  "#a855f7",
  "#f59e0b",
  "#ec4899",
  "#6366f1",
  "#14b8a6",
  "#f97316",
  "#84cc16",
  "#06b6d4",
  "#e879f9",
  "#f43f5e",
];

/** Known step ids (spec + common pack aliases). Unknown pack steps → stable palette hash. */
const TIMING_STEP_COLORS = {
  "find-context": "#38bdf8",
  "context-researcher": "#38bdf8",
  "write-feature": "#22c55e",
  "spec-writer": "#22c55e",
  "check-feature": "#a855f7",
  "spec-reviewer": "#a855f7",
  "resolve-gaps": "#f59e0b",
  "gap-resolver": "#f59e0b",
  "challenge-feature": "#ec4899",
  "spec-challenger": "#ec4899",
  "resolve-challenges": "#f472b6",
  "challenge-resolver": "#f472b6",
  "check-feature-code": "#6366f1",
  "code-auditor": "#6366f1",
  "resolve-code-alignment": "#818cf8",
  "alignment-resolver": "#818cf8",
  "analyze-routing": "#4338ca",
  "routing-analyzer": "#4338ca",
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
const AFTER_STEP_LABEL = "после завершения шага";
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
  pipeline: "",
  graphView: "target",
  staleCollapsed: true,
  screenMode: "run",
  packId: "",
  source: null,
  graph: null,
  pack: null,
  packBase: null,
  catalogPipelines: [],
  runPipelines: [],
  allSlugs: [],
  catalogAgents: [],
  catalogSkills: [],
  catalogPredicates: { core: [], by_pipeline: {} },
  catalogRouting: {},
  agentsByCli: {},
  writeFeatureCycle: { profile: "", calls: [] },
  dismissedNotices: loadDismissedNotices(),
  packSave: { ok: false, errors: [], warnings: [], preview: null },
};

let cy = null;
let nodeDetails = {};
let graphInteractionsBound = false;
let selectedNodeId = null;
let selectedEdgeId = null;
let selectedElementId = null;
let selectedTimelineSeq = null;
let schemaConnectFrom = null;
let schemaInspectorSyncing = false;
let schemaInspectorUndoArmed = false;
const SCHEMA_UNDO_LIMIT = 40;
const schemaUndoByPack = {};
const SCHEMA_NODE_KINDS = ["orchestrator", "step", "terminal", "ask", "cycle", "meta"];
const SCHEMA_EDGE_KINDS = ["main", "branch", "loop"];
const CYCLE_CLOSE = "on_done";
const DISPATCH_OUTCOMES = ["ready", "stopped"];
const ASK_HANDSHAKE_NOTE =
  "Пауза на этой клетке, apply без смены шага. Между вопросом и apply перехода на другого агента нет.";
const FORBIDDEN_CYCLE_AGENTS = new Set(["analyze-routing", "routing-analyzer"]);
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
  return new Set();
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
          width: 168,
          height: 74,
          "text-max-width": "156px",
        },
      },
      {
        selector: 'node[cycleFlag = "true"][expanded = "true"]',
        style: {
          width: 220,
          "text-max-width": "208px",
          "font-size": "11px",
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
          opacity: 0.45,
          "text-rotation": "none",
          "text-wrap": "wrap",
          "text-max-width": "92px",
          "font-size": "9px",
        },
      },
      {
        selector: "edge.schema-edge.dim",
        style: {
          opacity: 0.12,
        },
      },
      {
        selector: "edge.schema-edge.outgoing",
        style: {
          opacity: 1,
          width: 3,
          "line-color": "#38bdf8",
          "target-arrow-color": "#38bdf8",
          color: "#e0f2fe",
          "font-size": "10px",
          "text-background-opacity": 0.92,
        },
      },
      {
        selector: 'edge.schema-edge[kind = "loop"]',
        style: {
          opacity: 0.32,
          width: 1.8,
        },
      },
      {
        selector: 'edge.schema-edge.outgoing[kind = "loop"]',
        style: {
          opacity: 0.95,
          width: 2.4,
        },
      },
      {
        selector: "edge.selected",
        style: {
          width: 3.5,
          "line-color": "#fbbf24",
          "target-arrow-color": "#fbbf24",
          color: "#fef3c7",
          "font-size": "10px",
          "text-background-opacity": 0.92,
          opacity: 1,
        },
      },
      {
        selector: "edge.schema-edge.save-error",
        style: {
          "line-color": "#ef4444",
          "target-arrow-color": "#ef4444",
          color: "#fecaca",
          opacity: 1,
          width: 3,
        },
      },
      {
        selector: "node.save-error",
        style: {
          "border-color": "#ef4444",
          "border-width": 4,
        },
      },
      {
        selector: "node.connect-source",
        style: {
          "border-color": "#22d3ee",
          "border-width": 4,
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
  setSchemaEdgeActionsVisible(false);
  if (isSchemaMode()) resetSchemaInspectorForms();
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
      `✓ Пайплайн готов — ${outcome.verdict || "PASS"}`,
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
      "✓ Workflow validate: OK · пайплайн готов",
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
    lines.push("✓ Пайплайн готов.");
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
  if (!stepId) return "#94a3b8";
  if (TIMING_STEP_COLORS[stepId]) return TIMING_STEP_COLORS[stepId];
  let hash = 0;
  for (let i = 0; i < stepId.length; i += 1) {
    hash = (hash * 31 + stepId.charCodeAt(i)) >>> 0;
  }
  return TIMING_PALETTE[hash % TIMING_PALETTE.length];
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
  } else {
    el.textContent = "Квадрат — шаг pipeline; hook/validate — в «Инфраструктура» справа";
  }
}

function updateInfraPanel() {
  const panel = document.getElementById("infra-panel");
  if (!panel) return;
  panel.classList.remove("hidden");
}

function buildTargetElements(data) {
  const elements = [];

  // Prefer positions from Schema draft (same pack id) so Прогон matches what you drew.
  const draftPositions = data.pipeline ? getPackDraft(data.pipeline).positions || {} : {};

  const nodeById = {};
  for (const node of data.nodes || []) {
    nodeById[node.id] = node;
    const pos = draftPositions[node.id] || node.position || { x: 0, y: 0 };
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


  for (const edge of data.edges || []) {
    const kind = edge.kind || "main";
    const source = edge.from;
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
  if (!summary) return;

  const expectedStep = summary.expected_step;
  const cur = data.current;
  const alreadyRunning =
    cur?.status === "running" && cur?.step === expectedStep;
  if (expectedStep && summary.must_continue && !alreadyRunning) {
    const expectedNode = graph.getElementById(expectedStep);
    if (expectedNode.length) expectedNode.addClass("expected");
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
  graph.edges().removeClass("selected");
  if (isSchemaMode()) {
    if (selectedEdgeId) {
      const edge = graph.getElementById(selectedEdgeId);
      if (edge.length) edge.addClass("selected");
    }
    if (selectedNodeId) {
      const node = graph.getElementById(selectedNodeId);
      if (node.length) node.addClass("selected");
    }
    graph.nodes().removeClass("connect-source");
    if (schemaConnectFrom) {
      const src = graph.getElementById(schemaConnectFrom);
      if (src.length) src.addClass("connect-source");
    }
    graph.nodes().forEach((el) => {
      const node = packNodeById(el.id());
      if (node) applyCycleNodePresentation(el, node);
    });
    highlightSchemaSelection();
    return;
  }
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
      const nodeId = node.id();
      const shift = Boolean(evt.originalEvent?.shiftKey);
      schemaInspectorUndoArmed = false;
      if (schemaConnectFrom) {
        finishSchemaConnect(nodeId);
        hideTooltip();
        return;
      }
      if (shift && selectedNodeId && selectedNodeId !== nodeId) {
        addSchemaEdge(selectedNodeId, nodeId);
        hideTooltip();
        return;
      }
      selectedElementId = nodeId;
      selectedNodeId = nodeId;
      selectedEdgeId = null;
      selectedTimelineSeq = null;
      highlightNode(selectedNodeId, null);
      showSchemaInspector();
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

  graph.on("mouseover", "edge", (evt) => {
    if (!isSchemaMode()) return;
    const edge = packEdgeById(evt.target.id());
    if (!edge) return;
    showTooltip(
      packEdgeTooltip(edge),
      evt.originalEvent.clientX,
      evt.originalEvent.clientY
    );
  });
  graph.on("mousemove", "edge", (evt) => {
    if (!isSchemaMode()) return;
    const edge = packEdgeById(evt.target.id());
    if (!edge) return;
    showTooltip(
      packEdgeTooltip(edge),
      evt.originalEvent.clientX,
      evt.originalEvent.clientY
    );
  });
  graph.on("mouseout", "edge", () => {
    if (isSchemaMode()) hideTooltip();
  });

  graph.on("tap", "edge", (evt) => {
    if (!isSchemaMode()) return;
    cancelSchemaConnect();
    schemaInspectorUndoArmed = false;
    selectedEdgeId = evt.target.id();
    selectedNodeId = null;
    selectedElementId = selectedEdgeId;
    selectedTimelineSeq = null;
    highlightNode(null, null);
    showSchemaInspector();
    hideTooltip();
  });

  graph.on("dragfree", "node", () => {
    if (!isSchemaMode()) return;
    captureSchemaPositions();
  });

  graph.on("tap", (evt) => {
    if (evt.target === graph) {
      if (isSchemaMode() && schemaConnectFrom) {
        cancelSchemaConnect();
        return;
      }
      selectedNodeId = null;
      selectedEdgeId = null;
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
  return {
    positions: {},
    extraNodes: [],
    deletedIds: [],
    extraEdges: [],
    deletedEdgeIds: [],
    nodeEdits: {},
    edgeEdits: {},
    orchestrator: "",
    seededCycleCalls: {},
    dispatchRules: null,
  };
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

function objectMap(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function getPackDraft(packId) {
  const store = loadDraftStore();
  const raw = store.packs?.[packId];
  if (!raw || typeof raw !== "object") return emptyPackDraft();
  return {
    positions: objectMap(raw.positions),
    extraNodes: Array.isArray(raw.extraNodes) ? raw.extraNodes : [],
    deletedIds: Array.isArray(raw.deletedIds) ? raw.deletedIds : [],
    extraEdges: Array.isArray(raw.extraEdges) ? raw.extraEdges : [],
    deletedEdgeIds: Array.isArray(raw.deletedEdgeIds) ? raw.deletedEdgeIds : [],
    nodeEdits: objectMap(raw.nodeEdits),
    edgeEdits: objectMap(raw.edgeEdits),
    orchestrator: typeof raw.orchestrator === "string" ? raw.orchestrator : "",
    seededCycleCalls: objectMap(raw.seededCycleCalls),
    dispatchRules: Array.isArray(raw.dispatchRules) ? raw.dispatchRules : null,
  };
}

function setPackDraft(packId, draft) {
  const store = loadDraftStore();
  store.packs = store.packs || {};
  store.packs[packId] = sanitizePackDraft(draft || emptyPackDraft());
  saveDraftStore(store);
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function schemaUndoStack(packId) {
  const id = packId || state.packId;
  if (!schemaUndoByPack[id]) schemaUndoByPack[id] = { past: [] };
  return schemaUndoByPack[id];
}

function updateSchemaUndoChrome() {
  const btn = document.getElementById("schema-undo");
  const n = schemaUndoStack(state.packId).past.length;
  if (btn) {
    btn.disabled = n === 0;
    btn.title = n ? `Отменить последнее изменение (${n})` : "Нечего отменять";
  }
}

function pushSchemaUndo() {
  const stack = schemaUndoStack(state.packId);
  stack.past.push(cloneJson(getPackDraft(state.packId)));
  if (stack.past.length > SCHEMA_UNDO_LIMIT) stack.past.shift();
  updateSchemaUndoChrome();
}

function undoSchemaDraft() {
  if (!isSchemaMode()) return;
  const stack = schemaUndoStack(state.packId);
  if (!stack.past.length) return;
  cancelSchemaConnect();
  const prev = stack.past.pop();
  setPackDraft(state.packId, prev);
  state.pack = applyDraftToPack(
    state.packBase || { id: state.packId, graph: { nodes: [], edges: [] } },
    prev
  );
  schemaInspectorUndoArmed = false;
  invalidatePackSave();
  renderPackGraph(state.pack, { skipFit: true });
  updateSchemaUndoChrome();
}

function draftNodeIds(draft) {
  const deleted = new Set(draft.deletedIds || []);
  const ids = new Set();
  for (const node of state.packBase?.graph?.nodes || []) {
    if (!node?.id || deleted.has(node.id)) continue;
    const edit = (draft.nodeEdits || {})[node.id];
    ids.add(edit?.id && String(edit.id).trim() ? String(edit.id).trim() : node.id);
  }
  for (const extra of draft.extraNodes || []) {
    if (extra?.id) ids.add(extra.id);
  }
  return ids;
}

function sanitizePackDraft(draft) {
  const next = { ...emptyPackDraft(), ...(draft || {}) };
  const ids = draftNodeIds(next);
  next.extraEdges = (next.extraEdges || []).filter(
    (edge) => edge && edge.from && edge.to && ids.has(edge.from) && ids.has(edge.to)
  );
  const edgeEdits = {};
  for (const [edgeId, patch] of Object.entries(next.edgeEdits || {})) {
    if (!patch || typeof patch !== "object") continue;
    const fromOk = patch.from == null || (patch.from && ids.has(patch.from));
    const toOk = patch.to == null || (patch.to && ids.has(patch.to));
    if (!fromOk || !toOk) {
      const cleaned = { ...patch };
      if (!fromOk) delete cleaned.from;
      if (!toOk) delete cleaned.to;
      if (Object.keys(cleaned).length) edgeEdits[edgeId] = cleaned;
      continue;
    }
    edgeEdits[edgeId] = patch;
  }
  next.edgeEdits = edgeEdits;
  if (next.orchestrator && !ids.has(next.orchestrator)) next.orchestrator = "";
  if (Array.isArray(next.dispatchRules)) {
    next.dispatchRules = next.dispatchRules.map(normalizeDispatchRule);
  } else {
    next.dispatchRules = null;
  }
  return next;
}

function nodeUiKind(node) {
  if (!node) return "step";
  if (node.kind === "orchestrator") return "orchestrator";
  if (node.kind === "terminal") return "terminal";
  if (node.kind === "meta") return "meta";
  if (node.cycle) return "cycle";
  if (node.ask) return "ask";
  return node.kind === "step" ? "step" : node.kind || "step";
}

function writeFeatureCycleDefaults() {
  const cat = state.writeFeatureCycle && typeof state.writeFeatureCycle === "object" ? state.writeFeatureCycle : {};
  return {
    persistent: true,
    close: CYCLE_CLOSE,
    assemble: String(cat.assemble || "write_feature"),
    param: String(cat.param || "block_id"),
    folder: "Feature-writing/{slug}",
    out: "{slug}.md",
    item_file: "{slug}.part-{param}.md",
    ask_queue: false,
  };
}

function defaultCycle() {
  return writeFeatureCycleDefaults();
}

function cycleNeedsCatalogFill(node) {
  if (!node?.cycle || typeof node.cycle !== "object") return false;
  const cycle = node.cycle;
  const missingMeta = !cycle.assemble || !cycle.param || !cycle.folder || !cycle.out || !cycle.item_file;
  return missingMeta || !packCycleCalls(node).length;
}

function parseCycleCallSections(value) {
  return String(value || "")
    .replace(/^коды:\s*/i, "")
    .split(/[,;]/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function normalizeCycleCall(call) {
  const item = {
    agent: String(call?.agent || "").trim(),
    param: String(call?.param || "").trim(),
  };
  const skills = Array.isArray(call?.skills)
    ? call.skills.map((skill) => String(skill || "").trim()).filter(Boolean)
    : String(call?.skills || "")
        .split(",")
        .map((skill) => skill.trim())
        .filter(Boolean);
  if (skills.length) item.skills = skills;
  const label = String(call?.label || "").trim();
  if (call && Object.prototype.hasOwnProperty.call(call, "label")) item.label = label;
  const sections = Array.isArray(call?.sections)
    ? call.sections.map((section) => String(section || "").trim()).filter(Boolean)
    : typeof call?.sections === "string"
      ? parseCycleCallSections(call.sections)
      : null;
  if (sections) item.sections = sections;
  return item;
}

function isForbiddenCycleCall(call) {
  const agent = String(call?.agent || "").trim().toLowerCase();
  const param = String(call?.param || "").trim().toLowerCase();
  return FORBIDDEN_CYCLE_AGENTS.has(agent) || param === "analyze-routing";
}

function normalizeCycle(raw) {
  const src = raw && typeof raw === "object" ? raw : {};
  const cycle = { close: CYCLE_CLOSE };
  cycle.persistent = src.persistent !== false;
  for (const key of ["assemble", "param", "folder", "out", "item_file"]) {
    const value = String(src[key] || "").trim();
    if (value) cycle[key] = value;
  }
  if (src.ask_queue === true) cycle.ask_queue = true;
  else if (src.ask_queue === false) cycle.ask_queue = false;
  const calls = Array.isArray(src.calls)
    ? src.calls.filter((call) => call && typeof call === "object").map(normalizeCycleCall)
    : [];
  if (calls.length) cycle.calls = calls;
  return cycle;
}

function applyUiKindToNode(node, uiKind) {
  const next = { ...node };
  const kind = SCHEMA_NODE_KINDS.includes(uiKind) ? uiKind : "step";
  delete next.ask;
  if (kind === "cycle") {
    next.kind = "step";
    next.cycle = normalizeCycle(
      node.cycle && typeof node.cycle === "object" ? node.cycle : defaultCycle()
    );
    return next;
  }
  delete next.cycle;
  if (kind === "orchestrator") next.kind = "orchestrator";
  else if (kind === "terminal") next.kind = "terminal";
  else if (kind === "meta") next.kind = "meta";
  else if (kind === "ask") {
    next.kind = "step";
    next.ask = true;
  } else next.kind = "step";
  return next;
}

function extraNodePayload(node) {
  const payload = {
    id: node.id,
    label: node.label || node.id,
    kind: node.kind || "step",
    subagent: node.subagent == null ? null : node.subagent,
  };
  if (node.ask) payload.ask = true;
  if (node.cycle && typeof node.cycle === "object") payload.cycle = cloneJson(node.cycle);
  return payload;
}

function applyNodeEditRecord(node, edit) {
  if (!edit || typeof edit !== "object") return { ...node };
  let next = { ...node };
  if (edit.uiKind) next = applyUiKindToNode(next, edit.uiKind);
  else {
    if (edit.kind != null) next.kind = edit.kind;
    if (edit.ask === true) next.ask = true;
    else if (edit.ask === false) delete next.ask;
  }
  if (edit.cycle && typeof edit.cycle === "object") next.cycle = cloneJson(edit.cycle);
  else if (edit.cycle === null) delete next.cycle;
  if (edit.label != null) next.label = edit.label;
  if (edit.subagent !== undefined) next.subagent = edit.subagent;
  if (edit.id && String(edit.id).trim() && String(edit.id).trim() !== node.id) {
    next.id = String(edit.id).trim();
  }
  return next;
}

function ensureEdgeId(edge, index, used) {
  let id = edge.id || `e-${edge.from}-${edge.to}`;
  if (used.has(id)) id = `e-${edge.from}-${edge.to}-${index}`;
  used.add(id);
  return { ...edge, id };
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
  const edits = draft.nodeEdits || {};
  const idMap = {};
  const nodes = [];
  const existing = new Set();

  for (const node of pack.graph.nodes || []) {
    if (!node?.id || deleted.has(node.id)) continue;
    const next = applyNodeEditRecord(node, edits[node.id]);
    if (next.id !== node.id) idMap[node.id] = next.id;
    if (existing.has(next.id)) continue;
    nodes.push(next);
    existing.add(next.id);
  }

  for (const extra of draft.extraNodes || []) {
    if (!extra?.id || existing.has(extra.id) || deleted.has(extra.id)) continue;
    const node = applyNodeEditRecord(
      {
        id: extra.id,
        label: extra.label || extra.id,
        kind: extra.kind || "step",
        subagent: extra.subagent === undefined ? extra.id : extra.subagent,
        draft: true,
        ...(extra.ask ? { ask: true } : {}),
        ...(extra.cycle && typeof extra.cycle === "object" ? { cycle: extra.cycle } : {}),
      },
      edits[extra.id]
    );
    node.draft = true;
    if (existing.has(node.id)) continue;
    nodes.push(node);
    existing.add(node.id);
  }

  const mapId = (id) => idMap[id] || id;
  const deletedEdges = new Set(draft.deletedEdgeIds || []);
  const edgeEdits = draft.edgeEdits || {};
  const usedEdgeIds = new Set();
  let edges = [];

  (pack.graph.edges || []).forEach((edge, index) => {
    if (!edge) return;
    const mapped = {
      ...edge,
      from: mapId(edge.from),
      to: mapId(edge.to),
    };
    const withId = ensureEdgeId(mapped, index, usedEdgeIds);
    if (deletedEdges.has(withId.id)) return;
    const patch = edgeEdits[withId.id] || {};
    const next = { ...withId, ...patch };
    if (!next.from || !next.to) return;
    if (!existing.has(next.from) || !existing.has(next.to)) return;
    edges.push(next);
  });

  for (const extra of draft.extraEdges || []) {
    if (!extra?.from || !extra?.to) continue;
    if (!existing.has(extra.from) || !existing.has(extra.to)) continue;
    if (extra.id && deletedEdges.has(extra.id)) continue;
    const withId = extra.id
      ? extra
      : ensureEdgeId({ ...extra }, edges.length, usedEdgeIds);
    if (withId.id && usedEdgeIds.has(withId.id) && extra.id) {
      /* keep explicit extra id even if pack already used it — skip duplicate */
      if (edges.some((item) => item.id === withId.id)) continue;
    }
    if (withId.id) usedEdgeIds.add(withId.id);
    const patch = edgeEdits[withId.id] || {};
    const next = { ...withId, ...patch };
    if (!next.from || !next.to) continue;
    if (!existing.has(next.from) || !existing.has(next.to)) continue;
    edges.push(next);
  }

  pack.graph.nodes = nodes;
  pack.graph.edges = edges.map((edge) => {
    const next = { ...edge };
    if (edgeIsAfterStep(next) || next.after_step === true) {
      next.after_step = true;
      next.kind = "loop";
      if (!String(next.label || "").trim()) next.label = AFTER_STEP_LABEL;
      delete next.condition;
      delete next.conditions;
      delete next.condition_label;
      delete next.condition_labels;
      return next;
    }
    delete next.after_step;
    const labels = { ...(next.condition_labels || {}) };
    const ids = [];
    const seen = new Set();
    const collect = (raw, label) => {
      const text = String(raw || "").trim();
      const human = String(label || "").trim();
      if (!text && !human) return;
      const token = normalizeWhenToken(text || human, human);
      if (!token.id || seen.has(token.id)) return;
      seen.add(token.id);
      ids.push(token.id);
      if (token.label) labels[token.id] = token.label;
    };
    collect(next.condition, next.condition_label || labels[next.condition]);
    if (Array.isArray(next.conditions)) {
      for (const item of next.conditions) {
        if (typeof item === "string") collect(item, labels[item]);
        else if (item && typeof item === "object") collect(item.id || item.label, item.label || item.instruction);
      }
    }
    if (ids.length) {
      next.condition = ids[0];
      if (ids.length > 1) next.conditions = ids;
      else delete next.conditions;
      if (labels[ids[0]]) next.condition_label = labels[ids[0]];
      else delete next.condition_label;
      next.condition_labels = labels;
    } else {
      delete next.condition;
      delete next.conditions;
      delete next.condition_label;
      delete next.condition_labels;
    }
    return next;
  });

  const keepDispatchNext = (rule) => {
    const nxt = rule?.next;
    return !nxt || existing.has(nxt) || DISPATCH_OUTCOMES.includes(nxt);
  };
  if (Array.isArray(draft.dispatchRules)) {
    pack.dispatch = { ...(pack.dispatch || {}) };
    pack.dispatch.rules = draft.dispatchRules.map(normalizeDispatchRule).filter(keepDispatchNext);
  } else if (Array.isArray(pack.dispatch?.rules)) {
    pack.dispatch = { ...(pack.dispatch || {}) };
    pack.dispatch.rules = pack.dispatch.rules.map(normalizeDispatchRule).filter(keepDispatchNext);
  }

  if (draft.orchestrator && existing.has(draft.orchestrator)) {
    pack.graph.orchestrator = draft.orchestrator;
  } else {
    const orch = nodes.find((node) => node.kind === "orchestrator");
    if (orch) pack.graph.orchestrator = orch.id;
  }
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

function setSchemaEdgeActionsVisible(show) {
  const el = document.getElementById("schema-edge-actions");
  if (el) el.classList.toggle("hidden", !show);
}

function setSchemaInspectorError(text) {
  const el = document.getElementById("schema-inspector-error");
  if (!el) return;
  el.textContent = text || "";
  el.classList.toggle("hidden", !text);
}

function schemaKindHint(uiKind) {
  if (uiKind === "cycle") {
    return "Составная клетка: сначала очередь calls этой клетки, потом «спросить» или «зафиксировать» по ней же.";
  }
  if (uiKind === "ask") {
    return ASK_HANDSHAKE_NOTE;
  }
  if (uiKind === "orchestrator") {
    return "Ровно одна клетка-оркестратор. Другой оркестратор станет шагом.";
  }
  if (uiKind === "terminal") return "Терминал (PASS / done).";
  if (uiKind === "meta") return "Мета-шаг, не ask/cycle.";
  return "Обычный шаг. YAML не пишется.";
}

function fillNodeIdOptions(select, selectedId) {
  if (!select) return;
  const nodes = state.pack?.graph?.nodes || [];
  select.innerHTML = "";
  for (const node of nodes) {
    const opt = document.createElement("option");
    opt.value = node.id;
    opt.textContent = node.label && node.label !== node.id ? `${node.id} · ${node.label}` : node.id;
    select.appendChild(opt);
  }
  if (selectedId && ![...select.options].some((opt) => opt.value === selectedId)) {
    const opt = document.createElement("option");
    opt.value = selectedId;
    opt.textContent = selectedId;
    select.appendChild(opt);
  }
  select.value = selectedId || select.options[0]?.value || "";
}

function fillSubagentSelect(select, current) {
  if (!select) return;
  const agents = [...state.catalogAgents];
  if (current && !agents.includes(current)) agents.unshift(current);
  select.innerHTML = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "(нет)";
  select.appendChild(empty);
  for (const name of agents) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    select.appendChild(opt);
  }
  select.value = current || "";
}

function routingConditionsForPack(packId) {
  const block = state.catalogRouting?.[packId || state.packId];
  return block && typeof block === "object" ? block : {};
}

function whenCatalogEntries(packId) {
  // Authoring when-picker: only conditions on this pack's edges.
  // Do not merge predicates.core (union across packs) or by_pipeline —
  // those leak foreign has_spec / has_gaps_map into another pack's UI.
  const id = packId || state.packId;
  const labels = {};
  const catalogEdges = Array.isArray(routingConditionsForPack(id).edge_conditions)
    ? routingConditionsForPack(id).edge_conditions
    : [];
  for (const item of catalogEdges) {
    const condId = String(item?.id || "").trim();
    if (!condId) continue;
    labels[condId] = String(item.label || condId).trim() || condId;
  }
  // Draft arrows may invent when-ids before Apply refreshes catalogRouting.
  if (!packId || id === state.packId) {
    for (const edge of state.pack?.graph?.edges || []) {
      const edgeLabels = edge?.condition_labels || {};
      for (const condId of edgeConditionIds(edge)) {
        if (!condId || labels[condId]) continue;
        const human = String(edgeLabels[condId] || edge.condition_label || "").trim();
        labels[condId] = human && human !== condId ? human : condId;
      }
    }
  }
  return Object.keys(labels)
    .filter(Boolean)
    .sort()
    .map((condId) => ({
      id: condId,
      label: labels[condId] || condId,
    }));
}

function conditionHumanLabel(conditionId, edge) {
  const id = String(conditionId || "").trim();
  if (!id) return String(edge?.condition_label || "").trim();
  const fromMap = edge?.condition_labels && edge.condition_labels[id];
  if (fromMap && fromMap !== id) return fromMap;
  const found = whenCatalogEntries().find((item) => item.id === id);
  if (found && found.label && found.label !== id) return found.label;
  if (edge?.condition_label && edge.condition_label !== id) return edge.condition_label;
  return found?.label || id;
}

function inventConditionId(text, taken) {
  const raw = String(text || "").trim();
  if (!raw) return "";
  const compact = raw.replace(/-/g, "_");
  if (/^[A-Za-z][A-Za-z0-9_]*$/.test(compact)) return compact.toLowerCase();
  const slug = slugConditionId(raw);
  let base = slug.startsWith("has_") || slug.startsWith("not_has_") ? slug : `has_${slug}`;
  if (base.length > 56) base = base.slice(0, 56).replace(/_+$/, "") || "has_custom";
  if (!/^[a-z]/.test(base)) base = `has_${base}`;
  let candidate = base;
  let n = 2;
  const used = taken instanceof Set ? taken : new Set(taken || []);
  while (used.has(candidate)) {
    const suffix = `_${n}`;
    candidate = `${base.slice(0, Math.max(1, 56 - suffix.length))}${suffix}`;
    n += 1;
  }
  return candidate;
}

function normalizeWhenToken(raw, label) {
  const text = String(raw || "").trim();
  const human = String(label || "").trim();
  if (!text && !human) return { id: "", label: "" };
  const looksLikeId = (value) => /^[A-Za-z][A-Za-z0-9_]*$/.test(String(value || "").replace(/-/g, "_"));
  if (text && looksLikeId(text)) {
    return { id: inventConditionId(text, []), label: human || text };
  }
  if (human && !looksLikeId(human)) {
    return { id: inventConditionId(human, []), label: human };
  }
  if (text && !looksLikeId(text)) {
    return { id: inventConditionId(text, []), label: text };
  }
  return {
    id: inventConditionId(text || human, []),
    label: human || text,
  };
}

function edgeConditionIds(edge) {
  if (!edge) return [];
  const ids = [];
  const seen = new Set();
  const push = (raw, label) => {
    const token = normalizeWhenToken(raw, label);
    if (!token.id || seen.has(token.id)) return;
    seen.add(token.id);
    ids.push(token.id);
  };
  const labels = edge.condition_labels || {};
  push(edge.condition, edge.condition_label || labels[edge.condition]);
  if (Array.isArray(edge.conditions)) {
    for (const item of edge.conditions) {
      if (typeof item === "string") push(item, labels[item]);
      else if (item && typeof item === "object") push(item.id || item.label, item.label || item.instruction);
    }
  }
  return ids;
}

function mergedDraftEdge(edgeId) {
  const live = packEdgeById(edgeId) || {};
  const draft = getPackDraft(state.packId);
  const extra = (draft.extraEdges || []).find((item) => item.id === edgeId) || {};
  const edit = (draft.edgeEdits || {})[edgeId] || {};
  return { ...live, ...extra, ...edit, id: edgeId || live.id || extra.id };
}

function resolveEdgeConditionPatch(current, prevPatch, patch) {
  if (!patch || (!Object.prototype.hasOwnProperty.call(patch, "condition") && !Object.prototype.hasOwnProperty.call(patch, "conditions"))) {
    return patch;
  }
  const before = { ...current, ...prevPatch };
  const ids = Array.isArray(patch.conditions)
    ? edgeConditionIds({ condition: patch.condition, conditions: patch.conditions })
    : edgeConditionIds({ ...before, condition: patch.condition, conditions: [...edgeConditionIds(before), patch.condition] });
  return { ...patch, ...conditionPatchFromIds(ids, { ...before, ...patch }) };
}

function formatConditionId(conditionId, edge) {
  const id = String(conditionId || "").trim();
  if (!id) return "";
  const human = conditionHumanLabel(id, edge);
  return human && human !== id ? `${id} · ${human}` : id;
}

function conditionPatchFromIds(ids, edge) {
  const unique = [];
  const seen = new Set();
  for (const raw of ids || []) {
    const id = String(raw || "").trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    unique.push(id);
  }
  if (!unique.length) {
    return { condition: "", condition_label: "", conditions: [] };
  }
  const first = unique[0];
  const labels = { ...(edge?.condition_labels || {}) };
  const label = conditionHumanLabel(first, edge);
  if (label && label !== first) labels[first] = label;
  const kept = {};
  for (const id of unique) {
    if (labels[id]) kept[id] = labels[id];
  }
  return {
    condition: first,
    condition_label: label && label !== first ? label : "",
    conditions: unique,
    condition_labels: kept,
  };
}

const RU_TRANSLIT = {
  а: "a",
  б: "b",
  в: "v",
  г: "g",
  д: "d",
  е: "e",
  ё: "e",
  ж: "zh",
  з: "z",
  и: "i",
  й: "i",
  к: "k",
  л: "l",
  м: "m",
  н: "n",
  о: "o",
  п: "p",
  р: "r",
  с: "s",
  т: "t",
  у: "u",
  ф: "f",
  х: "kh",
  ц: "ts",
  ч: "ch",
  ш: "sh",
  щ: "shch",
  ъ: "",
  ы: "y",
  ь: "",
  э: "e",
  ю: "yu",
  я: "ya",
};

function slugConditionId(text) {
  const raw = String(text || "").trim();
  if (!raw) return "";
  const compact = raw.replace(/-/g, "_");
  if (/^[A-Za-z][A-Za-z0-9_]*$/.test(compact)) return compact.toLowerCase();
  const out = [];
  for (const char of raw.toLowerCase()) {
    if (Object.prototype.hasOwnProperty.call(RU_TRANSLIT, char)) out.push(RU_TRANSLIT[char]);
    else if (/[a-z0-9]/.test(char)) out.push(char);
    else out.push("_");
  }
  return out.join("").replace(/_+/g, "_").replace(/^_|_$/g, "") || "when_custom";
}

function matchWhenCatalog(text) {
  const raw = String(text || "").trim();
  if (!raw) return null;
  const lower = raw.toLowerCase();
  const entries = whenCatalogEntries();
  return (
    entries.find((item) => item.id.toLowerCase() === lower) ||
    entries.find((item) => String(item.label || "").toLowerCase() === lower) ||
    null
  );
}

function conditionPatchFromText(text) {
  const raw = String(text || "").trim();
  if (!raw) return { condition: "", condition_label: "", conditions: [], condition_labels: {} };
  const token = normalizeWhenToken(raw, raw);
  return {
    condition: token.id,
    condition_label: token.label || raw,
    conditions: [token.id],
    condition_labels: token.label ? { [token.id]: token.label } : {},
  };
}

function conditionTextForEdge(edge) {
  if (!edge) return "";
  const ids = edgeConditionIds(edge);
  if (!ids.length) return String(edge.condition_label || "").trim();
  return ids.map((id) => formatConditionId(id, edge)).join(" · ");
}

function fillWhenDatalist(datalist) {
  if (!datalist) return;
  datalist.innerHTML = "";
  for (const item of whenCatalogEntries()) {
    const optId = document.createElement("option");
    optId.value = item.id;
    optId.label = formatWhenOption(item);
    datalist.appendChild(optId);
    if (item.label && item.label !== item.id) {
      const optLabel = document.createElement("option");
      optLabel.value = item.label;
      optLabel.label = item.id;
      datalist.appendChild(optLabel);
    }
  }
}

function formatWhenOption(item) {
  if (!item) return "";
  return item.label && item.label !== item.id ? `${item.id} · ${item.label}` : item.id;
}

function fillWhenSelect(select, selectedId, opts = {}) {
  if (!select) return;
  const entries = whenCatalogEntries();
  const current = String(selectedId || "").trim();
  select.innerHTML = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = opts.emptyLabel || "(нет)";
  select.appendChild(empty);
  const known = new Set();
  for (const item of entries) {
    known.add(item.id);
    const opt = document.createElement("option");
    opt.value = item.id;
    opt.textContent = formatWhenOption(item);
    select.appendChild(opt);
  }
  if (current && !known.has(current)) {
    const opt = document.createElement("option");
    opt.value = current;
    opt.textContent = `${current} · не в каталоге`;
    select.appendChild(opt);
  }
  select.value = current;
}

function fillDispatchNextSelect(select, selectedNext, outcome) {
  if (!select) return;
  const nodes = state.pack?.graph?.nodes || [];
  const current = selectedNext || (DISPATCH_OUTCOMES.includes(outcome) ? outcome : "");
  select.innerHTML = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "(пусто)";
  select.appendChild(empty);
  for (const value of DISPATCH_OUTCOMES) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = value;
    select.appendChild(opt);
  }
  for (const node of nodes) {
    if (!node?.id) continue;
    const opt = document.createElement("option");
    opt.value = node.id;
    opt.textContent = node.label && node.label !== node.id ? `${node.id} · ${node.label}` : node.id;
    select.appendChild(opt);
  }
  if (current && ![...select.options].some((opt) => opt.value === current)) {
    const opt = document.createElement("option");
    opt.value = current;
    opt.textContent = current;
    select.appendChild(opt);
  }
  select.value = current || "";
}

function normalizeDispatchRule(rule) {
  const rawPriority = Number(rule?.priority);
  const when = slugConditionId(String(rule?.when || "").trim()) || String(rule?.when || "").trim();
  let next = rule?.next;
  if (next === "" || next === undefined) next = null;
  let outcome = String(rule?.outcome || "").trim();
  if (DISPATCH_OUTCOMES.includes(next)) {
    outcome = next;
    next = null;
  }
  if (!DISPATCH_OUTCOMES.includes(outcome)) outcome = "";
  const item = {
    priority: Number.isFinite(rawPriority) ? rawPriority : 0,
    when,
    next: next || null,
  };
  if (!item.next && outcome) item.outcome = outcome;
  return item;
}

function baseDispatchRules() {
  const rules = state.packBase?.dispatch?.rules;
  return Array.isArray(rules) ? rules.map(normalizeDispatchRule) : [];
}

function liveDispatchRules() {
  const draft = getPackDraft(state.packId);
  if (Array.isArray(draft.dispatchRules)) return draft.dispatchRules.map(normalizeDispatchRule);
  return (state.pack?.dispatch?.rules || baseDispatchRules()).map(normalizeDispatchRule);
}

function sortedDispatchRules(rules) {
  return rules
    .map((rule, index) => ({ rule, index }))
    .sort((a, b) => {
      if (a.rule.priority !== b.rule.priority) return a.rule.priority - b.rule.priority;
      return a.index - b.index;
    });
}

function dispatchPriorityCounts(rules) {
  const counts = {};
  for (const rule of rules) {
    const key = String(rule.priority);
    counts[key] = (counts[key] || 0) + 1;
  }
  return counts;
}

function ruleFromDispatchFields(priority, when, nextValue) {
  const next = String(nextValue || "").trim();
  if (DISPATCH_OUTCOMES.includes(next)) {
    return normalizeDispatchRule({ priority, when, next: null, outcome: next });
  }
  return normalizeDispatchRule({ priority, when, next: next || null });
}

function commitDispatchRules(rules, opts = {}) {
  if (!opts.skipUndo) armInspectorUndo();
  const draft = getPackDraft(state.packId);
  draft.dispatchRules = rules.map(normalizeDispatchRule);
  persistDraftWithoutFit(draft);
  renderSchemaDispatchTable();
  renderPackSummary(state.pack);
}

function nextDispatchPriority(rules) {
  const max = rules.reduce((acc, rule) => Math.max(acc, Number(rule.priority) || 0), 0);
  return max + 10;
}

function addDispatchRule() {
  const rules = liveDispatchRules();
  pushSchemaUndo();
  schemaInspectorUndoArmed = true;
  rules.push(ruleFromDispatchFields(nextDispatchPriority(rules), "", ""));
  commitDispatchRules(rules, { skipUndo: true });
}

function patchDispatchRule(index, patch, replace = false) {
  const rules = liveDispatchRules();
  if (!rules[index]) return;
  const next = replace
    ? normalizeDispatchRule(patch)
    : normalizeDispatchRule({ ...rules[index], ...patch });
  if (next.next) delete next.outcome;
  rules[index] = next;
  commitDispatchRules(rules);
}

function removeDispatchRule(index) {
  const rules = liveDispatchRules();
  if (!rules[index]) return;
  pushSchemaUndo();
  schemaInspectorUndoArmed = true;
  rules.splice(index, 1);
  commitDispatchRules(rules, { skipUndo: true });
}

function renderSchemaDispatchTable() {
  const list = document.getElementById("schema-dispatch-rules");
  const conflict = document.getElementById("schema-dispatch-conflict");
  if (!list) return;
  const rules = liveDispatchRules();
  const counts = dispatchPriorityCounts(rules);
  const dupes = Object.entries(counts)
    .filter(([, n]) => n > 1)
    .map(([priority]) => `P${priority}`);
  if (conflict) {
    conflict.textContent = dupes.length
      ? `Конфликт: одинаковый priority ${dupes.join(", ")}. Нужны уникальные числа.`
      : "";
    conflict.classList.toggle("hidden", !dupes.length);
  }
  list.innerHTML = "";
  if (!rules.length) {
    const empty = document.createElement("p");
    empty.className = "schema-dispatch-empty";
    empty.textContent = "Нет правил (calibration-style). YAML не пишется.";
    list.appendChild(empty);
    return;
  }
  for (const { rule, index } of sortedDispatchRules(rules)) {
    const li = document.createElement("li");
    li.className = "schema-dispatch-rule";
    li.dataset.index = String(index);
    li.dataset.when = rule.when || "";
    li.dataset.priority = String(rule.priority);
    if ((counts[String(rule.priority)] || 0) > 1) li.classList.add("is-conflict");

    const head = document.createElement("div");
    head.className = "schema-dispatch-rule-head";

    const pLabel = document.createElement("label");
    pLabel.className = "schema-dispatch-priority";
    pLabel.innerHTML = "<span>priority</span>";
    const pInput = document.createElement("input");
    pInput.type = "number";
    pInput.name = "priority";
    pInput.step = "1";
    pInput.value = String(rule.priority);
    pLabel.appendChild(pInput);

    const whenLabel = document.createElement("label");
    whenLabel.innerHTML = "<span>when</span>";
    const whenSelect = document.createElement("select");
    whenSelect.name = "when";
    fillWhenSelect(whenSelect, rule.when, { emptyLabel: "(when)" });
    whenLabel.appendChild(whenSelect);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn-secondary";
    remove.dataset.action = "remove";
    remove.textContent = "Удалить";

    head.append(pLabel, whenLabel, remove);

    const row = document.createElement("div");
    row.className = "schema-dispatch-rule-row";
    const nextLabel = document.createElement("label");
    nextLabel.innerHTML = "<span>next / outcome</span>";
    const nextSelect = document.createElement("select");
    nextSelect.name = "next";
    fillDispatchNextSelect(nextSelect, rule.next, rule.outcome);
    nextLabel.appendChild(nextSelect);
    row.appendChild(nextLabel);

    li.append(head, row);
    list.appendChild(li);
  }
  highlightSaveErrors();
}

function uniqueCycleCallParam(calls) {
  const used = new Set((calls || []).map((call) => String(call.param || "")));
  let i = 1;
  let param = `call-${i}`;
  while (used.has(param)) {
    i += 1;
    param = `call-${i}`;
  }
  return param;
}

function writeFeatureCatalogCalls() {
  const raw = state.writeFeatureCycle?.calls;
  if (!Array.isArray(raw) || !raw.length) return [];
  return raw.map((call) => ({
    agent: String(call.agent || "spec-writer"),
    param: String(call.param || ""),
    skills: Array.isArray(call.skills) ? [...call.skills] : [],
    label: String(call.label || ""),
    sections: Array.isArray(call.sections) ? [...call.sections] : [],
  }));
}

async function loadWriteFeatureCycleFallback() {
  if (writeFeatureCatalogCalls().length) return;
  try {
    const res = await fetch("/static/write-feature-cycle.json");
    if (!res.ok) return;
    const data = await res.json();
    if (data && Array.isArray(data.calls) && data.calls.length) {
      state.writeFeatureCycle = data;
    }
  } catch {
    /* catalog snapshot is optional; used only when pinning calls */
  }
}

function catalogMetaForParam(param) {
  const id = String(param || "");
  return (state.writeFeatureCycle?.calls || []).find((call) => call.param === id) || null;
}

function cycleCallLabel(call) {
  if (call && Object.prototype.hasOwnProperty.call(call, "label")) {
    return String(call.label || "").trim();
  }
  return String(catalogMetaForParam(call?.param)?.label || "").trim();
}

function cycleCallSections(call) {
  if (call && Array.isArray(call.sections)) {
    return call.sections.map((section) => String(section || "").trim()).filter(Boolean);
  }
  const meta = catalogMetaForParam(call?.param);
  return Array.isArray(meta?.sections)
    ? meta.sections.map((section) => String(section || "").trim()).filter(Boolean)
    : [];
}

function makeCycleCallEditable(field, text, placeholder) {
  const el = document.createElement("span");
  el.contentEditable = "true";
  el.dataset.field = field;
  el.spellcheck = false;
  el.setAttribute("role", "textbox");
  el.textContent = text || "";
  if (placeholder) el.dataset.placeholder = placeholder;
  return el;
}

function packCycleCalls(node) {
  const cycle = node?.cycle && typeof node.cycle === "object" ? node.cycle : {};
  return Array.isArray(cycle.calls) ? cycle.calls : [];
}

function cycleAskQueue(node) {
  const cycle = node?.cycle && typeof node.cycle === "object" ? node.cycle : {};
  return cycle.ask_queue;
}

function cycleQueueMode(node) {
  const flag = cycleAskQueue(node);
  if (flag === true) return "plan";
  if (flag === false) return "pinned";
  return packCycleCalls(node).length ? "pinned" : "plan";
}

function applyCycleQueueMode(cycle, mode) {
  if (mode === "plan") cycle.ask_queue = true;
  else cycle.ask_queue = false;
  return cycle;
}

function syncCycleQueueChrome(node) {
  const pinned = cycleQueueMode(node) === "pinned";
  const planRadio = document.getElementById("schema-cycle-queue-plan");
  const pinnedRadio = document.getElementById("schema-cycle-queue-pinned");
  if (planRadio) planRadio.checked = !pinned;
  if (pinnedRadio) pinnedRadio.checked = pinned;
  document.getElementById("schema-cycle-pinned-wrap")?.classList.remove("hidden");
}

function refreshSelectedCycleCanvas(node) {
  if (!cy || !node) return;
  const el = cy.getElementById(node.id);
  if (el.length) applyCycleNodePresentation(el, node);
}

function selectedCycleNode() {
  if (!selectedNodeId) return null;
  const node = packNodeById(selectedNodeId);
  return node?.cycle ? node : null;
}

function commitSelectedCycle(cycle, opts = {}) {
  const node = selectedCycleNode();
  if (!node) return false;
  const cleaned = normalizeCycle(cycle);
  if (opts.discrete) {
    pushSchemaUndo();
    schemaInspectorUndoArmed = true;
  }
  applyNodeFieldPatch(node.id, { cycle: cleaned }, { rebuild: Boolean(opts.rebuild) });
  if (opts.discrete) schemaInspectorUndoArmed = false;
  return true;
}

function cycleFieldValue(id) {
  return document.getElementById(id)?.value || "";
}

function readCycleFieldsFromForm(base) {
  const cycle = normalizeCycle(base);
  cycle.persistent = Boolean(document.getElementById("schema-cycle-persistent")?.checked);
  const assemble = cycleFieldValue("schema-cycle-assemble").trim();
  const param = cycleFieldValue("schema-cycle-param").trim();
  const folder = cycleFieldValue("schema-cycle-folder").trim();
  const out = cycleFieldValue("schema-cycle-out").trim();
  const itemFile = cycleFieldValue("schema-cycle-item-file").trim();
  if (assemble) cycle.assemble = assemble;
  else delete cycle.assemble;
  if (param) cycle.param = param;
  else delete cycle.param;
  if (folder) cycle.folder = folder;
  else delete cycle.folder;
  if (out) cycle.out = out;
  else delete cycle.out;
  if (itemFile) cycle.item_file = itemFile;
  else delete cycle.item_file;
  cycle.close = CYCLE_CLOSE;
  return cycle;
}

function renderCycleCalls(cycle, node) {
  const list = document.getElementById("schema-cycle-calls");
  const hint = document.getElementById("schema-cycle-calls-hint");
  if (!list) return;
  const calls = packCycleCalls({ ...node, cycle });
  const ask = cycleQueueMode({ ...node, cycle }) === "plan";
  if (hint) {
    if (!calls.length) {
      hint.textContent = ask
        ? "Очередь этой клетки пустая — спрашивать будет не о чем. Добавьте calls или «Из каталога»."
        : "Очередь этой клетки пустая. Добавьте calls или «Из каталога».";
    } else if (ask) {
      hint.textContent = "Спросить при прогоне по этим calls клетки. Каталог сам не подставляется.";
    } else {
      hint.textContent = "Эти calls клетки идут по порядку, без вопроса. Между ними нет рёбер.";
    }
  }
  const fillBtn = document.getElementById("schema-cycle-fill-catalog");
  if (fillBtn) fillBtn.disabled = writeFeatureCatalogCalls().length === 0;
  list.innerHTML = "";
  if (!calls.length) {
    const empty = document.createElement("li");
    empty.className = "schema-cycle-call";
    empty.textContent = "Calls этой клетки нет.";
    list.appendChild(empty);
    return;
  }
  calls.forEach((call, index) => {
    const li = document.createElement("li");
    li.className = "schema-cycle-call";
    li.dataset.index = String(index);

    const title = document.createElement("div");
    title.className = "schema-cycle-call-title";
    const num = document.createElement("span");
    num.className = "schema-cycle-call-num";
    num.textContent = `${index + 1}.`;
    title.appendChild(num);
    const paramEdit = makeCycleCallEditable("param", call.param || "", "param");
    paramEdit.className = "schema-cycle-call-heading-param";
    title.appendChild(paramEdit);
    const dash = document.createElement("span");
    dash.className = "schema-cycle-call-dash";
    dash.textContent = "—";
    title.appendChild(dash);
    const labelEdit = makeCycleCallEditable("label", cycleCallLabel(call), "заголовок");
    labelEdit.className = "schema-cycle-call-heading-label";
    title.appendChild(labelEdit);
    li.appendChild(title);

    const codes = document.createElement("div");
    codes.className = "schema-cycle-call-codes";
    const codesPrefix = document.createElement("span");
    codesPrefix.className = "schema-cycle-call-codes-prefix";
    codesPrefix.textContent = "коды:";
    codes.appendChild(codesPrefix);
    const sectionsEdit = makeCycleCallEditable("sections", cycleCallSections(call).join(", "), "раздел");
    sectionsEdit.className = "schema-cycle-call-codes-value";
    codes.appendChild(sectionsEdit);
    li.appendChild(codes);

    const indexLine = document.createElement("div");
    indexLine.className = "schema-cycle-call-index";
    indexLine.textContent = `${index + 1} / ${calls.length}`;
    li.appendChild(indexLine);

    const agentLabel = document.createElement("label");
    const agentSpan = document.createElement("span");
    agentSpan.textContent = "agent";
    const agentSelect = document.createElement("select");
    agentSelect.dataset.field = "agent";
    fillSubagentSelect(agentSelect, call.agent || node.subagent || "");
    agentLabel.appendChild(agentSpan);
    agentLabel.appendChild(agentSelect);
    li.appendChild(agentLabel);

    const paramLabel = document.createElement("label");
    const paramSpan = document.createElement("span");
    paramSpan.textContent = "param";
    const paramInput = document.createElement("input");
    paramInput.dataset.field = "param";
    paramInput.value = call.param || "";
    paramInput.spellcheck = false;
    paramLabel.appendChild(paramSpan);
    paramLabel.appendChild(paramInput);
    li.appendChild(paramLabel);

    const skillsLabel = document.createElement("label");
    const skillsSpan = document.createElement("span");
    skillsSpan.textContent = "skills";
    const skillsInput = document.createElement("input");
    skillsInput.dataset.field = "skills";
    skillsInput.value = Array.isArray(call.skills) ? call.skills.join(", ") : "";
    skillsInput.placeholder = "через запятую";
    skillsInput.spellcheck = false;
    skillsLabel.appendChild(skillsSpan);
    skillsLabel.appendChild(skillsInput);
    li.appendChild(skillsLabel);

    const actions = document.createElement("div");
    actions.className = "schema-cycle-call-actions";
    const up = document.createElement("button");
    up.type = "button";
    up.className = "btn-secondary";
    up.dataset.action = "up";
    up.textContent = "↑";
    up.disabled = index === 0;
    const down = document.createElement("button");
    down.type = "button";
    down.className = "btn-secondary";
    down.dataset.action = "down";
    down.textContent = "↓";
    down.disabled = index === calls.length - 1;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn-secondary";
    remove.dataset.action = "remove";
    remove.textContent = "Убрать";
    actions.appendChild(up);
    actions.appendChild(down);
    actions.appendChild(remove);
    li.appendChild(actions);
    list.appendChild(li);
  });
}

function fillSchemaCycleFields(node) {
  const wrap = document.getElementById("schema-cycle-fields");
  if (!wrap) return;
  const isCycle = nodeUiKind(node) === "cycle";
  wrap.classList.toggle("hidden", !isCycle);
  if (!isCycle) return;
  const cycle = normalizeCycle(node.cycle);
  const persistent = document.getElementById("schema-cycle-persistent");
  const assemble = document.getElementById("schema-cycle-assemble");
  const param = document.getElementById("schema-cycle-param");
  const folder = document.getElementById("schema-cycle-folder");
  const out = document.getElementById("schema-cycle-out");
  const itemFile = document.getElementById("schema-cycle-item-file");
  if (persistent) persistent.checked = cycle.persistent !== false;
  if (assemble) assemble.value = cycle.assemble || "";
  if (param) param.value = cycle.param || "";
  if (folder) folder.value = cycle.folder || "";
  if (out) out.value = cycle.out || "";
  if (itemFile) itemFile.value = cycle.item_file || "";
  syncCycleQueueChrome(node);
  renderCycleCalls(cycle, node);
  loadWriteFeatureCycleFallback().then(() => {
    if (selectedNodeId !== node.id) return;
    const current = packNodeById(node.id) || node;
    syncCycleQueueChrome(current);
    renderCycleCalls(normalizeCycle(current.cycle), current);
    refreshSelectedCycleCanvas(current);
  });
}

function patchSelectedCycleCall(index, field, value) {
  const node = selectedCycleNode();
  if (!node) return;
  const mode = cycleQueueMode(node);
  const cycle = applyCycleQueueMode(normalizeCycle(node.cycle), mode);
  const calls = [...(cycle.calls || [])];
  if (!calls[index]) return;
  const next = { ...calls[index], [field]: value };
  if (isForbiddenCycleCall(next)) {
    setSchemaInspectorError("analyze-routing нельзя ставить между блоками cycle.");
    fillSchemaCycleFields(node);
    return;
  }
  calls[index] = normalizeCycleCall(next);
  cycle.calls = calls;
  setSchemaInspectorError("");
  commitSelectedCycle(cycle);
}

function readCycleCallEditorValue(el) {
  const field = el.dataset.field;
  const raw = el.matches("input, select") ? el.value : el.textContent || "";
  if (field === "sections") return parseCycleCallSections(raw);
  return raw;
}

function handleCycleCallFieldEdit(event) {
  if (schemaInspectorSyncing) return;
  const el = event.target.closest("[data-field]");
  if (!el || !el.dataset.field) return;
  const row = el.closest(".schema-cycle-call");
  if (!row) return;
  const index = Number(row.dataset.index);
  if (Number.isNaN(index)) return;
  const field = el.dataset.field;
  const value = readCycleCallEditorValue(el);
  if (field === "param") {
    const heading = row.querySelector('[contenteditable][data-field="param"]');
    const input = row.querySelector('input[data-field="param"]');
    const text = String(value || "");
    if (el.isContentEditable && input && input !== el) input.value = text;
    if (!el.isContentEditable && heading && heading !== document.activeElement) heading.textContent = text;
  }
  patchSelectedCycleCall(index, field, value);
}

function addSchemaCycleCall() {
  const node = selectedCycleNode();
  if (!node) return;
  const mode = cycleQueueMode(node);
  const cycle = applyCycleQueueMode(normalizeCycle(node.cycle), mode);
  const calls = [...(cycle.calls || [])];
  const call = normalizeCycleCall({
    agent: node.subagent || "",
    param: uniqueCycleCallParam(calls),
  });
  if (isForbiddenCycleCall(call)) {
    setSchemaInspectorError("analyze-routing нельзя ставить между блоками cycle.");
    return;
  }
  calls.push(call);
  cycle.calls = calls;
  setSchemaInspectorError("");
  commitSelectedCycle(cycle, { discrete: true, rebuild: true });
}

function moveSchemaCycleCall(index, delta) {
  const node = selectedCycleNode();
  if (!node) return;
  const mode = cycleQueueMode(node);
  const cycle = applyCycleQueueMode(normalizeCycle(node.cycle), mode);
  const calls = [...(cycle.calls || [])];
  const nextIndex = index + delta;
  if (nextIndex < 0 || nextIndex >= calls.length) return;
  const swap = calls[index];
  calls[index] = calls[nextIndex];
  calls[nextIndex] = swap;
  cycle.calls = calls;
  commitSelectedCycle(cycle, { discrete: true, rebuild: true });
}

function removeSchemaCycleCall(index) {
  const node = selectedCycleNode();
  if (!node) return;
  const mode = cycleQueueMode(node);
  const cycle = applyCycleQueueMode(normalizeCycle(node.cycle), mode);
  const calls = [...(cycle.calls || [])];
  calls.splice(index, 1);
  if (calls.length) cycle.calls = calls;
  else delete cycle.calls;
  commitSelectedCycle(cycle, { discrete: true, rebuild: true });
}

async function fillSchemaCycleFromCatalog() {
  const node = selectedCycleNode();
  if (!node) return;
  await loadWriteFeatureCycleFallback();
  const preview = writeFeatureCatalogCalls();
  if (!preview.length) {
    setSchemaInspectorError("Каталог блоков недоступен.");
    syncCycleQueueChrome(node);
    return;
  }
  const mode = cycleQueueMode(node);
  const cycle = applyCycleQueueMode(normalizeCycle(node.cycle), mode);
  cycle.calls = preview.map((call) =>
    normalizeCycleCall({
      agent: call.agent,
      param: call.param,
      skills: call.skills,
      label: call.label,
      sections: call.sections,
    })
  );
  setSchemaInspectorError("");
  commitSelectedCycle(cycle, { discrete: true, rebuild: true });
}

async function seedAuthoredCycleCalls(packId, basePack) {
  // Fill incomplete cycle cells in the *draft* (kind=cycle on canvas), not only YAML.
  // Shell fields + sihist calls come from write-feature catalog; YAML is untouched until Apply.
  const draft = getPackDraft(packId);
  draft.seededCycleCalls = { ...(draft.seededCycleCalls || {}) };
  await loadWriteFeatureCycleFallback();
  const defaults = writeFeatureCycleDefaults();
  const preview = writeFeatureCatalogCalls();
  const live = applyDraftToPack(basePack, draft);
  let changed = false;
  for (const node of live?.graph?.nodes || []) {
    if (!node?.id || !node.cycle) continue;
    if (!cycleNeedsCatalogFill(node)) {
      draft.seededCycleCalls[node.id] = true;
      continue;
    }
    const merged = normalizeCycle({ ...defaults, ...node.cycle });
    for (const key of ["assemble", "param", "folder", "out", "item_file"]) {
      if (!merged[key]) merged[key] = defaults[key];
    }
    merged.persistent = merged.persistent !== false;
    // Keep ask_queue / queue mode from the node; do not force "зафиксировать".
    const cycle = applyCycleQueueMode(merged, cycleQueueMode({ cycle: merged }));
    if (!Array.isArray(cycle.calls) || !cycle.calls.length) {
      if (!preview.length) continue;
      cycle.calls = preview.map((call) =>
        normalizeCycleCall({
          agent: call.agent,
          param: call.param,
          skills: call.skills,
          label: call.label,
          sections: call.sections,
        })
      );
    }
    draft.nodeEdits = { ...(draft.nodeEdits || {}) };
    draft.nodeEdits[node.id] = {
      ...(draft.nodeEdits[node.id] || {}),
      uiKind: "cycle",
      cycle,
    };
    draft.seededCycleCalls[node.id] = true;
    changed = true;
  }
  if (changed) setPackDraft(packId, draft);
  return getPackDraft(packId);
}

function setCycleQueueMode(mode) {
  const node = selectedCycleNode();
  if (!node) return;
  const cycle = applyCycleQueueMode(normalizeCycle(node.cycle), mode);
  setSchemaInspectorError("");
  commitSelectedCycle(cycle, { discrete: true, rebuild: true });
}

function resetSchemaInspectorForms() {
  document.getElementById("schema-inspector-empty")?.classList.remove("hidden");
  document.getElementById("schema-node-form")?.classList.add("hidden");
  document.getElementById("schema-edge-form")?.classList.add("hidden");
  document.getElementById("schema-outgoing")?.classList.add("hidden");
  setSchemaInspectorError("");
  schemaInspectorUndoArmed = false;
}

function schemaCanvasIssues(pack) {
  const nodes = pack?.graph?.nodes || [];
  const edges = pack?.graph?.edges || [];
  const ids = new Set(nodes.map((node) => node.id));
  const issues = [];
  const orch = nodes.filter((node) => node.kind === "orchestrator");
  if (orch.length === 0) issues.push("Нет оркестратора — нужен ровно один.");
  else if (orch.length > 1) {
    issues.push(`Оркестраторов ${orch.length} — нужен один (${orch.map((n) => n.id).join(", ")}).`);
  }
  const dangling = edges.filter((edge) => !edge.from || !edge.to || !ids.has(edge.from) || !ids.has(edge.to));
  if (dangling.length) issues.push(`Рёбер в пустоту: ${dangling.length} (в черновик не пишем).`);
  return issues;
}

function renderSchemaCanvasIssues(pack) {
  const el = document.getElementById("schema-canvas-issues");
  if (!el) return;
  const issues = schemaCanvasIssues(pack);
  el.textContent = issues.join(" ");
  el.classList.toggle("hidden", !issues.length);
}

function edgeLooksLikeAgentFinished(edge) {
  const parts = [
    edge?.label,
    edge?.condition_label,
    edge?.condition,
    ...(Array.isArray(edge?.conditions)
      ? edge.conditions.map((item) => (typeof item === "string" ? item : item?.id || item?.label || ""))
      : []),
    ...Object.values(edge?.condition_labels || {}),
  ];
  const blob = parts.join(" ").toLowerCase();
  return blob.includes("zakonchil") || blob.includes("закончил");
}

function edgeIsAfterStep(edge) {
  if (!edge) return false;
  if (edge.after_step === true) return true;
  if (String(edge.to || "") !== ROUTING_STEP) return false;
  if (String(edge.kind || "") === "loop" && edgeLooksLikeAgentFinished(edge)) return true;
  return false;
}

function canUseAfterStepMode(edge) {
  if (!edge || String(edge.to || "") !== ROUTING_STEP) return false;
  const from = packNodeById(edge.from);
  if (!from) return true;
  return from.kind !== "orchestrator";
}

function afterStepEdgePatch(label) {
  return {
    after_step: true,
    kind: "loop",
    label: String(label || "").trim() || AFTER_STEP_LABEL,
    condition: "",
    condition_label: "",
    conditions: [],
    condition_labels: {},
  };
}

function packEdgeById(edgeId) {
  return (state.pack?.graph?.edges || []).find((edge) => edge.id === edgeId) || null;
}

function packEdgeTooltip(edge) {
  const lines = [`${edge.from} → ${edge.to}`, `kind: ${edge.kind || "main"}`];
  if (edgeIsAfterStep(edge)) {
    lines.push("тип: после завершения шага → analyze-routing");
    lines.push("не bool / нет when: в routing-state");
  } else {
    const ids = edgeConditionIds(edge);
    if (!ids.length) {
      lines.push("условие: нет");
    } else if (ids.length === 1) {
      lines.push(`условие (bool): ${formatConditionId(ids[0], edge)}`);
    } else {
      lines.push(`условия (bool): ${ids.join(", ")}`);
      ids.forEach((id) => lines.push(`  ${formatConditionId(id, edge)}`));
    }
  }
  const when = conditionTextForEdge(edge);
  if (edge.label && edge.label !== when && !edgeIsAfterStep(edge)) lines.push(`подпись: ${edge.label}`);
  if (edgeIsAfterStep(edge) && edge.label) lines.push(`подпись: ${edge.label}`);
  const fromNode = packNodeById(edge.from);
  if (fromNode?.ask) {
    lines.push("стрелка после apply; между вопросом и apply перехода нет");
  }
  lines.push("черновик: YAML не пишется");
  return lines.join("\n");
}

function outgoingEdgesFrom(nodeId) {
  if (!nodeId) return [];
  return (state.pack?.graph?.edges || []).filter((edge) => edge.from === nodeId);
}

function packEdgeCanvasLabel(edge) {
  if (edgeIsAfterStep(edge)) {
    return edge.label || AFTER_STEP_LABEL;
  }
  const ids = edgeConditionIds(edge);
  if (ids.length) {
    return ids.map((id) => conditionHumanLabel(id, edge) || id).join(" · ");
  }
  return edge.label || "";
}

function highlightSchemaSelection() {
  if (!cy || !isSchemaMode()) return;
  const outgoing = outgoingEdgesFrom(selectedNodeId);
  const outgoingIds = new Set(outgoing.map((edge) => edge.id).filter(Boolean));
  const focus = Boolean(selectedNodeId || selectedEdgeId);
  cy.edges(".schema-edge").forEach((el) => {
    const id = el.id();
    const edge = packEdgeById(id);
    const isOut = outgoingIds.has(id);
    const isSel = selectedEdgeId === id;
    el.removeClass("outgoing dim selected");
    if (isSel) el.addClass("selected");
    if (isOut) el.addClass("outgoing");
    else if (focus && !isSel) el.addClass("dim");
    const show = isOut || isSel;
    el.data("label", show && edge ? packEdgeCanvasLabel(edge) : "");
  });
  highlightSaveErrors();
}

function renderOutgoingEdges(node) {
  const wrap = document.getElementById("schema-outgoing");
  const list = document.getElementById("schema-outgoing-list");
  if (!wrap || !list) return;
  if (!node) {
    wrap.classList.add("hidden");
    list.innerHTML = "";
    return;
  }
  wrap.classList.remove("hidden");
  const edges = outgoingEdgesFrom(node.id);
  list.innerHTML = "";
  if (!edges.length) {
    const empty = document.createElement("p");
    empty.className = "schema-outgoing-empty";
    empty.textContent = "Нет исходящих стрелок. Shift+клик или «Стрелка к…».";
    list.appendChild(empty);
    return;
  }
  for (const edge of edges) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "schema-outgoing-item";
    item.dataset.edgeId = edge.id || "";
    const to = document.createElement("span");
    to.className = "schema-outgoing-to";
    const target = packNodeById(edge.to);
    to.textContent = `→ ${target?.label || edge.to}`;
    const when = document.createElement("span");
    const ids = edgeConditionIds(edge);
    const text = ids.length ? ids.map((id) => formatConditionId(id, edge)).join(" · ") : "";
    when.className = text ? "schema-outgoing-when" : "schema-outgoing-when is-empty";
    when.textContent = text || "без условия";
    item.append(to, when);
    list.appendChild(item);
  }
}

function selectSchemaEdge(edgeId) {
  if (!edgeId || !packEdgeById(edgeId)) return;
  selectedEdgeId = edgeId;
  selectedNodeId = null;
  selectedElementId = edgeId;
  highlightNode(null, null);
  showSchemaInspector();
}

function commitSchemaDraft(draft, opts = {}) {
  const cleaned = sanitizePackDraft(draft);
  setPackDraft(state.packId, cleaned);
  state.pack = applyDraftToPack(
    state.packBase || { id: state.packId, graph: { nodes: [], edges: [] } },
    cleaned
  );
  if (!opts.keepSave) invalidatePackSave();
  if (opts.selectNode) {
    selectedNodeId = opts.selectNode;
    selectedEdgeId = null;
    selectedElementId = opts.selectNode;
  }
  if (opts.selectEdge) {
    selectedEdgeId = opts.selectEdge;
    selectedNodeId = null;
    selectedElementId = opts.selectEdge;
  }
  renderPackGraph(state.pack, { skipFit: opts.skipFit !== false });
}

function originalPackNodeId(currentId, draft) {
  for (const [orig, edit] of Object.entries(draft.nodeEdits || {})) {
    if (edit?.id === currentId) return orig;
  }
  return currentId;
}

function patchDraftNode(draft, nodeId, patch) {
  const extras = draft.extraNodes || [];
  const idx = extras.findIndex((node) => node.id === nodeId);
  if (idx >= 0) {
    extras[idx] = extraNodePayload({ ...extras[idx], ...patch });
    draft.extraNodes = extras;
    return;
  }
  const origId = originalPackNodeId(nodeId, draft);
  draft.nodeEdits = { ...(draft.nodeEdits || {}) };
  draft.nodeEdits[origId] = { ...(draft.nodeEdits[origId] || {}), ...patch };
}

function patchDraftEdge(draft, edgeId, patch) {
  const ids = new Set((state.pack?.graph?.nodes || []).map((node) => node.id));
  const extras = draft.extraEdges || [];
  const idx = extras.findIndex((edge) => edge.id === edgeId);
  const current = idx >= 0 ? extras[idx] : packEdgeById(edgeId) || {};
  const prevPatch = (draft.edgeEdits || {})[edgeId] || {};
  const nextPatch = resolveEdgeConditionPatch(current, prevPatch, patch) || {};
  const nextFrom = nextPatch.from !== undefined ? nextPatch.from : prevPatch.from ?? current.from;
  const nextTo = nextPatch.to !== undefined ? nextPatch.to : prevPatch.to ?? current.to;
  if (!nextFrom || !nextTo) return "from и to не могут быть пустыми.";
  if (!ids.has(nextFrom) || !ids.has(nextTo)) return "Ребро только между существующими клетками.";
  if (idx >= 0) {
    extras[idx] = { ...extras[idx], ...nextPatch, from: nextFrom, to: nextTo };
    draft.extraEdges = extras;
    return "";
  }
  draft.edgeEdits = { ...(draft.edgeEdits || {}) };
  draft.edgeEdits[edgeId] = { ...prevPatch, ...nextPatch };
  return "";
}

function uniqueSchemaEdgeId(from, to) {
  const used = new Set((state.pack?.graph?.edges || []).map((edge) => edge.id).filter(Boolean));
  const base = `e-${from}-${to}`;
  if (!used.has(base)) return base;
  let i = 2;
  while (used.has(`${base}-${i}`)) i += 1;
  return `${base}-${i}`;
}

function setSchemaConnectFrom(nodeId) {
  schemaConnectFrom = nodeId || null;
  document.body.classList.toggle("schema-connecting", Boolean(schemaConnectFrom));
  const hint = document.getElementById("schema-connect-hint");
  if (hint) {
    hint.classList.toggle("hidden", !schemaConnectFrom);
    if (schemaConnectFrom) {
      const fromNode = packNodeById(schemaConnectFrom);
      hint.textContent = fromNode?.ask
        ? `Стрелка от ask «${schemaConnectFrom}»: путь после apply. Между вопросом и apply перехода на другого агента нет.`
        : `Стрелка от «${schemaConnectFrom}»: кликните целевую клетку (Esc — отмена)`;
    }
  }
  highlightNode(selectedNodeId, null);
}

function cancelSchemaConnect() {
  setSchemaConnectFrom(null);
}

function beginSchemaConnect(fromId) {
  if (!fromId) return;
  setSchemaConnectFrom(fromId);
}

function finishSchemaConnect(toId) {
  const fromId = schemaConnectFrom;
  cancelSchemaConnect();
  if (!fromId || !toId) return;
  const fromNode = packNodeById(fromId);
  const fields =
    toId === ROUTING_STEP && fromNode?.kind !== "orchestrator"
      ? { kind: "loop", after_step: true, label: AFTER_STEP_LABEL }
      : { kind: "main" };
  addSchemaEdge(fromId, toId, fields);
}

function addSchemaEdge(from, to, fields = {}) {
  if (!isSchemaMode()) return;
  if (!from || !to) {
    setSchemaInspectorError("Нельзя сохранить ребро в пустоту.");
    return;
  }
  if (from === to) {
    setSchemaInspectorError("Петля на ту же клетку не нужна — выберите другую.");
    return;
  }
  const ids = new Set((state.pack?.graph?.nodes || []).map((node) => node.id));
  if (!ids.has(from) || !ids.has(to)) {
    setSchemaInspectorError("Оба конца стрелки должны быть клетками на холсте.");
    return;
  }
  const fromNode = packNodeById(from);
  const afterStep =
    fields.after_step === true ||
    (to === ROUTING_STEP && fromNode?.kind !== "orchestrator" && fields.after_step !== false);
  pushSchemaUndo();
  const id = uniqueSchemaEdgeId(from, to);
  const draft = getPackDraft(state.packId);
  const edge = {
    id,
    from,
    to,
    kind: SCHEMA_EDGE_KINDS.includes(fields.kind) ? fields.kind : afterStep ? "loop" : "main",
    label: fields.label || (afterStep ? AFTER_STEP_LABEL : ""),
  };
  if (afterStep) {
    edge.after_step = true;
    edge.kind = "loop";
    if (!edge.label) edge.label = AFTER_STEP_LABEL;
  }
  draft.extraEdges = [...(draft.extraEdges || []), edge];
  commitSchemaDraft(draft, { selectEdge: id, skipFit: true });
  setSchemaInspectorError(
    fromNode?.ask
      ? "Стрелка с ask-клетки — только после apply. Между вопросом и apply перехода на другого агента нет."
      : afterStep
        ? "Стрелка «после завершения» → analyze-routing (не bool-условие)."
        : ""
  );
}

function deleteSchemaEdge(edgeId) {
  if (!edgeId || !isSchemaMode()) return;
  pushSchemaUndo();
  const draft = getPackDraft(state.packId);
  const extraIds = new Set((draft.extraEdges || []).map((edge) => edge.id));
  if (extraIds.has(edgeId)) {
    draft.extraEdges = (draft.extraEdges || []).filter((edge) => edge.id !== edgeId);
  } else {
    draft.deletedEdgeIds = Array.from(new Set([...(draft.deletedEdgeIds || []), edgeId]));
  }
  if (draft.edgeEdits) delete draft.edgeEdits[edgeId];
  if (selectedEdgeId === edgeId) {
    selectedEdgeId = null;
    selectedElementId = null;
  }
  commitSchemaDraft(draft, { skipFit: true });
}

function armInspectorUndo() {
  if (schemaInspectorSyncing || schemaInspectorUndoArmed) return false;
  pushSchemaUndo();
  schemaInspectorUndoArmed = true;
  return true;
}

function orchestratorCount(pack) {
  return (pack?.graph?.nodes || []).filter((node) => node.kind === "orchestrator").length;
}

function applyNodeKindChange(nodeId, uiKind) {
  const node = packNodeById(nodeId);
  if (!node) return false;
  if (!SCHEMA_NODE_KINDS.includes(uiKind)) {
    setSchemaInspectorError("Неизвестный kind.");
    return false;
  }
  if (uiKind !== "orchestrator" && node.kind === "orchestrator" && orchestratorCount(state.pack) <= 1) {
    setSchemaInspectorError("Нужен ровно один оркестратор. Сначала назначьте оркестратором другую клетку.");
    return false;
  }
  armInspectorUndo();
  const draft = getPackDraft(state.packId);
  const patched = applyUiKindToNode(node, uiKind);
  let cycle = patched.cycle ? normalizeCycle(patched.cycle) : null;
  if (uiKind === "cycle" && cycle) {
    const defaults = writeFeatureCycleDefaults();
    cycle = normalizeCycle({ ...defaults, ...cycle });
    for (const key of ["assemble", "param", "folder", "out", "item_file"]) {
      if (!cycle[key]) cycle[key] = defaults[key];
    }
    cycle = applyCycleQueueMode(cycle, packCycleCalls({ cycle }).length ? cycleQueueMode({ cycle }) : "pinned");
  }
  patchDraftNode(draft, nodeId, {
    uiKind,
    kind: patched.kind,
    ask: patched.ask === true,
    cycle,
    label: patched.label,
    subagent: patched.subagent,
  });
  if (uiKind === "cycle") {
    delete (draft.seededCycleCalls || {})[nodeId];
  }
  if (uiKind === "orchestrator") {
    const live = applyDraftToPack(state.packBase, draft);
    for (const other of live.graph.nodes || []) {
      if (other.id === nodeId || other.kind !== "orchestrator") continue;
      const demoted = applyUiKindToNode(other, "step");
      patchDraftNode(draft, other.id, {
        uiKind: "step",
        kind: "step",
        ask: false,
        cycle: null,
        label: demoted.label,
        subagent: demoted.subagent,
      });
    }
    draft.orchestrator = nodeId;
  } else if (draft.orchestrator === nodeId) {
    draft.orchestrator = "";
  }
  commitSchemaDraft(draft, { selectNode: nodeId, skipFit: true });
  setSchemaInspectorError("");
  if (uiKind === "cycle" && state.packBase) {
    const packId = state.packId;
    seedAuthoredCycleCalls(packId, state.packBase).then(() => {
      if (state.packId !== packId) return;
      commitSchemaDraft(getPackDraft(packId), { selectNode: nodeId, skipFit: true });
    });
  }
  return true;
}

function renameSchemaNode(oldId, newIdRaw) {
  const newId = String(newIdRaw || "").trim();
  if (newId === oldId) return true;
  if (!newId) {
    setSchemaInspectorError("id не может быть пустым.");
    return false;
  }
  if (packNodeById(newId)) {
    setSchemaInspectorError(`id «${newId}» уже занят.`);
    return false;
  }
  armInspectorUndo();
  const draft = getPackDraft(state.packId);
  const extras = draft.extraNodes || [];
  const extraIdx = extras.findIndex((node) => node.id === oldId);
  if (extraIdx >= 0) {
    extras[extraIdx] = { ...extras[extraIdx], id: newId };
    draft.extraNodes = extras;
  } else {
    const origId = originalPackNodeId(oldId, draft);
    draft.nodeEdits = { ...(draft.nodeEdits || {}) };
    draft.nodeEdits[origId] = { ...(draft.nodeEdits[origId] || {}), id: newId };
  }
  if (draft.positions?.[oldId]) {
    draft.positions[newId] = draft.positions[oldId];
    delete draft.positions[oldId];
  }
  draft.extraEdges = (draft.extraEdges || []).map((edge) => ({
    ...edge,
    from: edge.from === oldId ? newId : edge.from,
    to: edge.to === oldId ? newId : edge.to,
  }));
  for (const [edgeId, patch] of Object.entries(draft.edgeEdits || {})) {
    const next = { ...patch };
    if (next.from === oldId) next.from = newId;
    if (next.to === oldId) next.to = newId;
    draft.edgeEdits[edgeId] = next;
  }
  if (draft.orchestrator === oldId) draft.orchestrator = newId;
  if (Array.isArray(draft.dispatchRules)) {
    draft.dispatchRules = draft.dispatchRules.map((rule) =>
      rule.next === oldId ? { ...rule, next: newId } : rule
    );
  }
  selectedNodeId = newId;
  selectedElementId = newId;
  commitSchemaDraft(draft, { selectNode: newId, skipFit: true });
  setSchemaInspectorError("");
  return true;
}

function refreshSchemaElementVisuals() {
  if (!cy || !isSchemaMode()) return;
  for (const node of state.pack?.graph?.nodes || []) {
    const el = cy.getElementById(node.id);
    if (!el.length) continue;
    el.data("label", formatPackNodeLabel(node));
    el.data("color", packNodeColor(node));
    el.data("kind", node.kind || "step");
    el.data("askFlag", node.ask ? "true" : "false");
    el.data("cycleFlag", node.cycle ? "true" : "false");
    applyCycleNodePresentation(el, node);
    el.removeClass("draft-added cli-missing");
    const classes = packNodeClasses(node);
    if (classes) el.addClass(classes);
  }
  for (const edge of state.pack?.graph?.edges || []) {
    if (!edge.id) continue;
    const el = cy.getElementById(edge.id);
    if (!el.length) continue;
    el.data("label", packEdgeCanvasLabel(edge));
    el.data("kind", edge.kind || "main");
    el.data("color", PACK_EDGE_COLORS[edge.kind] || PACK_EDGE_COLORS.main);
    el.data("source", edge.from);
    el.data("target", edge.to);
  }
  renderPackSummary(state.pack);
  highlightSchemaSelection();
}

function persistDraftWithoutFit(draft) {
  const cleaned = sanitizePackDraft(draft);
  setPackDraft(state.packId, cleaned);
  state.pack = applyDraftToPack(
    state.packBase || { id: state.packId, graph: { nodes: [], edges: [] } },
    cleaned
  );
  invalidatePackSave();
}

function applyNodeFieldPatch(nodeId, patch, opts = {}) {
  armInspectorUndo();
  const draft = getPackDraft(state.packId);
  patchDraftNode(draft, nodeId, patch);
  persistDraftWithoutFit(draft);
  if (opts.rebuild) {
    commitSchemaDraft(getPackDraft(state.packId), { selectNode: nodeId, skipFit: true });
    return;
  }
  refreshSchemaElementVisuals();
}

function applyEdgeFieldPatch(edgeId, patch, opts = {}) {
  const pushed = armInspectorUndo();
  const draft = getPackDraft(state.packId);
  const err = patchDraftEdge(draft, edgeId, patch);
  if (err) {
    if (pushed) {
      schemaUndoStack(state.packId).past.pop();
      schemaInspectorUndoArmed = false;
      updateSchemaUndoChrome();
    }
    setSchemaInspectorError(err);
    showSchemaInspector();
    return false;
  }
  persistDraftWithoutFit(draft);
  if (opts.rebuild) {
    commitSchemaDraft(getPackDraft(state.packId), { selectEdge: edgeId, skipFit: true });
    setSchemaInspectorError("");
    return true;
  }
  refreshSchemaElementVisuals();
  setSchemaInspectorError("");
  return true;
}

function fillSchemaNodeForm(node) {
  schemaInspectorSyncing = true;
  const uiKind = nodeUiKind(node);
  const idEl = document.getElementById("schema-node-id");
  const labelEl = document.getElementById("schema-node-label");
  const kindEl = document.getElementById("schema-node-kind");
  const hintEl = document.getElementById("schema-kind-hint");
  if (idEl) idEl.value = node.id;
  if (labelEl) labelEl.value = node.label || node.id;
  if (kindEl) kindEl.value = SCHEMA_NODE_KINDS.includes(uiKind) ? uiKind : "step";
  if (hintEl) hintEl.textContent = schemaKindHint(uiKind);
  fillSubagentSelect(document.getElementById("schema-node-subagent"), node.subagent || "");
  const askNote = document.getElementById("schema-ask-note");
  askNote?.classList.toggle("hidden", uiKind !== "ask");
  fillSchemaCycleFields(node);
  schemaInspectorSyncing = false;
}

function markSchemaEdgeKindNotes(kind) {
  const current = SCHEMA_EDGE_KINDS.includes(kind) ? kind : "main";
  document.querySelectorAll("#schema-edge-kind-notes [data-kind]").forEach((item) => {
    item.classList.toggle("is-current", item.dataset.kind === current);
  });
}

function renderSchemaEdgeConditions(edge) {
  const list = document.getElementById("schema-edge-conditions");
  const yamlEl = document.getElementById("schema-edge-condition-yaml");
  if (!list) return;
  const ids = edgeConditionIds(edge);
  const errors = state.packSave?.errors || [];
  list.innerHTML = "";
  if (!ids.length) {
    const empty = document.createElement("li");
    empty.className = "schema-edge-conditions-empty";
    empty.textContent = "Нет условий. Напишите текст по-русски и нажмите «Добавить».";
    list.appendChild(empty);
  } else {
    for (const id of ids) {
      const li = document.createElement("li");
      li.className = "schema-edge-condition";
      li.dataset.when = id;
      const hit = errors.some(
        (item) => item.when === id && (!item.edge || item.edge === edge.id)
      );
      if (hit) li.classList.add("is-save-error");
      const text = document.createElement("span");
      text.className = "schema-edge-condition-text";
      const human = conditionHumanLabel(id, edge);
      text.textContent = human && human !== id ? human : id;
      text.title = `when: ${id}`;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "btn-secondary";
      remove.dataset.removeWhen = id;
      remove.setAttribute("aria-label", `Убрать ${human || id}`);
      remove.textContent = "Убрать";
      li.append(text, remove);
      list.appendChild(li);
    }
  }
  if (!yamlEl) return;
  if (!ids.length) {
    yamlEl.textContent = "";
    yamlEl.classList.add("hidden");
    return;
  }
  yamlEl.textContent =
    ids.length === 1
      ? `система запишет: status_fields.${ids[0]} + dispatch when:${ids[0]}`
      : `система запишет: ${ids.map((id) => `when:${id}`).join(", ")}`;
  yamlEl.classList.remove("hidden");
}

function syncEdgeRoutingModeUi(edge) {
  const afterOk = canUseAfterStepMode(edge);
  const after = edgeIsAfterStep(edge);
  const afterWrap = document.getElementById("schema-edge-routing-after-wrap");
  const boolRadio = document.getElementById("schema-edge-routing-bool");
  const afterRadio = document.getElementById("schema-edge-routing-after");
  const condBlock = document.getElementById("schema-edge-conditions-block");
  const afterNote = document.getElementById("schema-edge-after-step-note");
  const boolHint = document.getElementById("schema-edge-bool-hint");
  afterWrap?.classList.toggle("hidden", !afterOk);
  if (boolRadio) boolRadio.checked = !after;
  if (afterRadio) afterRadio.checked = after;
  condBlock?.classList.toggle("hidden", after);
  afterNote?.classList.toggle("hidden", !after);
  boolHint?.classList.toggle("hidden", after);
}

function applySelectedEdgeRoutingMode(mode) {
  if (!selectedEdgeId) return;
  const edge = mergedDraftEdge(selectedEdgeId) || packEdgeById(selectedEdgeId);
  if (!edge) return;
  if (mode === "after_step") {
    if (!canUseAfterStepMode(edge)) {
      setSchemaInspectorError("«После завершения» только для стрелки к analyze-routing с рабочего шага.");
      syncEdgeRoutingModeUi(edge);
      return;
    }
    applyEdgeFieldPatch(selectedEdgeId, afterStepEdgePatch(edge.label), { rebuild: true });
    setSchemaInspectorError("");
    return;
  }
  const patch = {
    after_step: false,
  };
  if (edge.kind === "loop" && edgeIsAfterStep(edge)) {
    patch.kind = "branch";
  }
  if (edge.label === AFTER_STEP_LABEL) {
    patch.label = "";
  }
  applyEdgeFieldPatch(selectedEdgeId, patch, { rebuild: true });
  setSchemaInspectorError("");
}

function fillSchemaEdgeForm(edge) {
  schemaInspectorSyncing = true;
  fillNodeIdOptions(document.getElementById("schema-edge-from"), edge.from);
  fillNodeIdOptions(document.getElementById("schema-edge-to"), edge.to);
  const kindEl = document.getElementById("schema-edge-kind");
  const labelEl = document.getElementById("schema-edge-label");
  const addEl = document.getElementById("schema-edge-condition-add");
  const kind = SCHEMA_EDGE_KINDS.includes(edge.kind) ? edge.kind : "main";
  if (kindEl) kindEl.value = kind;
  if (labelEl) labelEl.value = edge.label || "";
  if (addEl) addEl.value = "";
  renderSchemaEdgeConditions(edge);
  markSchemaEdgeKindNotes(kind);
  syncEdgeRoutingModeUi(edge);
  schemaInspectorSyncing = false;
}

function ensureDispatchRuleForWhen(when, nextId) {
  const id = String(when || "").trim();
  if (!id) return;
  const rules = liveDispatchRules();
  if (rules.some((rule) => rule.when === id)) return;
  rules.push(ruleFromDispatchFields(nextDispatchPriority(rules), id, nextId || ""));
  commitDispatchRules(rules, { skipUndo: true });
}

function addSelectedEdgeCondition(rawText) {
  if (!selectedEdgeId) return;
  const edge = mergedDraftEdge(selectedEdgeId);
  if (!edge.from && !packEdgeById(selectedEdgeId)) return;
  if (edgeIsAfterStep(edge)) {
    setSchemaInspectorError("На петле «после завершения» нет bool-условия — переключите тип перехода.");
    return;
  }
  const raw = String(rawText || "").trim();
  if (!raw) {
    setSchemaInspectorError("Напишите условие по-русски.");
    return;
  }
  const parsed = conditionPatchFromText(raw);
  const id = parsed.condition;
  if (!id) {
    setSchemaInspectorError("Не удалось сделать id из этого текста.");
    return;
  }
  const ids = edgeConditionIds(edge);
  if (ids.includes(id)) {
    const addEl = document.getElementById("schema-edge-condition-add");
    if (addEl) addEl.value = "";
    setSchemaInspectorError("");
    return;
  }
  ids.push(id);
  const withLabel = {
    ...edge,
    condition_labels: {
      ...(edge.condition_labels || {}),
      ...(parsed.condition_labels || {}),
      ...(parsed.condition_label ? { [id]: parsed.condition_label } : {}),
    },
  };
  applyEdgeFieldPatch(selectedEdgeId, { ...conditionPatchFromIds(ids, withLabel), after_step: false });
  ensureDispatchRuleForWhen(id, edge.to);
  const addEl = document.getElementById("schema-edge-condition-add");
  if (addEl) addEl.value = "";
  setSchemaInspectorError("");
  const next = mergedDraftEdge(selectedEdgeId);
  fillSchemaEdgeForm(next);
  highlightSchemaSelection();
}

function removeSelectedEdgeCondition(whenId) {
  if (!selectedEdgeId || !whenId) return;
  const edge = mergedDraftEdge(selectedEdgeId);
  const ids = edgeConditionIds(edge).filter((id) => id !== whenId);
  applyEdgeFieldPatch(selectedEdgeId, conditionPatchFromIds(ids, edge));
  fillSchemaEdgeForm(mergedDraftEdge(selectedEdgeId));
  highlightSchemaSelection();
}

function showSchemaInspector() {
  const heading = document.getElementById("step-heading");
  const empty = document.getElementById("schema-inspector-empty");
  const nodeForm = document.getElementById("schema-node-form");
  const edgeForm = document.getElementById("schema-edge-form");
  setSchemaNodeActionsVisible(false);
  setSchemaEdgeActionsVisible(false);

  if (selectedEdgeId) {
    const edge = packEdgeById(selectedEdgeId);
    if (!edge) {
      selectedEdgeId = null;
      resetSchemaInspectorForms();
      if (heading) heading.textContent = "Инспектор";
      return;
    }
    if (heading) heading.textContent = "Стрелка";
    empty?.classList.add("hidden");
    nodeForm?.classList.add("hidden");
    edgeForm?.classList.remove("hidden");
    fillSchemaEdgeForm(edge);
    renderOutgoingEdges(null);
    setSchemaEdgeActionsVisible(true);
    return;
  }

  if (selectedNodeId) {
    const node = packNodeById(selectedNodeId);
    if (!node) {
      selectedNodeId = null;
      resetSchemaInspectorForms();
      if (heading) heading.textContent = "Инспектор";
      return;
    }
    if (heading) heading.textContent = "Клетка";
    empty?.classList.add("hidden");
    edgeForm?.classList.add("hidden");
    nodeForm?.classList.remove("hidden");
    fillSchemaNodeForm(node);
    renderOutgoingEdges(node);
    setSchemaNodeActionsVisible(true);
    return;
  }

  if (heading) heading.textContent = "Инспектор";
  resetSchemaInspectorForms();
}

function showPackNodeSummary(nodeId) {
  selectedNodeId = nodeId;
  selectedEdgeId = null;
  showSchemaInspector();
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

function formatPackNodeLabel(node, opts = {}) {
  const lines = [node.label || node.id];
  if (node.cycle) {
    const calls = packCycleCalls(node);
    const ask = cycleQueueMode(node) === "plan";
    if (opts.expanded) {
      lines.push("cycle");
      lines.push(ask ? "спросить при прогоне" : "зафиксировать");
      if (!calls.length) lines.push("calls: нет");
      else {
        calls.forEach((call, index) => {
          lines.push(`${index + 1}. ${call.param || "—"}`);
        });
      }
      lines.push("выход: on_done → внешний dispatch");
    } else if (ask) {
      lines.push(calls.length ? `cycle · спросить · ${calls.length}` : "cycle · спросить");
    } else {
      lines.push(calls.length ? `cycle · ${calls.length}` : "cycle");
    }
  } else if (node.ask) lines.push("пауза · apply здесь");
  if (node.kind === "meta") lines.push("meta");
  return lines.join("\n");
}

function applyCycleNodePresentation(el, node) {
  if (!el || !node) return;
  const expanded = Boolean(node.cycle) && selectedNodeId === node.id && isSchemaMode();
  el.data("label", formatPackNodeLabel(node, { expanded }));
  el.data("expanded", expanded ? "true" : "false");
  if (!node.cycle) {
    el.removeStyle("height");
    el.removeStyle("width");
    el.removeStyle("font-size");
    el.removeStyle("text-max-width");
    return;
  }
  const calls = packCycleCalls(node);
  const n = calls.length;
  if (expanded) {
    const extra = cycleQueueMode(node) === "plan" ? 1 : 1;
    const rows = 3 + Math.max(n, 1) + extra;
    el.style("width", 228);
    el.style("height", Math.min(420, 40 + rows * 16));
    el.style("font-size", "11px");
    el.style("text-max-width", "216px");
  } else {
    el.style("width", 168);
    el.style("height", 74);
    el.style("font-size", "12px");
    el.style("text-max-width", "156px");
  }
}

function packNodeTooltip(node) {
  const lines = [node.label || node.id, `id: ${node.id}`, `kind: ${node.kind || "step"}`];
  if (node.subagent) lines.push(`subagent: ${node.subagent}`);
  else if (node.kind === "orchestrator") lines.push("оркестратор");
  if (node.draft) lines.push("черновик: клетка с палитры, не в YAML");
  const missing = node.subagent ? missingClisFor(node.subagent) : [];
  if (missing.length) lines.push(`нет в CLI: ${missing.join(", ")}`);
  if (node.ask) {
    lines.push("ask: пауза на этой клетке, apply без смены шага");
    lines.push("между вопросом и apply перехода на другого агента нет");
  }
  if (node.cycle && typeof node.cycle === "object") {
    const cycle = node.cycle;
    lines.push("cycle: как в YAML, одна клетка");
    if (cycle.assemble) lines.push(`assemble: ${cycle.assemble}`);
    if (cycle.param) lines.push(`param: ${cycle.param}`);
    if (cycle.folder) lines.push(`folder: ${cycle.folder}`);
    if (cycle.out) lines.push(`out: ${cycle.out}`);
    if (cycle.item_file) lines.push(`item_file: ${cycle.item_file}`);
    lines.push("close: on_done");
    const calls = packCycleCalls(node);
    if (cycleQueueMode(node) === "plan") {
      lines.push("очередь: спросить при прогоне по calls клетки");
    } else {
      lines.push("очередь: зафиксировать calls клетки");
    }
    if (!calls.length) lines.push("calls: нет");
    else {
      lines.push(`calls: ${calls.length}`);
      calls.forEach((call, index) => {
        lines.push(`  ${index + 1}. ${call.agent || "?"} · ${call.param || "—"}`);
      });
    }
  }
  return lines.join("\n");
}

function packEdgeLabel(edge) {
  const ids = edgeConditionIds(edge);
  if (ids.length) return ids.map((id) => formatConditionId(id, edge)).join(" · ");
  return edge.label || edge.condition_label || "";
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
        label: formatPackNodeLabel(node, {
          expanded: Boolean(node.cycle) && selectedNodeId === node.id,
        }),
        color: packNodeColor(node),
        kind,
        askFlag: node.ask ? "true" : "false",
        cycleFlag: node.cycle ? "true" : "false",
        expanded: node.cycle && selectedNodeId === node.id ? "true" : "false",
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
        label: "",
        color: PACK_EDGE_COLORS[kind] || PACK_EDGE_COLORS.main,
        kind,
      },
      classes: "schema-edge",
    });
  });
  return elements;
}

function renderPackSummary(pack) {
  const el = document.getElementById("pack-summary");
  const badge = document.getElementById("pack-badge");
  const graph = pack?.graph || {};
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  const draft = getPackDraft(state.packId);
  const extra = (draft.extraNodes || []).length;
  const extraEdges = (draft.extraEdges || []).length;
  const removed = (draft.deletedIds || []).length;
  const removedEdges = (draft.deletedEdgeIds || []).length;
  const edited =
    Object.keys(draft.nodeEdits || {}).length + Object.keys(draft.edgeEdits || {}).length;
  const draftBits = [];
  if (extra) draftBits.push(`+${extra} клеток`);
  if (extraEdges) draftBits.push(`+${extraEdges} стрелок`);
  if (removed) draftBits.push(`−${removed} клеток`);
  if (removedEdges) draftBits.push(`−${removedEdges} стрелок`);
  if (edited) draftBits.push("правки инспектора");
  if (Array.isArray(draft.dispatchRules)) draftBits.push("dispatch");
  const rules = liveDispatchRules();
  const text = [
    `id: ${pack?.id || "—"}`,
    `label: ${graph.label || "—"}`,
    `оркестратор: ${graph.orchestrator || "—"}`,
    `клеток: ${nodes.length} · стрелок: ${edges.length} · dispatch: ${rules.length}`,
    draftBits.length ? `черновик: ${draftBits.join(", ")}` : "черновик: координаты в браузере",
  ].join("\n");
  if (el) el.textContent = text;
  if (badge) {
    const mark = draftBits.length ? " · черновик" : "";
    badge.textContent = `${pack?.id || "—"} · ${nodes.length} клеток${mark}`;
  }
  renderSchemaCanvasIssues(pack);
}

function renderPackGraph(pack, opts = {}) {
  const empty = document.getElementById("empty-state");
  const nodes = pack?.graph?.nodes || [];
  const noGraph = !nodes.length;
  empty.classList.toggle("hidden", !noGraph);
  document.getElementById("cy").style.visibility = noGraph ? "hidden" : "visible";

  state.pack = pack;
  renderPackSummary(pack);
  renderSchemaDispatchTable();

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
  graph.nodes().forEach((el) => {
    const node = packNodeById(el.id());
    if (node) applyCycleNodePresentation(el, node);
  });
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
  updateSchemaUndoChrome();
  updateSchemaSaveChrome();
  highlightSaveErrors();

  if (selectedEdgeId && packEdgeById(selectedEdgeId)) {
    selectedNodeId = null;
    selectedElementId = selectedEdgeId;
    highlightNode(null, null);
    showSchemaInspector();
  } else if (selectedNodeId && packNodeById(selectedNodeId)) {
    selectedEdgeId = null;
    selectedElementId = selectedNodeId;
    highlightNode(selectedNodeId, null);
    showSchemaInspector();
  } else {
    selectedNodeId = null;
    selectedEdgeId = null;
    selectedElementId = null;
    highlightNode(null, null);
    showSchemaInspector();
  }
}

let packLoadSeq = 0;

async function pullServerAuthoringDraft(packId) {
  // Disk overlay for schema draft (pipelines/<id>/.authoring-draft.json) — not pack YAML.
  // Lets an agent fill cycle fields once; every browser picks them up before Apply.
  // Never override a cycle that already lives in pack YAML (after Apply / committed graph).
  try {
    const res = await fetch(`/api/pack/draft?pipeline=${encodeURIComponent(packId)}`);
    if (!res.ok) return getPackDraft(packId);
    const data = await parseJsonResponse(res);
    const remote = data && data.draft && typeof data.draft === "object" ? data.draft : null;
    if (!remote) return getPackDraft(packId);
    const draft = getPackDraft(packId);
    const remoteEdits = remote.nodeEdits && typeof remote.nodeEdits === "object" ? remote.nodeEdits : {};
    const baseById = {};
    for (const node of state.packBase?.graph?.nodes || []) {
      if (node?.id) baseById[node.id] = node;
    }
    let changed = false;
    draft.nodeEdits = { ...(draft.nodeEdits || {}) };
    for (const [nodeId, edit] of Object.entries(remoteEdits)) {
      if (!edit || typeof edit !== "object") continue;
      const remoteCycle = edit.cycle && typeof edit.cycle === "object" ? edit.cycle : null;
      if (!remoteCycle) continue;
      const baseCycle =
        baseById[nodeId]?.cycle && typeof baseById[nodeId].cycle === "object"
          ? baseById[nodeId].cycle
          : null;
      const baseComplete =
        Boolean(baseCycle?.assemble) &&
        Boolean(baseCycle?.folder) &&
        Array.isArray(baseCycle?.calls) &&
        baseCycle.calls.length > 0;
      // YAML already has a full cycle — stale disk draft must not flip ask_queue / calls.
      if (baseComplete) continue;
      const localEdit = draft.nodeEdits[nodeId] || {};
      const localCycle = localEdit.cycle && typeof localEdit.cycle === "object" ? localEdit.cycle : null;
      const localIncomplete =
        !localCycle ||
        !localCycle.assemble ||
        !localCycle.folder ||
        !Array.isArray(localCycle.calls) ||
        !localCycle.calls.length;
      const remoteComplete =
        remoteCycle.assemble &&
        remoteCycle.folder &&
        Array.isArray(remoteCycle.calls) &&
        remoteCycle.calls.length;
      if (localIncomplete && remoteComplete) {
        draft.nodeEdits[nodeId] = {
          ...localEdit,
          ...edit,
          uiKind: edit.uiKind || localEdit.uiKind || "cycle",
          cycle: remoteCycle,
        };
        draft.seededCycleCalls = { ...(draft.seededCycleCalls || {}), [nodeId]: true };
        changed = true;
      }
    }
    if (changed) setPackDraft(packId, draft);
    return getPackDraft(packId);
  } catch {
    return getPackDraft(packId);
  }
}

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
    await pullServerAuthoringDraft(packId);
    if (seq !== packLoadSeq || state.packId !== packId) return;
    const draft = await seedAuthoredCycleCalls(packId, data);
    if (seq !== packLoadSeq || state.packId !== packId) return;
    renderPackGraph(applyDraftToPack(data, draft));
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
    setSchemaEdgeActionsVisible(false);
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
  const node = extraNodePayload({
    id,
    label: agent,
    kind: "step",
    subagent: agent,
  });
  pushSchemaUndo();
  const draft = getPackDraft(state.packId);
  draft.extraNodes = [...(draft.extraNodes || []).filter((item) => item.id !== id), node];
  draft.deletedIds = (draft.deletedIds || []).filter((item) => item !== id);
  draft.positions = { ...(draft.positions || {}), [id]: position };
  commitSchemaDraft(draft, { selectNode: id, skipFit: true });
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
  pushSchemaUndo();
  cancelSchemaConnect();
  const draft = getPackDraft(state.packId);
  const extraIds = new Set((draft.extraNodes || []).map((node) => node.id));
  if (extraIds.has(nodeId)) {
    draft.extraNodes = (draft.extraNodes || []).filter((node) => node.id !== nodeId);
  } else {
    draft.deletedIds = Array.from(new Set([...(draft.deletedIds || []), nodeId]));
  }
  if (draft.positions) delete draft.positions[nodeId];
  if (draft.nodeEdits) {
    delete draft.nodeEdits[nodeId];
    for (const [orig, edit] of Object.entries(draft.nodeEdits)) {
      if (edit?.id === nodeId) delete draft.nodeEdits[orig];
    }
  }
  draft.extraEdges = (draft.extraEdges || []).filter(
    (edge) => edge.from !== nodeId && edge.to !== nodeId
  );
  const packEdges = state.packBase?.graph?.edges || [];
  for (const edge of packEdges) {
    const from = edge.from;
    const to = edge.to;
    if (from === nodeId || to === nodeId) {
      const id = edge.id;
      if (id) draft.deletedEdgeIds = Array.from(new Set([...(draft.deletedEdgeIds || []), id]));
    }
  }
  if (draft.orchestrator === nodeId) draft.orchestrator = "";
  selectedNodeId = null;
  selectedEdgeId = null;
  selectedElementId = null;
  commitSchemaDraft(draft, { skipFit: true });
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

function overlayPackBody() {
  const pack = state.pack || state.packBase || {};
  return {
    id: pack.id || state.packId,
    graph: pack.graph || { label: state.packId, orchestrator: "", nodes: [], edges: [] },
    dispatch: { rules: liveDispatchRules() },
    codegen: true,
  };
}

function loadAppliedStore() {
  try {
    const parsed = JSON.parse(localStorage.getItem(SAVE_STORAGE_KEY) || "{}");
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return { packs: {} };
    if (!parsed.packs || typeof parsed.packs !== "object") return { packs: {} };
    return parsed;
  } catch {
    return { packs: {} };
  }
}

function appliedRecord(packId) {
  return loadAppliedStore().packs?.[packId] || null;
}

function rememberAppliedOverlay(packId, rec) {
  const store = loadAppliedStore();
  store.packs = store.packs || {};
  store.packs[packId] = {
    previous: rec?.previous || null,
    last: rec?.last || null,
  };
  localStorage.setItem(SAVE_STORAGE_KEY, JSON.stringify(store));
  updateSchemaSaveChrome();
}

function invalidatePackSave() {
  if (!state.packSave?.ok && !(state.packSave?.errors || []).length) {
    updateSchemaSaveChrome();
    return;
  }
  state.packSave = { ok: false, errors: [], warnings: [], preview: null };
  updateSchemaSaveChrome();
  highlightSaveErrors();
}

function clipSaveText(text, max = 42) {
  const raw = String(text || "").replace(/\s+/g, " ").trim();
  if (raw.length <= max) return raw;
  return `${raw.slice(0, max - 1)}…`;
}

function looksLikeProseWhen(when) {
  const raw = String(when || "").trim();
  return /[а-яё]/i.test(raw) || /\s/.test(raw);
}

function saveErrorWhere(item) {
  if (item?.edge) {
    const edge = packEdgeById(item.edge);
    if (edge) return `${edge.from} → ${edge.to}`;
    return String(item.edge).replace(/^e-/, "");
  }
  if (item?.priority != null && item.priority !== "") return `P${item.priority}`;
  if (item?.node) return item.node;
  return "";
}

function humanSaveError(item) {
  const msg = String(item?.message || "");
  const when = String(item?.when || "").trim();
  const where = saveErrorWhere(item);
  if (/unknown when/i.test(msg) || /нет в каталоге when/i.test(msg)) {
    return `${where ? `${where}: ` : ""}when: ${when || "—"} — нет формулы, Проверить сделает stub.`;
  }
  if (/invalid next/i.test(msg) || /нет на холсте/i.test(msg)) {
    const node = item.node || when;
    const pri = item.priority != null && item.priority !== "" ? `P${item.priority}` : where;
    return `${pri}${when ? ` ${when}` : ""}: клетки «${node}» нет на холсте. Удалите правило или верните клетку.`;
  }
  if (/добавь правило|нет строки в таблице/i.test(msg)) {
    return `${where ? `${where}: ` : ""}для ${when || "условия"} нет строки в таблице dispatch.`;
  }
  if (/пустой when/i.test(msg)) {
    return `${where || "таблица"}: пустой when:.`;
  }
  return msg.replace(/\s*—\s*диск не пишется\.?$/i, "");
}

function formatSaveError(item) {
  return humanSaveError(item);
}

function syncSaveStatusVisibility() {
  const box = document.getElementById("schema-save-status");
  if (!box) return;
  const line = (document.getElementById("schema-save-status-line")?.textContent || "").trim();
  const errors = document.getElementById("schema-save-errors");
  const checklist = document.getElementById("schema-save-checklist");
  const hasErrors = errors && !errors.classList.contains("hidden") && errors.children.length > 0;
  const hasChecklist =
    checklist && !checklist.classList.contains("hidden") && checklist.children.length > 0;
  const visible = Boolean(line || hasErrors || hasChecklist);
  box.classList.toggle("hidden", !visible);
}

function dismissSaveStatus() {
  if (state.packSave && typeof state.packSave === "object") {
    state.packSave = { ...state.packSave, dismissed: true, checklist: [] };
  }
  setSaveStatus("", "");
  renderRunnableChecklist([], "schema-save-checklist");
}

function setSaveStatus(kind, line, errors) {
  const box = document.getElementById("schema-save-status");
  const lineEl = document.getElementById("schema-save-status-line");
  const list = document.getElementById("schema-save-errors");
  if (box) {
    box.classList.remove("is-ok", "is-error", "is-warn");
    if (kind) box.classList.add(kind);
  }
  if (lineEl) lineEl.textContent = line || "";
  else if (box && !list) box.textContent = line || "";
  if (!list) {
    syncSaveStatusVisibility();
    return;
  }
  list.innerHTML = "";
  const items = Array.isArray(errors) ? errors.filter(Boolean) : [];
  list.classList.toggle("hidden", !items.length);
  for (const item of items) {
    const row = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "schema-save-error";
    if (item.edge) btn.dataset.edgeId = item.edge;
    if (item.node) btn.dataset.nodeId = item.node;
    btn.textContent = humanSaveError(item);
    row.appendChild(btn);
    list.appendChild(row);
  }
  if (items.length) {
    renderRunnableChecklist([], "schema-save-checklist");
  }
  syncSaveStatusVisibility();
}

function updateSchemaSaveChrome() {
  const applyBtn = document.getElementById("schema-apply");
  const rollbackBtn = document.getElementById("schema-rollback");
  const deletePackBtn = document.getElementById("schema-delete-pack");
  const save = state.packSave || {};
  const errors = Array.isArray(save.errors) ? save.errors : [];
  const warnings = Array.isArray(save.warnings) ? save.warnings : [];
  const checklist = Array.isArray(save.checklist) ? save.checklist : [];
  if (applyBtn) {
    applyBtn.classList.toggle("hidden", !save.ok);
    applyBtn.disabled = !save.ok;
  }
  if (rollbackBtn) rollbackBtn.disabled = !appliedRecord(state.packId)?.previous;
  if (deletePackBtn) {
    deletePackBtn.disabled = !state.packId;
    deletePackBtn.title = "Удалить текущий пак с диска";
  }
  if (save.dismissed) {
    setSaveStatus("", "");
    renderRunnableChecklist([], "schema-save-checklist");
    return;
  }
  if (errors.length) {
    const n = errors.length;
    setSaveStatus("is-error", `${n} ${n === 1 ? "ошибка" : n < 5 ? "ошибки" : "ошибок"} — Применить скрыт, диск не пишется.`, errors);
    return;
  }
  if (save.ok) {
    const extra = warnings.length ? ` ${warnings.join("; ")}` : "";
    setSaveStatus("is-ok", `Проверка ок.${extra} Применить доступен, диск не писали.`);
    renderRunnableChecklist([], "schema-save-checklist");
    return;
  }
  if (checklist.length) {
    const checklistLine = checklist.map((item) => `${item.ok ? "✓" : "✗"} ${item.label}`).join(" · ");
    const prefix = save.applyDone ? "Записано. " : "";
    setSaveStatus(
      checklist.some((item) => !item.ok) ? "is-warn" : "is-ok",
      `${prefix}Runnable: ${checklistLine}`
    );
    renderRunnableChecklist(checklist, "schema-save-checklist");
    return;
  }
  if (warnings.length) {
    setSaveStatus("is-warn", warnings.join(" · "));
    renderRunnableChecklist([], "schema-save-checklist");
    return;
  }
  setSaveStatus("", "");
  renderRunnableChecklist([], "schema-save-checklist");
}

function highlightSaveErrors() {
  if (!cy || !isSchemaMode()) return;
  const errors = state.packSave?.errors || [];
  const edgeIds = new Set(errors.map((item) => item.edge).filter(Boolean));
  const nodeIds = new Set(errors.map((item) => item.node).filter(Boolean));
  cy.nodes().forEach((el) => el.toggleClass("save-error", nodeIds.has(el.id())));
  cy.edges(".schema-edge").forEach((el) => el.toggleClass("save-error", edgeIds.has(el.id())));
  document.querySelectorAll("#schema-dispatch-rules .schema-dispatch-rule").forEach((row) => {
    const priority = row.dataset.priority;
    const when = row.dataset.when;
    const hit = errors.some(
      (item) =>
        (item.priority != null && String(item.priority) === priority) ||
        (item.when && item.when === when)
    );
    row.classList.toggle("is-save-error", hit);
  });
  document.querySelectorAll("#schema-outgoing-list .schema-outgoing-item").forEach((row) => {
    row.classList.toggle("is-save-error", edgeIds.has(row.dataset.edgeId));
  });
  document.querySelectorAll("#schema-edge-conditions .schema-edge-condition").forEach((row) => {
    const when = row.dataset.when;
    const hit = errors.some(
      (item) => item.when === when && (!item.edge || item.edge === selectedEdgeId)
    );
    row.classList.toggle("is-save-error", hit);
  });
}

function clearPackDraftKeepPositions(packId) {
  const draft = getPackDraft(packId);
  const next = emptyPackDraft();
  next.positions = draft.positions || {};
  setPackDraft(packId, next);
}

async function validatePackDraft() {
  if (!isSchemaMode() || !state.pack) {
    showError("Сначала откройте пак на вкладке «Схема».");
    return;
  }
  setSaveStatus("", "Проверка…");
  try {
    const res = await fetch("/api/pack/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(overlayPackBody()),
    });
    const data = await parseJsonResponse(res);
    state.packSave = {
      ok: Boolean(data.ok),
      errors: Array.isArray(data.errors) ? data.errors : data.error ? [{ message: data.error }] : [],
      warnings: Array.isArray(data.warnings) ? data.warnings : [],
      preview: data.preview || null,
    };
    updateSchemaSaveChrome();
    highlightSaveErrors();
    const firstEdge = state.packSave.errors.find((item) => item.edge);
    if (firstEdge?.edge && packEdgeById(firstEdge.edge)) selectSchemaEdge(firstEdge.edge);
    else if (!data.ok) {
      const firstNode = state.packSave.errors.find((item) => item.node);
      if (firstNode?.node && packNodeById(firstNode.node)) {
        selectedNodeId = firstNode.node;
        selectedEdgeId = null;
        selectedElementId = firstNode.node;
        highlightNode(firstNode.node, null);
        showSchemaInspector();
      }
    }
    if (data.ok) clearError();
  } catch (err) {
    state.packSave = { ok: false, errors: [{ message: err.message || String(err) }], warnings: [], preview: null };
    updateSchemaSaveChrome();
    showError(`Проверка пака: ${err.message || err}`);
  }
}

function closeSchemaModal(which) {
  const map = {
    init: "schema-init-modal",
    apply: "schema-apply-modal",
    "delete-pack": "schema-delete-pack-modal",
  };
  const id = map[which] || "";
  if (id) document.getElementById(id)?.classList.add("hidden");
}

function renderRunnableChecklist(items, targetId) {
  const list = document.getElementById(targetId || "schema-apply-checklist");
  if (!list) return;
  const rows = Array.isArray(items) ? items : [];
  list.innerHTML = "";
  list.classList.toggle("hidden", !rows.length);
  for (const item of rows) {
    const li = document.createElement("li");
    li.className = `schema-runnable-item ${item.ok ? "is-ok" : "is-bad"}`;
    const mark = document.createElement("span");
    mark.className = "schema-runnable-mark";
    mark.textContent = item.ok ? "✓" : "✗";
    const text = document.createElement("span");
    text.textContent = `${item.label || item.id}: ${item.detail || (item.ok ? "ok" : "нет")}`;
    li.append(mark, text);
    list.appendChild(li);
  }
  if ((targetId || "schema-apply-checklist") === "schema-save-checklist") {
    syncSaveStatusVisibility();
  }
}

function openApplyModal() {
  if (!state.packSave?.ok) return;
  const modal = document.getElementById("schema-apply-modal");
  const summary = document.getElementById("schema-apply-summary");
  const warn = document.getElementById("schema-apply-warn");
  const overwrite = document.getElementById("schema-apply-overwrite-orch");
  const preview = state.packSave.preview || {};
  if (summary) {
    summary.textContent = [
      `Пак ${state.packId}: ${preview.nodes ?? "?"} клеток, ${preview.edges ?? "?"} стрелок, ${preview.rules ?? "?"} правил.`,
      "Запишем YAML + collectors/predicates при необходимости + orchestrator md (если нет).",
    ].join(" ");
  }
  if (warn) {
    const protectedPack = PROTECTED_PACKS.has(state.packId);
    warn.textContent = protectedPack
      ? `Пак ${state.packId} живой. Меняйте только безобидное (label). Комментарии в изменённых YAML могут пропасть.`
      : "";
    warn.classList.toggle("hidden", !protectedPack);
  }
  if (overwrite) overwrite.checked = false;
  renderRunnableChecklist([], "schema-apply-checklist");
  modal?.classList.remove("hidden");
}

async function confirmApplyPack() {
  if (!state.packSave?.ok) return;
  const confirmBtn = document.getElementById("schema-apply-confirm");
  if (confirmBtn) confirmBtn.disabled = true;
  const overlay = overlayPackBody();
  const previous = overlayPackBodyFromPack(state.packBase);
  const overwriteOrch = document.getElementById("schema-apply-overwrite-orch")?.checked === true;
  try {
    const res = await fetch("/api/pack/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...overlay,
        confirm: true,
        overwrite_orchestrator: overwriteOrch,
      }),
    });
    const data = await parseJsonResponse(res);
    if (!data.ok) {
      state.packSave = {
        ok: false,
        errors: Array.isArray(data.errors) ? data.errors : [{ message: data.error || "apply failed" }],
        warnings: Array.isArray(data.warnings) ? data.warnings : [],
        preview: data.preview || null,
      };
      updateSchemaSaveChrome();
      highlightSaveErrors();
      showError(data.error || formatSaveError(state.packSave.errors[0]) || "Применить не удалось, диск не должен быть сломан.");
      return;
    }
    rememberAppliedOverlay(state.packId, {
      previous,
      last: overlayPackBodyFromPack(data.pack) || overlay,
    });
    closeSchemaModal("apply");
    clearPackDraftKeepPositions(state.packId);
    schemaUndoByPack[state.packId] = { past: [] };
    const checklist = Array.isArray(data.checklist) ? data.checklist : [];
    state.packSave = {
      ok: false,
      errors: [],
      warnings: data.warnings || [],
      preview: data.preview || null,
      checklist,
      dismissed: false,
      applyDone: true,
    };
    clearError();
    await refreshCatalogAndPack(data.pack);
  } catch (err) {
    showError(`Применить: ${err.message || err}`);
  } finally {
    if (confirmBtn) confirmBtn.disabled = false;
    updateSchemaSaveChrome();
  }
}

function overlayPackBodyFromPack(pack) {
  if (!pack) return null;
  return {
    id: pack.id,
    graph: pack.graph,
    dispatch: { rules: Array.isArray(pack.dispatch?.rules) ? pack.dispatch.rules : [] },
  };
}

async function rollbackLastApply() {
  const rec = appliedRecord(state.packId);
  if (!rec?.previous) return;
  if (!window.confirm(`Откатить ${state.packId} к последнему успешно применённому JSON?`)) return;
  try {
    const res = await fetch("/api/pack/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...rec.previous, confirm: true }),
    });
    const data = await parseJsonResponse(res);
    if (!data.ok) {
      showError(data.error || "Откат не прошёл, диск не меняли если проверка не зелёная.");
      return;
    }
    rememberAppliedOverlay(state.packId, {
      previous: overlayPackBodyFromPack(data.pack),
      last: rec.previous,
    });
    clearPackDraftKeepPositions(state.packId);
    schemaUndoByPack[state.packId] = { past: [] };
    setSaveStatus("is-ok", "Откат записан. Схема перечитывается.");
    await refreshCatalogAndPack(data.pack);
  } catch (err) {
    showError(`Откат: ${err.message || err}`);
  }
}

function openInitModal() {
  document.getElementById("schema-init-error")?.classList.add("hidden");
  const idEl = document.getElementById("schema-init-id");
  if (idEl && !idEl.value) idEl.value = "";
  document.getElementById("schema-init-modal")?.classList.remove("hidden");
  idEl?.focus();
}

async function confirmInitPack() {
  const id = String(document.getElementById("schema-init-id")?.value || "").trim();
  const template = String(document.getElementById("schema-init-template")?.value || "routing-state");
  const errEl = document.getElementById("schema-init-error");
  if (!/^[a-z][a-z0-9-]*$/.test(id)) {
    if (errEl) {
      errEl.textContent = "id: kebab-case, например authoring-ui-demo";
      errEl.classList.remove("hidden");
    }
    return;
  }
  if (!INIT_TEMPLATES.includes(template)) {
    if (errEl) {
      errEl.textContent = "шаблон: routing-state | full-dispatch | orchestrator-only";
      errEl.classList.remove("hidden");
    }
    return;
  }
  try {
    const res = await fetch("/api/pack/init", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, template }),
    });
    const data = await parseJsonResponse(res);
    if (!data.ok) {
      if (errEl) {
        errEl.textContent = data.error || "не удалось создать пак";
        errEl.classList.remove("hidden");
      }
      return;
    }
    closeSchemaModal("init");
    const warnings = Array.isArray(data.warnings) ? data.warnings : [];
    state.packSave = { ok: false, errors: [], warnings, preview: null };
    if (warnings.length) showError(warnings.join(" · "));
    else clearError();
    state.packId = id;
    saveSelection();
    await refreshCatalogAndPack(data.pack);
    const hasStatus = Boolean(data.pack?.status && Object.keys(data.pack.status).length);
    setSaveStatus(
      warnings.length ? "is-warn" : "is-ok",
      hasStatus
        ? `Пак ${id} из шаблона ${template}. status на месте, это не пустой холст.`
        : `Пак ${id} создан, но status пуст.`
    );
  } catch (err) {
    if (errEl) {
      errEl.textContent = err.message || String(err);
      errEl.classList.remove("hidden");
    }
  }
}

function forgetPackLocalState(packId) {
  const draftStore = loadDraftStore();
  if (draftStore.packs?.[packId]) {
    delete draftStore.packs[packId];
    localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draftStore));
  }
  const applied = loadAppliedStore();
  if (applied.packs?.[packId]) {
    delete applied.packs[packId];
    localStorage.setItem(SAVE_STORAGE_KEY, JSON.stringify(applied));
  }
  if (schemaUndoByPack[packId]) delete schemaUndoByPack[packId];
}

function openDeletePackModal() {
  const errEl = document.getElementById("schema-delete-pack-error");
  errEl?.classList.add("hidden");
  const id = state.packId;
  if (!id) return;
  const summary = document.getElementById("schema-delete-pack-summary");
  if (summary) {
    const builtin = PROTECTED_PACKS.has(id)
      ? ` Внимание: ${id} — встроенный пак репозитория.`
      : "";
    summary.textContent = `Удалит pipelines/${id}/ с диска и пересоберёт registry. Действие необратимо.${builtin}`;
  }
  const orch = document.getElementById("schema-delete-pack-orch");
  if (orch) orch.checked = true;
  document.getElementById("schema-delete-pack-modal")?.classList.remove("hidden");
}

async function confirmDeletePack() {
  const id = state.packId;
  const errEl = document.getElementById("schema-delete-pack-error");
  if (!id) return;
  const deleteOrch = document.getElementById("schema-delete-pack-orch")?.checked !== false;
  const confirmBtn = document.getElementById("schema-delete-pack-confirm");
  if (confirmBtn) confirmBtn.disabled = true;
  try {
    const res = await fetch("/api/pack/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, confirm: true, delete_orchestrator: deleteOrch }),
    });
    const data = await parseJsonResponse(res);
    if (!data.ok) {
      if (errEl) {
        errEl.textContent = data.error || "не удалось удалить пак";
        errEl.classList.remove("hidden");
      }
      return;
    }
    closeSchemaModal("delete-pack");
    forgetPackLocalState(id);
    clearError();
    const remaining = Array.isArray(data.remaining) ? data.remaining : [];
    const nextId = remaining[0] || "";
    state.packId = nextId;
    state.packBase = null;
    state.pack = null;
    state.packSave = { ok: false, errors: [], warnings: [], preview: null };
    saveSelection();
    await refreshCatalogAndPack(null);
    setSaveStatus(
      "is-ok",
      nextId ? `Пак ${id} удалён. Открыт ${nextId}.` : `Пак ${id} удалён. Паков больше нет.`
    );
  } catch (err) {
    if (errEl) {
      errEl.textContent = err.message || String(err);
      errEl.classList.remove("hidden");
    }
  } finally {
    if (confirmBtn) confirmBtn.disabled = false;
  }
}

async function refreshCatalogAndPack(pack) {
  try {
    const catalogRes = await fetch("/api/catalog");
    if (catalogRes.ok) {
      const catalog = await catalogRes.json();
      state.catalogPipelines = Array.isArray(catalog.pipelines) ? catalog.pipelines : state.catalogPipelines;
      state.catalogAgents = Array.isArray(catalog.agents) ? catalog.agents : state.catalogAgents;
      state.catalogPredicates =
        catalog.predicates && typeof catalog.predicates === "object"
          ? {
              core: Array.isArray(catalog.predicates.core) ? catalog.predicates.core : [],
              by_pipeline:
                catalog.predicates.by_pipeline && typeof catalog.predicates.by_pipeline === "object"
                  ? catalog.predicates.by_pipeline
                  : {},
            }
          : state.catalogPredicates;
      state.catalogRouting =
        catalog.routing_conditions && typeof catalog.routing_conditions === "object"
          ? catalog.routing_conditions
          : state.catalogRouting;
      fillPackTabs();
    }
  } catch {
    /* catalog refresh is best-effort */
  }
  setActivePackTab();
  if (pack && pack.id === state.packId) {
    state.packBase = pack;
    renderPackGraph(applyDraftToPack(pack, getPackDraft(state.packId)));
    return;
  }
  await loadPackGraph();
}

function bindSchemaDraftActions() {
  document.getElementById("schema-node-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
  });
  document.getElementById("schema-edge-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
  });

  document.getElementById("schema-delete-node")?.addEventListener("click", () => {
    if (selectedNodeId) deleteSchemaNode(selectedNodeId);
  });
  document.getElementById("schema-delete-edge")?.addEventListener("click", () => {
    if (selectedEdgeId) deleteSchemaEdge(selectedEdgeId);
  });
  document.getElementById("schema-connect-edge")?.addEventListener("click", () => {
    if (selectedNodeId) beginSchemaConnect(selectedNodeId);
  });
  document.getElementById("schema-undo")?.addEventListener("click", () => undoSchemaDraft());
  document.getElementById("schema-validate")?.addEventListener("click", () => validatePackDraft());
  document.getElementById("schema-save-status-dismiss")?.addEventListener("click", () => dismissSaveStatus());
  document.getElementById("schema-save-errors")?.addEventListener("click", (event) => {
    const btn = event.target.closest(".schema-save-error");
    if (!btn) return;
    if (btn.dataset.edgeId && packEdgeById(btn.dataset.edgeId)) {
      selectSchemaEdge(btn.dataset.edgeId);
      return;
    }
    if (btn.dataset.nodeId && packNodeById(btn.dataset.nodeId)) {
      selectedNodeId = btn.dataset.nodeId;
      selectedEdgeId = null;
      selectedElementId = btn.dataset.nodeId;
      highlightNode(btn.dataset.nodeId, null);
      showSchemaInspector();
    }
  });
  document.getElementById("schema-apply")?.addEventListener("click", () => openApplyModal());
  document.getElementById("schema-rollback")?.addEventListener("click", () => rollbackLastApply());
  document.getElementById("schema-init")?.addEventListener("click", () => openInitModal());
  document.getElementById("schema-delete-pack")?.addEventListener("click", () => openDeletePackModal());
  document.getElementById("schema-apply-confirm")?.addEventListener("click", () => confirmApplyPack());
  document.getElementById("schema-init-confirm")?.addEventListener("click", () => confirmInitPack());
  document.getElementById("schema-delete-pack-confirm")?.addEventListener("click", () => confirmDeletePack());
  document.getElementById("schema-init-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
    confirmInitPack();
  });
  document.querySelectorAll("[data-schema-close]").forEach((el) => {
    el.addEventListener("click", () => closeSchemaModal(el.getAttribute("data-schema-close")));
  });

  document.getElementById("schema-node-id")?.addEventListener("change", (event) => {
    if (schemaInspectorSyncing || !selectedNodeId) return;
    if (!renameSchemaNode(selectedNodeId, event.target.value)) {
      event.target.value = selectedNodeId;
    }
  });
  document.getElementById("schema-node-label")?.addEventListener("input", (event) => {
    if (schemaInspectorSyncing || !selectedNodeId) return;
    applyNodeFieldPatch(selectedNodeId, { label: event.target.value });
  });
  document.getElementById("schema-node-kind")?.addEventListener("change", (event) => {
    if (schemaInspectorSyncing || !selectedNodeId) return;
    if (!applyNodeKindChange(selectedNodeId, event.target.value)) {
      const node = packNodeById(selectedNodeId);
      event.target.value = nodeUiKind(node);
    }
  });
  document.getElementById("schema-node-subagent")?.addEventListener("change", (event) => {
    if (schemaInspectorSyncing || !selectedNodeId) return;
    applyNodeFieldPatch(selectedNodeId, { subagent: event.target.value || null });
  });

  document.getElementById("schema-cycle-persistent")?.addEventListener("change", () => {
    if (schemaInspectorSyncing || !selectedCycleNode()) return;
    commitSelectedCycle(readCycleFieldsFromForm(selectedCycleNode().cycle));
  });
  ["schema-cycle-assemble", "schema-cycle-param", "schema-cycle-folder", "schema-cycle-out", "schema-cycle-item-file"].forEach(
    (id) => {
      document.getElementById(id)?.addEventListener("input", () => {
        if (schemaInspectorSyncing || !selectedCycleNode()) return;
        commitSelectedCycle(readCycleFieldsFromForm(selectedCycleNode().cycle));
      });
    }
  );
  document.getElementById("schema-cycle-add-call")?.addEventListener("click", () => {
    if (schemaInspectorSyncing) return;
    addSchemaCycleCall();
  });
  document.getElementById("schema-cycle-fill-catalog")?.addEventListener("click", () => {
    if (schemaInspectorSyncing) return;
    fillSchemaCycleFromCatalog();
  });
  document.getElementById("schema-cycle-queue-mode")?.addEventListener("change", (event) => {
    if (schemaInspectorSyncing) return;
    const radio = event.target.closest('input[name="schema-cycle-queue"]');
    if (!radio) return;
    setCycleQueueMode(radio.value);
  });
  document.getElementById("schema-cycle-calls")?.addEventListener("click", (event) => {
    if (schemaInspectorSyncing) return;
    const button = event.target.closest("button[data-action]");
    const row = event.target.closest(".schema-cycle-call");
    if (!button || !row) return;
    const index = Number(row.dataset.index);
    if (Number.isNaN(index)) return;
    if (button.dataset.action === "up") moveSchemaCycleCall(index, -1);
    else if (button.dataset.action === "down") moveSchemaCycleCall(index, 1);
    else if (button.dataset.action === "remove") removeSchemaCycleCall(index);
  });
  document.getElementById("schema-cycle-calls")?.addEventListener("change", (event) => {
    if (schemaInspectorSyncing) return;
    handleCycleCallFieldEdit(event);
  });
  document.getElementById("schema-cycle-calls")?.addEventListener("input", (event) => {
    if (schemaInspectorSyncing) return;
    const el = event.target.closest?.("[data-field]");
    if (!el || el.dataset.field === "agent") return;
    handleCycleCallFieldEdit(event);
  });
  document.getElementById("schema-cycle-calls")?.addEventListener("keydown", (event) => {
    if (!event.target.closest("[contenteditable]")) return;
    if (event.key === "Enter") {
      event.preventDefault();
      event.target.blur();
    }
  });
  document.getElementById("schema-cycle-calls")?.addEventListener("paste", (event) => {
    const editor = event.target.closest("[contenteditable]");
    if (!editor) return;
    event.preventDefault();
    const text = (event.clipboardData || window.clipboardData).getData("text/plain").replace(/\s+/g, " ");
    document.execCommand("insertText", false, text);
  });

  document.getElementById("schema-edge-from")?.addEventListener("change", (event) => {
    if (schemaInspectorSyncing || !selectedEdgeId) return;
    applyEdgeFieldPatch(selectedEdgeId, { from: event.target.value }, { rebuild: true });
  });
  document.getElementById("schema-edge-to")?.addEventListener("change", (event) => {
    if (schemaInspectorSyncing || !selectedEdgeId) return;
    const to = event.target.value;
    const edge = mergedDraftEdge(selectedEdgeId) || packEdgeById(selectedEdgeId);
    const fromNode = packNodeById(edge?.from);
    const patch = { to };
    if (to === ROUTING_STEP && fromNode?.kind !== "orchestrator") {
      Object.assign(patch, afterStepEdgePatch(edge?.label));
    } else if (edgeIsAfterStep(edge)) {
      patch.after_step = false;
    }
    applyEdgeFieldPatch(selectedEdgeId, patch, { rebuild: true });
  });
  document.getElementById("schema-edge-routing-mode")?.addEventListener("change", (event) => {
    if (schemaInspectorSyncing || !selectedEdgeId) return;
    const radio = event.target.closest('input[name="schema-edge-routing"]');
    if (!radio) return;
    applySelectedEdgeRoutingMode(radio.value);
  });
  document.getElementById("schema-edge-kind")?.addEventListener("change", (event) => {
    if (schemaInspectorSyncing || !selectedEdgeId) return;
    markSchemaEdgeKindNotes(event.target.value);
    applyEdgeFieldPatch(selectedEdgeId, { kind: event.target.value });
  });
  document.getElementById("schema-edge-label")?.addEventListener("input", (event) => {
    if (schemaInspectorSyncing || !selectedEdgeId) return;
    applyEdgeFieldPatch(selectedEdgeId, { label: event.target.value });
  });
  const commitAddedEdgeCondition = () => {
    if (schemaInspectorSyncing || !selectedEdgeId) return;
    const addEl = document.getElementById("schema-edge-condition-add");
    addSelectedEdgeCondition(addEl?.value || "");
  };
  document.getElementById("schema-edge-condition-add-btn")?.addEventListener("click", () => {
    commitAddedEdgeCondition();
  });
  document.getElementById("schema-edge-condition-add")?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    commitAddedEdgeCondition();
  });
  document.getElementById("schema-edge-condition-add")?.addEventListener("change", () => {
    commitAddedEdgeCondition();
  });
  document.getElementById("schema-edge-conditions")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-when]");
    if (!button || schemaInspectorSyncing || !selectedEdgeId) return;
    removeSelectedEdgeCondition(button.dataset.removeWhen);
  });
  document.getElementById("schema-outgoing-list")?.addEventListener("click", (event) => {
    const item = event.target.closest(".schema-outgoing-item");
    if (!item?.dataset.edgeId) return;
    selectSchemaEdge(item.dataset.edgeId);
  });

  document.getElementById("schema-dispatch-add")?.addEventListener("click", () => {
    if (!isSchemaMode()) return;
    addDispatchRule();
  });
  document.getElementById("schema-dispatch")?.addEventListener("change", (event) => {
    if (!isSchemaMode() || schemaInspectorSyncing) return;
    const row = event.target.closest(".schema-dispatch-rule");
    if (!row) return;
    const index = Number(row.dataset.index);
    if (Number.isNaN(index)) return;
    const rule = liveDispatchRules()[index];
    if (!rule) return;
    const field = event.target.name;
    if (field === "priority") {
      patchDispatchRule(index, { priority: Number(event.target.value) });
      return;
    }
    if (field === "when") {
      patchDispatchRule(index, { when: event.target.value });
      return;
    }
    if (field === "next") {
      patchDispatchRule(
        index,
        ruleFromDispatchFields(rule.priority, rule.when, event.target.value),
        true
      );
    }
  });
  document.getElementById("schema-dispatch")?.addEventListener("click", (event) => {
    if (!isSchemaMode()) return;
    const button = event.target.closest("button[data-action='remove']");
    if (!button) return;
    const row = button.closest(".schema-dispatch-rule");
    if (!row) return;
    const index = Number(row.dataset.index);
    if (Number.isNaN(index)) return;
    removeDispatchRule(index);
  });

  document.addEventListener("keydown", (event) => {
    if (!isSchemaMode()) return;
    const inField = event.target?.closest?.("input, textarea, select, [contenteditable]");
    if ((event.key === "z" || event.key === "Z") && (event.metaKey || event.ctrlKey) && !event.shiftKey) {
      if (inField) return;
      event.preventDefault();
      undoSchemaDraft();
      return;
    }
    if (event.key === "Escape") {
      if (schemaConnectFrom) {
        event.preventDefault();
        cancelSchemaConnect();
      }
      return;
    }
    if (event.key !== "Delete" && event.key !== "Backspace") return;
    if (inField) return;
    if (selectedEdgeId) {
      event.preventDefault();
      deleteSchemaEdge(selectedEdgeId);
      return;
    }
    if (selectedNodeId) {
      event.preventDefault();
      deleteSchemaNode(selectedNodeId);
    }
  });
}

function fillPackTabs() {
  const nav = document.getElementById("pack-tabs");
  if (!nav) return;
  nav.innerHTML = "";
  const pipelines = state.catalogPipelines.length ? state.catalogPipelines : [];
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
      cancelSchemaConnect();
      state.packId = item.id;
      state.packSave = { ok: false, errors: [], warnings: [], preview: null };
      setActivePackTab();
      saveSelection();
      loadPackGraph();
    });
    nav.appendChild(btn);
  }
  const known = new Set(pipelines.map((item) => item.id));
  if (!known.has(state.packId)) {
    state.packId = pipelines[0]?.id || "";
  }
  setActivePackTab();
}

function fillPipelineTabs() {
  const nav = document.getElementById("pipeline-tabs");
  if (!nav) return;
  nav.innerHTML = "";
  const pipelines = state.runPipelines.length
    ? state.runPipelines
    : state.catalogPipelines.length
      ? state.catalogPipelines
      : [];
  state.runPipelines = pipelines;
  for (const item of pipelines) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "tab";
    btn.dataset.pipeline = item.id;
    btn.textContent = item.id;
    btn.title = item.label || item.id;
    btn.addEventListener("click", () => {
      if (state.pipeline === item.id) return;
      state.pipeline = item.id;
      setActiveTab(state.pipeline);
      const preferred = fillSlugSelect(
        { slugs: state.allSlugs },
        { default_slug: "" },
        { slug: state.slug }
      );
      state.slug = preferred;
      updateRestartActions(selectedNodeId);
      saveSelection();
      if (!isSchemaMode()) connectStream();
    });
    nav.appendChild(btn);
  }
  const known = new Set(pipelines.map((item) => item.id));
  if (!known.has(state.pipeline)) {
    state.pipeline = pipelines[0]?.id || "";
  }
  setActiveTab(state.pipeline);
}

function setActivePackTab() {
  document.querySelectorAll("#pack-tabs .tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.pack === state.packId);
  });
  updateSchemaSaveChrome();
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
  if (heading) heading.textContent = schema ? "Инспектор" : "Выбранный шаг";
  if (hint) {
    hint.textContent = schema
      ? "Клетка: исходящие стрелки. Стрелка: условие перехода. Shift+клик — ребро. YAML не пишется."
      : "Клик по узлу на графе. Жёлтая/оранжевая рамка — есть замечания.";
  }
  if (schema) {
    document.getElementById("legend")?.classList.remove("hidden");
    document.getElementById("graph-scroll")?.classList.remove("hidden-for-timing");
    document.getElementById("timing-panel")?.classList.add("hidden");
    updateSchemaUndoChrome();
  } else {
    cancelSchemaConnect();
    setGraphViewTabs();
  }
  if (cy) cy.autoungrabify(false);
}

function setScreenMode(mode) {
  const next = mode === "schema" ? "schema" : "run";
  const changed = state.screenMode !== next;
  state.screenMode = next;
  saveSelection();
  if (changed && next === "run") {
    captureSchemaPositions();
    selectedEdgeId = null;
    cancelSchemaConnect();
  }
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
  const hasTopology = nodes.length > 0;

  empty.classList.toggle("hidden", hasTopology);
  document.getElementById("cy").style.visibility = hasTopology ? "visible" : "hidden";
  const emptyRun = empty?.querySelector(".empty-run");
  if (emptyRun && !hasTopology) {
    emptyRun.innerHTML =
      `<p>Нет топологии для пайплайна <code>${escapeHtml(state.pipeline)}</code>.</p>` +
      `<p class="hint">Проверьте, что пак скомпилирован: <code>pipeline_compile.py --apply</code></p>`;
  }

  const runEl = document.getElementById("run-id");
  if (data.target_only || noSlug) {
    runEl.textContent = "целевой · без задачи";
  } else if (data.pipeline === "calibration") {
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

  if (!hasTopology) {
    document.getElementById("timeline").innerHTML = "";
    document.getElementById("stats").textContent = "—";
    clearNodePanel();
    renderTimingsPanel(null);

    if (cy) cy.elements().remove();
    return;
  }

  if (noSlug && state.graphView !== "target") {
    state.graphView = "target";
  }

  setGraphViewTabs();
  updateGraphViewHint(data);

  if (state.graphView === "timing") {
    renderTimingsPanel(data.timings, data.timeline);
    renderDispatchPanel(data);
    renderSessionOutcomeBanner(data);
    renderDivergenceBanner(data.divergence?.summary);
    renderValidationBanner(data.validation);
    renderValidationPanel(data.validation);
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
  renderValidationPanel(data.validation);
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
  saveSelection();
  setConnection("", state.slug ? "подключение…" : "целевой граф…");

  const source = new EventSource(streamUrl());
  state.source = source;

  source.onopen = () => {
    if (state.source !== source || isSchemaMode()) return;
    setConnection("live", state.slug ? "live" : "live · целевой");
  };

  source.onmessage = (event) => {
    if (state.source !== source || isSchemaMode()) return;
    try {
      const data = JSON.parse(event.data);
      renderGraph(data);
      clearError();
      setConnection(
        "live",
        state.slug ? `live · ${data.updated_at || ""}` : "live · целевой"
      );
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
      if (state.source) return;
      connectStream();
    }, 2000);
  };
}

function slugsForCurrentPipeline(allSlugs) {
  const pipe = state.pipeline || "";
  if (!pipe) return [];
  return (allSlugs || []).filter((item) => {
    const pipes = Array.isArray(item.pipelines) ? item.pipelines : null;
    return Boolean(pipes && pipes.includes(pipe));
  });
}

function fillSlugSelect(payload, config, saved) {
  const select = document.getElementById("slug-select");
  select.innerHTML = "";

  const all = Array.isArray(payload?.slugs) ? payload.slugs : state.allSlugs;
  if (Array.isArray(payload?.slugs)) {
    state.allSlugs = payload.slugs;
  }
  const filtered = slugsForCurrentPipeline(all);

  if (!filtered.length) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = `— нет задач для ${state.pipeline} —`;
    select.appendChild(opt);
    select.value = "";
    return "";
  }

  const withLogs = filtered.filter((s) => s.has_agent_logs);
  const withoutLogs = filtered.filter((s) => !s.has_agent_logs);

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

  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "— без задачи (целевой граф) —";
  select.appendChild(blank);

  addGroup("С телеметрией (agent-logs)", withLogs);
  addGroup("Только Feature-writing", withoutLogs);

  const slugSet = new Set(filtered.map((s) => s.slug));
  let preferred = saved?.slug || "";
  if (preferred && !slugSet.has(preferred)) {
    preferred = "";
  }
  if (!preferred && config?.default_slug && slugSet.has(config.default_slug)) {
    preferred = config.default_slug;
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

    state.pipeline = saved.pipeline || config.default_pipeline || "";
    state.graphView = ["actual", "timing"].includes(saved.graphView) ? saved.graphView : "target";
    state.staleCollapsed = saved.staleCollapsed !== false;
    state.screenMode = saved.screenMode === "schema" ? "schema" : "run";
    state.packId = typeof saved.packId === "string" && saved.packId ? saved.packId : "";
    state.runPipelines = Array.isArray(config.pipelines) ? config.pipelines : [];
    state.catalogPipelines = Array.isArray(catalog.pipelines) ? catalog.pipelines : [];
    state.catalogAgents = Array.isArray(catalog.agents) ? catalog.agents : [];
    state.catalogSkills = Array.isArray(catalog.skills) ? catalog.skills : [];
    state.catalogPredicates =
      catalog.predicates && typeof catalog.predicates === "object"
        ? {
            core: Array.isArray(catalog.predicates.core) ? catalog.predicates.core : [],
            by_pipeline:
              catalog.predicates.by_pipeline && typeof catalog.predicates.by_pipeline === "object"
                ? catalog.predicates.by_pipeline
                : {},
          }
        : { core: [], by_pipeline: {} };
    state.catalogRouting =
      catalog.routing_conditions && typeof catalog.routing_conditions === "object"
        ? catalog.routing_conditions
        : {};
    state.agentsByCli =
      catalog.agents_by_cli && typeof catalog.agents_by_cli === "object" ? catalog.agents_by_cli : {};
    state.writeFeatureCycle =
      catalog.write_feature_cycle && typeof catalog.write_feature_cycle === "object"
        ? catalog.write_feature_cycle
        : { profile: "", calls: [] };
    fillPackTabs();
    fillPipelineTabs();
    bindSchemaPalette();
    bindSchemaDraftActions();
    setActiveTab(state.pipeline);
    setGraphViewTabs();
    applyScreenModeChrome();
    state.slug = fillSlugSelect(payload, config, saved);

    if (apiVersion < SCHEMA_API_VERSION && isSchemaMode()) {
      showError(staleViewerMessage("вкладка «Схема» (GET /api/pack, validate/apply)"));
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
