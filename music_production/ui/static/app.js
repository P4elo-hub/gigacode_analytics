"use strict";

const GATE_LABELS = {
  PACKAGE_APPROVAL: "Утверждение пакета",
  BASE_SELECTION: "Выбор базы",
  REVISION_ESCALATION: "Эскалация правки",
  FINAL_APPROVAL: "Финальное утверждение",
};

const ACTION_LABELS = {
  APPROVE_PACKAGE: "Утвердить пакет",
  CHANGE_LYRICS: "Изменить текст",
  CHANGE_PRODUCTION: "Изменить звучание",
  STOP: "Остановить",
  SELECT_AS_BASE: "Выбрать базой",
  REGENERATE_BATCH: "Сгенерировать заново",
  COMBINE_DIRECTION: "Совместить направления",
  ACCEPT_REVISION: "Принять правку",
  RETRY_REVISION: "Повторить правку",
  ROLLBACK: "Откатить к родителю",
  APPROVE_FINAL: "Утвердить финал",
  REQUEST_REVISION: "Запросить правку",
};

let csrfToken = "";
let currentView = null;
let posting = false;
const players = { left: null, right: null };

function el(tag, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  return node;
}

function text(tag, value, className) {
  const node = el(tag, className);
  node.textContent = value == null ? "" : String(value);
  return node;
}

function field(label, value) {
  const row = el("p");
  row.append(text("strong", label + ": "));
  row.append(document.createTextNode(value == null || value === "" ? "—" : String(value)));
  return row;
}

async function readJson(response) {
  const payload = await response.json();
  if (!response.ok) {
    const error = new Error(payload.error || "request_failed");
    error.payload = payload;
    throw error;
  }
  return payload;
}

function showError(message) {
  document.getElementById("error").textContent = message || "";
}

async function boot() {
  const session = await readJson(await fetch("/api/session"));
  csrfToken = session.csrf_token;
  const listing = await readJson(await fetch("/api/tracks"));
  const select = document.getElementById("track-select");
  const empty = document.getElementById("empty-state");
  select.replaceChildren();
  if (!listing.tracks.length) {
    empty.hidden = false;
    document.getElementById("screen").hidden = true;
    return;
  }
  empty.hidden = true;
  listing.tracks.forEach(function (track) {
    const option = el("option");
    option.value = track.track_id;
    option.textContent = track.track_id + " · " + track.state;
    select.append(option);
  });
  select.addEventListener("change", function () {
    loadTrack(select.value);
  });
  await loadTrack(select.value);
}

async function loadTrack(trackId) {
  showError("");
  const view = await readJson(await fetch("/api/tracks/" + encodeURIComponent(trackId)));
  render(view);
}

function audioNode(version) {
  const audio = document.createElement("audio");
  audio.controls = true;
  audio.preload = "none";
  if (!version || !version.audio_available) {
    audio.disabled = true;
    return audio;
  }
  audio.src = "/api/tracks/" + encodeURIComponent(currentView.track_id) +
    "/audio/" + encodeURIComponent(version.version_id);
  return audio;
}

function versionById(versionId) {
  return (currentView.versions || []).find(function (item) {
    return item.version_id === versionId;
  }) || null;
}

function render(view) {
  currentView = view;
  const screen = document.getElementById("screen");
  screen.hidden = false;
  screen.replaceChildren();
  screen.append(summary(view));
  screen.append(abSection(view));
  screen.append(lineage(view));
  screen.append(jobs(view));
  screen.append(defects(view));
  screen.append(promptBlock(view));
  screen.append(comparison(view));
  screen.append(qc(view));
  screen.append(history(view));
  screen.append(knowledge(view));
  screen.append(decisionForm(view));
}

