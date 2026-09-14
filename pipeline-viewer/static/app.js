/* global cytoscape */

const STORAGE_KEY = "pipeline-viewer-selection";
const DISMISS_STORAGE_KEY = "pipeline-viewer-dismissed";

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
  source: null,
  graph: null,
  dismissedNotices: loadDismissedNotices(),
};

let cy = null;
let nodeDetails = {};
let graphInteractionsBound = false;
let selectedNodeId = null;
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

  el.className = ["notice-banner", baseClass, statusClass].filter(Boolean).join(" ");
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
          "curve-style": "taxi",
          "taxi-direction": "vertical",
          "taxi-turn": 28,
          "taxi-turn-min-distance": 16,
          label: "data(label)",
          "font-size": "8px",
          color: "#94a3b8",
          "text-rotation": "autorotate",
        },
      },
      {
        selector: "edge[traversed = 'true']",
        style: {
          width: 3,
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
    const ts = row.ts ? row.ts.slice(0, 19).replace("T", " ") : "—";
    const staleTag = displayState === "stale" ? " · устарел" : "";
    li.textContent = `#${row.seq} · pass ${row.pass} · ${ts}${sub}${staleTag}`;
    list.appendChild(li);
  }
  box.appendChild(list);
}

function clearNodePanel() {
  document.getElementById("step-detail").textContent = "Кликните узел на графе.";
  document.getElementById("step-visits").classList.add("hidden");
  document.getElementById("step-divergence").classList.add("hidden");
  document.getElementById("restart-actions").classList.add("hidden");
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

function timingStepColor(stepId) {
  return TIMING_STEP_COLORS[stepId] || "#94a3b8";
}

function renderTimingsPanel(timings) {
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
  const range =
    timings.started_at && timings.ended_at
      ? `${timings.started_at} → ${timings.ended_at}`
      : "—";
  const src = timings.primary_source || "—";
  summaryEl.innerHTML =
    `<p><strong>Σ ${timings.total_label || "—"}</strong> активной работы subagent` +
    (timings.wall_sec ? ` · на timeline ${Math.round(timings.wall_sec / 60)} мин` : "") +
    `<br><span class="timing-range">${range}</span>` +
    `<br><span class="timing-range">источник: ${src}</span></p>`;

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
      .map((note) => `<li>${note}</li>`)
      .join("");
  }

  const passes = timings.passes || [];
  if (passesEl && passesWrap) {
    if (!passes.length) {
      passesWrap.classList.add("hidden");
      passesEl.innerHTML = "";
    } else {
      passesWrap.classList.remove("hidden");
      passesEl.innerHTML = passes
        .map(
          (row) =>
            `<li><code>${row.step}</code> · ${row.seconds} с · ${row.source}` +
            (row.start_ts ? ` · ${row.start_ts}` : "") +
            (row.note ? ` — ${row.note}` : "") +
            `</li>`
        )
        .join("");
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
    el.textContent = "Источник: agent-logs/subagent-passes.jsonl";
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
  for (const node of data.nodes || []) {
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
      },
      position: pos,
    });
  }
  for (const edge of data.edges || []) {
    elements.push({
      group: "edges",
      data: {
        id: edge.id,
        source: edge.from,
        target: edge.to,
        label: edge.label || "",
        color: edge.color,
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
  const stepY = 78;
  let prevNodeId = null;

  sequence.forEach((item, index) => {
    let nodeId;
    let edgeMeta = { stale: false, diverged: false };

    if (item.type === "bundle") {
      const count = item.rows.length;
      const fromSeq = item.rows[0]?.seq;
      const toSeq = item.rows[item.rows.length - 1]?.seq;
      nodeId = "stale-collapsed";
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
        position: { x: centerX, y: startY + index * stepY },
      });
      edgeMeta.stale = true;
    } else {
      const row = item.row;
      nodeId = `visit-${row.seq}`;
      const step = row.step || "?";
      const sub = row.subagent ? `\n${row.subagent}` : "";
      const ts = row.ts ? row.ts.slice(11, 19) : "";
      const pass = row.pass ? ` · pass ${row.pass}` : "";
    const displayState = rowDisplayState(row);
    const staleLine =
      displayState === "stale"
        ? row.result === "fail" || row.result === "retry"
          ? `\n⛔ ${row.result} · устарел`
          : "\n⛔ устарел"
        : "";
      const label = `#${row.seq} ${step}${pass}\n${ts}${sub}${staleLine}`;
      const color = RESULT_COLORS[displayState] || RESULT_COLORS.ok;
      edgeMeta.diverged = (row.divergence_kinds || []).includes("order_violation");
      edgeMeta.stale = displayState === "stale";

      elements.push({
        group: "nodes",
        data: {
          id: nodeId,
          stepId: step,
          seq: row.seq,
          label,
          color,
          state: displayState,
          kind: "visit",
        },
        position: { x: centerX, y: startY + index * stepY },
      });
    }

    if (prevNodeId) {
      let edgeColor = "#64748b";
      if (edgeMeta.stale) edgeColor = "#44403c";
      else if (edgeMeta.diverged) edgeColor = "#f97316";
      elements.push({
        group: "edges",
        data: {
          id: `e-${prevNodeId}-${nodeId}`,
          source: prevNodeId,
          target: nodeId,
          label: edgeMeta.diverged && !edgeMeta.stale ? "≠ schema" : "",
          color: edgeColor,
          stale: edgeMeta.stale ? "true" : "false",
          traversed: "true",
        },
      });
    }
    prevNodeId = nodeId;
  });
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
    const ts = row.ts ? row.ts.slice(0, 19).replace("T", " ") : "—";
    const pass = row.pass ? `pass ${row.pass}` : "";
    const staleTag =
      displayState === "stale"
        ? row.result === "fail" || row.result === "retry"
          ? ` · ${row.result} · устарел`
          : " · устарел"
        : "";
    li.textContent = `#${row.seq || "?"} · ${pass} · ${row.step}${sub} · ${ts}${staleTag}`;
    li.addEventListener("click", () => {
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
  if (!nodeId && !timelineSeq) return;

  if (state.graphView === "actual") {
    if (nodeId === "stale-collapsed") {
      const el = graph.getElementById("stale-collapsed");
      if (el.length) el.addClass("selected");
      return;
    }
    if (timelineSeq) {
      const el = graph.getElementById(`visit-${timelineSeq}`);
      if (el.length) el.addClass("selected");
    } else if (nodeId) {
      graph.nodes(`[stepId = "${nodeId}"]`).addClass("selected");
    }
    return;
  }

  if (nodeId) {
    const el = graph.getElementById(nodeId);
    if (el.length) el.addClass("selected");
  }
}

function bindGraphInteractions(graph) {
  if (graphInteractionsBound) return;
  graphInteractionsBound = true;

  graph.on("tap", "node", (evt) => {
    const node = evt.target;
    if (node.data("kind") === "stale-bundle") {
      setStaleCollapsed(false);
      hideTooltip();
      return;
    }
    const stepId = node.data("stepId") || node.id();
    selectedNodeId = stepId;
    selectedTimelineSeq = node.data("seq") || null;
    highlightNode(selectedNodeId, selectedTimelineSeq);
    showNodePanel(selectedNodeId);
    highlightTimelineRow(selectedNodeId, selectedTimelineSeq);
    hideTooltip();
  });

  function tooltipForNode(nodeId, cyNode) {
    const stepId = cyNode?.data("stepId") || nodeId;
    const detail = nodeDetails[stepId];
    const node = (state.graph?.nodes || []).find((n) => n.id === stepId);
    let text = detail?.tooltip || detail?.hint || stepId;
    if (cyNode?.data("kind") === "stale-bundle") {
      text = `Отменённые шаги · ${cyNode.data("staleCount")} проходов · клик — развернуть`;
    } else if (cyNode?.data("kind") === "visit") {
      text = `#${cyNode.data("seq")} ${stepId} · ${text}`;
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

  graph.on("tap", (evt) => {
    if (evt.target === graph) {
      selectedNodeId = null;
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
    })
  );
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
  el.className = `badge conn ${status}`;
}

function setActiveTab(pipeline) {
  document.querySelectorAll("#pipeline-tabs .tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.pipeline === pipeline);
  });
  updateInfraPanel();
}

function renderGraph(data) {
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
    renderTimingsPanel(data.timings);
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
  if (!state.slug) {
    renderGraph({ slug: "", nodes: [], edges: [], history: [] });
    setConnection("idle", "нет задачи");
    return;
  }
  saveSelection();
  setConnection("", "подключение…");

  const source = new EventSource(streamUrl());
  state.source = source;

  source.onopen = () => setConnection("live", "live");

  source.onmessage = (event) => {
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
    setConnection("reconnecting", "переподключение…");
    disconnectStream();
    setTimeout(connectStream, 2000);
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
    const [configRes, slugsRes] = await Promise.all([
      fetch("/api/config"),
      fetch("/api/slugs"),
    ]);

    if (!configRes.ok || !slugsRes.ok) {
      const st = !configRes.ok ? configRes.status : slugsRes.status;
      throw new Error(await apiUnavailableMessage(st));
    }

    const config = await configRes.json();
    const payload = await slugsRes.json();

    state.pipeline = saved.pipeline || config.default_pipeline || "spec";
    state.graphView = ["actual", "timing"].includes(saved.graphView) ? saved.graphView : "target";
    state.staleCollapsed = saved.staleCollapsed !== false;
    setActiveTab(state.pipeline);
    setGraphViewTabs();
    state.slug = fillSlugSelect(payload, config, saved);

    document.getElementById("stale-toggle")?.addEventListener("click", () => {
      setStaleCollapsed(!state.staleCollapsed);
    });

    document.querySelectorAll("#graph-view-tabs .tab").forEach((btn) => {
      btn.addEventListener("click", () => {
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

    document.getElementById("restart-btn").addEventListener("click", openRestartModal);
    document.getElementById("restart-confirm-btn").addEventListener("click", confirmRestart);
    document.querySelectorAll("#restart-modal [data-close]").forEach((el) => {
      el.addEventListener("click", closeRestartModal);
    });

    document.getElementById("slug-select").addEventListener("change", (e) => {
      state.slug = e.target.value;
      connectStream();
    });

    document.querySelectorAll("#pipeline-tabs .tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.pipeline = btn.dataset.pipeline;
        setActiveTab(state.pipeline);
        updateRestartActions(selectedNodeId);
        connectStream();
      });
    });

    connectStream();
  } catch (err) {
    console.error(err);
    showError(err.message || String(err));
    setConnection("reconnecting", "ошибка загрузки");
    document.getElementById("slug-select").innerHTML =
      '<option value="">— ошибка загрузки —</option>';
  }
}

init();