function summary(view) {
  const panel = el("section", "panel");
  panel.append(text("h2", "Состояние"));
  panel.append(field("Трек", view.track_id));
  panel.append(field("State", view.state));
  panel.append(field("Шаг", view.step));
  panel.append(field("Гейт", view.gate ? (GATE_LABELS[view.gate] || view.gate) : "нет"));
  panel.append(field("Исход движка", view.outcome));
  const budget = view.budget || {};
  const brief = budget.brief || {};
  panel.append(field("Остаток правок", budget.revision_budget_remaining));
  panel.append(field("Итерация", budget.revision_iteration));
  panel.append(field("Лимит batch", brief.max_batch));
  panel.append(field("Лимит попыток дефекта", brief.max_defect_fix_attempts));
  panel.append(field("Лимит итераций", brief.max_iterations));
  panel.append(field("Ожидание API, с", brief.max_api_wait_seconds));
  panel.append(field("Лимит стоимости", brief.max_cost));
  return panel;
}

function abSection(view) {
  const panel = el("section", "panel");
  panel.append(text("h2", "A/B"));
  const wrap = el("div", "ab");
  const left = card("A", versionById(view.ab && view.ab.left_version_id), "left");
  const right = card("B", versionById(view.ab && view.ab.right_version_id), "right");
  wrap.append(left, right);
  panel.append(wrap);
  const controls = el("div");
  const play = el("button");
  play.type = "button";
  play.textContent = "Play / Pause";
  const unavailable = !players.left || players.left.disabled || !players.right || players.right.disabled;
  play.disabled = unavailable || posting;
  play.addEventListener("click", togglePlay);
  controls.append(play);
  const drift = text("p", "Drift: —", "hint");
  drift.id = "drift";
  controls.append(drift);
  const seek = el("button");
  seek.type = "button";
  const defect = (view.defects || [])[0];
  seek.textContent = "К началу дефекта";
  seek.disabled = !defect || unavailable || posting;
  seek.addEventListener("click", function () {
    if (!defect) return;
    [players.left, players.right].forEach(function (audio) {
      if (audio && !audio.disabled) audio.currentTime = Number(defect.start_seconds) || 0;
    });
  });
  controls.append(seek);
  panel.append(controls);
  if ((view.versions || []).some(function (item) { return item.audio_block_reason === "mock_uri"; })) {
    panel.append(text("p", view.mock_audio_message, "mock-note"));
  }
  return panel;
}

function card(title, version, slot) {
  const box = el("article", "ab-card");
  box.append(text("h3", title));
  if (!version) {
    box.append(text("p", "Версия не выбрана"));
    players[slot] = null;
    return box;
  }
  box.append(field("version_id", version.version_id));
  box.append(field("Родитель", version.parent_version_id));
  box.append(field("audio_uri", version.audio_uri));
  box.append(field("audio_available", version.audio_available ? "да" : "нет"));
  const audio = audioNode(version);
  players[slot] = audio;
  audio.addEventListener("timeupdate", updateDrift);
  box.append(audio);
  if (version.audio_block_reason === "mock_uri") {
    box.append(text("p", currentView.mock_audio_message, "mock-note"));
  }
  return box;
}

function togglePlay() {
  const pair = [players.left, players.right].filter(Boolean);
  if (!pair.length || pair.some(function (audio) { return audio.disabled; })) return;
  if (pair.some(function (audio) { return !audio.paused; })) {
    pair.forEach(function (audio) { audio.pause(); });
    return;
  }
  const start = Math.min.apply(null, pair.map(function (audio) { return audio.currentTime || 0; }));
  pair.forEach(function (audio) { audio.currentTime = start; });
  pair.forEach(function (audio) { audio.play(); });
}

function updateDrift() {
  const node = document.getElementById("drift");
  if (!node || !players.left || !players.right) return;
  if (players.left.disabled || players.right.disabled) {
    node.textContent = "Drift: недоступно";
    return;
  }
  const drift = Math.abs((players.left.currentTime || 0) - (players.right.currentTime || 0));
  node.textContent = "Drift: " + drift.toFixed(3) + " с";
}

function lineage(view) {
  const panel = el("section", "panel");
  panel.append(text("h2", "Версии и lineage"));
  const list = el("ol", "lineage");
  const versions = view.versions || [];
  versions.forEach(function (version) {
    list.append(text(
      "li",
      version.version_id + " ← " + (version.parent_version_id || "корень") + " · " + version.operation
    ));
  });
  if (!versions.length) list.append(text("li", "Версий нет"));
  panel.append(list);
  if ((view.lineage || []).length > 1) {
    panel.append(field("Текущая цепочка", view.lineage.join(" ← ")));
  }
  return panel;
}

function jobs(view) {
  const panel = el("section", "panel");
  panel.append(text("h2", "Jobs"));
  const list = el("ul");
  (view.jobs || []).forEach(function (job) {
    list.append(text("li", (job.kind || "job") + " · " + (job.outcome || "—") + " · " + (job.job_id || "")));
  });
  if (!(view.jobs || []).length) list.append(text("li", "Заданий нет"));
  panel.append(list);
  return panel;
}

function defects(view) {
  const panel = el("section", "panel");
  panel.append(text("h2", "Дефект"));
  const defect = (view.defects || [])[0];
  if (!defect) {
    panel.append(text("p", "Дефектов нет"));
    return panel;
  }
  panel.append(field("Диапазон, с", defect.start_seconds + "–" + defect.end_seconds));
  panel.append(field("Диагноз", defect.diagnosis));
  panel.append(field("Сохранить", defect.preserve));
  panel.append(field("Желаемая правка", defect.desired_change));
  const plan = view.revision_plan;
  if (plan) {
    panel.append(field("Причина плана", plan.objective));
    panel.append(field("Операция плана", plan.operation));
  }
  return panel;
}

function promptBlock(view) {
  const panel = el("section", "panel");
  panel.append(text("h2", "Промпт и параметры"));
  const generation = view.generation || {};
  panel.append(field("prompt_id", generation.prompt_id));
  panel.append(field("operation", generation.operation));
  const parameters = generation.parameters || {};
  Object.keys(parameters).forEach(function (key) {
    panel.append(field(key, parameters[key]));
  });
  return panel;
}

function comparison(view) {
  const panel = el("section", "panel");
  panel.append(text("h2", "Сравнение"));
  const item = view.version_comparison;
  if (!item) {
    panel.append(text("p", "Сравнения нет"));
    return panel;
  }
  panel.append(field("Исход", item.outcome));
  panel.append(field("Родитель", item.parent_version_id));
  panel.append(field("Потомок", item.child_version_id));
  panel.append(field("Целевой дефект", item.target_defect_id));
  panel.append(text("p", "Comparator не утверждает, что прослушал музыку.", "hint"));
  return panel;
}

function qc(view) {
  const panel = el("section", "panel");
  panel.append(text("h2", "Technical QC"));
  const item = view.technical_qc;
  if (!item) {
    panel.append(text("p", "QC ещё нет"));
    panel.append(text("p", view.mock_qc_notice, "mock-note"));
    return panel;
  }
  panel.append(field("analyzer", item.analyzer));
  panel.append(field("result", item.result));
  if (item.analyzer === "mock") {
    panel.append(text("p", view.mock_qc_notice, "mock-note"));
  }
  return panel;
}

function history(view) {
  const panel = el("section", "panel");
  panel.append(text("h2", "Решения"));
  const list = el("ul", "history");
  (view.decisions || []).forEach(function (decision) {
    const captured = (view.captured_decision_ids || []).indexOf(decision.decision_id) !== -1;
    list.append(text(
      "li",
      decision.gate + " · " + decision.verdict + " · " + decision.decided_by +
        " · " + (captured ? "captured" : "pending") +
        (decision.comment ? " · " + decision.comment : "")
    ));
  });
  if (!(view.decisions || []).length) list.append(text("li", "Решений нет"));
  panel.append(list);
  return panel;
}

function knowledge(view) {
  const panel = el("section", "panel");
  panel.append(text("h2", "Knowledge capture"));
  panel.append(field("Статус текущего решения", view.pending_status || "нет решения"));
  const rules = (view.knowledge_cases || []).map(function (item) {
    return item.rule_status || "";
  });
  panel.append(field("rule_status", rules.length ? rules.join(", ") : "candidate_rule ещё не создан"));
  panel.append(text("p", "Один кейс не меняет active skills. rule_status остаётся candidate_rule.", "hint"));
  return panel;
}

function decisionForm(view) {
  const panel = el("form", "decision-form");
  panel.append(text("h2", "Решение"));
  if (!view.gate) {
    panel.append(text("p", "Сейчас нет открытого human gate."));
    return panel;
  }
  const who = document.createElement("input");
  who.id = "decided-by";
  who.name = "decided_by";
  who.required = true;
  who.autocomplete = "name";
  const whoLabel = el("label");
  whoLabel.htmlFor = "decided-by";
  whoLabel.textContent = "Кто решил";
  panel.append(whoLabel, who);
  const comment = document.createElement("textarea");
  comment.id = "comment";
  comment.name = "comment";
  const commentLabel = el("label");
  commentLabel.htmlFor = "comment";
  commentLabel.textContent = "Комментарий";
  panel.append(commentLabel, comment);
  let candidateSelect = null;
  if (view.gate === "BASE_SELECTION") {
    candidateSelect = document.createElement("select");
    candidateSelect.id = "candidate-id";
    (view.candidates || []).forEach(function (candidate) {
      const option = el("option");
      option.value = candidate.candidate_id;
      option.textContent = candidate.candidate_id;
      candidateSelect.append(option);
    });
    const label = el("label");
    label.htmlFor = "candidate-id";
    label.textContent = "Кандидат";
    panel.append(label, candidateSelect);
  }
  let rollbackSelect = null;
  if (view.gate === "REVISION_ESCALATION") {
    rollbackSelect = document.createElement("select");
    rollbackSelect.id = "rollback-version";
    (view.references.rollback_version_ids || []).forEach(function (versionId) {
      const option = el("option");
      option.value = versionId;
      option.textContent = versionId;
      rollbackSelect.append(option);
    });
    const label = el("label");
    label.htmlFor = "rollback-version";
    label.textContent = "Версия для отката";
    panel.append(label, rollbackSelect);
  }
  const actions = el("div");
  actions.id = "actions";
  (view.actions || []).forEach(function (action) {
    const button = el("button");
    button.type = "button";
    button.textContent = ACTION_LABELS[action.verdict] || action.label;
    button.disabled = posting;
    if (action.verdict === "ROLLBACK" && !(view.references.rollback_version_ids || []).length) {
      button.disabled = true;
    }
    button.addEventListener("click", function () {
      submitDecision(view, action.verdict, who.value, comment.value, candidateSelect, rollbackSelect);
    });
    actions.append(button);
  });
  panel.append(actions);
  return panel;
}

async function submitDecision(view, verdict, decidedBy, comment, candidateSelect, rollbackSelect) {
  if (posting) return;
  showError("");
  if (!decidedBy.trim()) {
    showError("Введите, кто принял решение.");
    return;
  }
  const body = {
    expected_view_token: view.view_token,
    verdict: verdict,
    decided_by: decidedBy.trim(),
    comment: comment,
  };
  if (view.gate === "BASE_SELECTION" && candidateSelect) {
    body.candidate_id = candidateSelect.value;
  }
  if (verdict === "ROLLBACK" && rollbackSelect) {
    body.version_id = rollbackSelect.value;
  }
  posting = true;
  render(view);
  try {
    const response = await fetch("/api/tracks/" + encodeURIComponent(view.track_id) + "/decisions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) {
      showError(payload.error || "Не удалось сохранить решение.");
      if (payload.view) render(payload.view);
      return;
    }
    render(payload.view || payload);
  } catch (error) {
    showError("Не удалось сохранить решение.");
  } finally {
    posting = false;
    if (currentView) render(currentView);
  }
}

boot().catch(function () {
  showError("Экран не загрузился.");
});
