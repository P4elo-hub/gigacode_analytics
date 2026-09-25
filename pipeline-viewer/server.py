#!/usr/bin/env python3
"""Local pipeline graph viewer — http://127.0.0.1:8765 with SSE updates."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
VIEWER = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(VIEWER))

from artifact_paths import list_feature_slugs, workspace_root  # noqa: E402
from build_pipeline_graph import build_graph, build_pack_target_graph  # noqa: E402
from sync_pipeline_session import sync_session  # noqa: E402
from pipeline_common import known_pipeline_ids, pipeline_restartable_steps  # noqa: E402
from pipeline_pack import DEFAULT_PIPELINE_ID, discover_pipeline_ids, export_pack_json  # noqa: E402
from pipeline_active_task import feature_active_task_path  # noqa: E402
from pipeline_runtime import load_pipeline_schema  # noqa: E402
from pipeline_restart import (  # noqa: E402
    apply_restart_plan,
    build_restart_plan,
    plan_to_dict,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_PORT = 8765
API_VERSION = 7
POLL_INTERVAL = 1.0
CLI_AGENT_DIRS = (".qwen", ".gigacode", ".opencode")


def authoring_draft_path(workspace: Path, pipeline_id: str) -> Path:
    return workspace / "pipelines" / pipeline_id / ".authoring-draft.json"


def load_authoring_draft_pack(workspace: Path, pipeline_id: str) -> dict | None:
    """Browser schema draft overlay (not pack YAML). Written for authoring UI only."""
    path = authoring_draft_path(workspace, pipeline_id)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    packs = raw.get("packs")
    if isinstance(packs, dict) and isinstance(packs.get(pipeline_id), dict):
        return packs[pipeline_id]
    # allow a bare pack draft object
    if any(key in raw for key in ("nodeEdits", "positions", "extraNodes")):
        return raw
    return None


def run_pipeline_tabs(workspace: Path) -> list[dict]:
    """Прогон tabs: compiled pack ids (same set as build_graph / known_pipeline_ids)."""
    labels: dict[str, str] = {}
    try:
        from pipeline_pack import load_all_packs

        for pid, pack in load_all_packs(workspace).items():
            graph = pack.get("graph") if isinstance(pack, dict) else None
            if isinstance(graph, dict):
                labels[pid] = str(graph.get("label") or pid)
    except Exception:
        pass
    return [{"id": pid, "label": labels.get(pid, pid)} for pid in known_pipeline_ids()]


def write_feature_cycle_preview() -> dict:
    """Default write-feature queue: spec-catalog blocks for the default profile (sihist)."""
    try:
        from pipeline_common import write_cycle_config
        from section_profiles import DEFAULT_PROFILE, infer_sections
        from write_feature import list_active_blocks
    except ImportError:
        return {"profile": "", "calls": []}
    target = infer_sections("", None, DEFAULT_PROFILE)
    cfg = write_cycle_config("spec") or {}
    subagent = str(cfg.get("subagent") or "spec-writer")
    calls = []
    for block in list_active_blocks(target):
        calls.append(
            {
                "agent": subagent,
                "param": str(block.get("id") or ""),
                "label": str(block.get("label") or block.get("id") or ""),
                "skills": list(block.get("active_skills") or []),
                "sections": list(block.get("active_sections") or []),
            }
        )
    return {
        "profile": DEFAULT_PROFILE,
        "assemble": str(cfg.get("assemble") or "write_feature"),
        "param": str(cfg.get("param") or "block_id"),
        "calls": calls,
    }


def catalog_for_viewer(workspace: Path) -> dict:
    """GET /api/catalog: compile catalog plus per-CLI agent presence for the palette."""
    from pipeline_pack import build_catalog

    catalog = build_catalog(workspace)
    by_cli: dict[str, list[str]] = {}
    for cli_dir in CLI_AGENT_DIRS:
        name = cli_dir.lstrip(".")
        folder = workspace / cli_dir / "agents"
        if folder.is_dir():
            by_cli[name] = sorted(path.stem for path in folder.glob("*.md") if path.is_file())
        else:
            by_cli[name] = []
    catalog["agents_by_cli"] = by_cli
    catalog["write_feature_cycle"] = write_feature_cycle_preview()
    return catalog


def _normalize_pipeline(raw: str | None) -> str:
    pipeline = raw or DEFAULT_PIPELINE_ID
    if pipeline not in known_pipeline_ids():
        return DEFAULT_PIPELINE_ID
    return pipeline


@dataclass
class Defaults:
    slug: str = ""
    pipeline: str = "spec"
    run_id: str = "auto"


def _exclusive_pack_steps() -> dict[str, set[str]]:
    """Step ids that appear in only one pack (used to attribute legacy run-logs)."""
    step_sets: dict[str, set[str]] = {}
    for pid in known_pipeline_ids():
        try:
            schema = load_pipeline_schema(pid)
        except Exception:
            continue
        step_sets[pid] = {
            str(node.get("id") or "")
            for node in (schema.get("nodes") or [])
            if isinstance(node, dict) and node.get("id")
        }
    exclusive: dict[str, set[str]] = {}
    for pid, steps in step_sets.items():
        others: set[str] = set()
        for oid, ost in step_sets.items():
            if oid != pid:
                others |= ost
        exclusive[pid] = {s for s in steps - others if s}
    return exclusive


def pipelines_for_slug(
    workspace: Path,
    slug: str,
    *,
    exclusive: dict[str, set[str]] | None = None,
) -> list[str]:
    """Which Прогон tabs should list this slug.

    Explicit ``pipeline`` on active-task / run-log wins. Else unique step names
    from run-log. Feature-writing without evidence → ``spec`` only (legacy).
    """
    known = set(known_pipeline_ids())
    found: set[str] = set()
    steps_seen: set[str] = set()

    active_path = feature_active_task_path(workspace, slug)
    if active_path.is_file():
        try:
            data = json.loads(active_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if isinstance(data, dict):
            raw = data.get("pipeline") or data.get("pipeline_id")
            if raw and str(raw) in known:
                found.add(str(raw))

    runs_root = workspace / "agent-logs" / slug / "runs"
    if runs_root.is_dir():
        for run_dir in runs_root.iterdir():
            if not run_dir.is_dir() or not run_dir.name.startswith("run-"):
                continue
            log_path = run_dir / "run-log.jsonl"
            if not log_path.is_file():
                continue
            try:
                text = log_path.read_text(encoding="utf-8")
            except OSError:
                continue
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                raw = row.get("pipeline") or row.get("pipeline_id")
                if raw and str(raw) in known:
                    found.add(str(raw))
                step = row.get("step")
                if step:
                    steps_seen.add(str(step))

    if found:
        return sorted(found)

    excl = exclusive if exclusive is not None else _exclusive_pack_steps()
    for pid, steps in excl.items():
        if steps_seen & steps:
            found.add(pid)
    if found:
        return sorted(found)

    has_logs = (workspace / "agent-logs" / slug).is_dir()
    in_features = slug in set(list_feature_slugs(workspace))
    if has_logs or in_features:
        return [DEFAULT_PIPELINE_ID] if DEFAULT_PIPELINE_ID in known else []
    return []


def list_available_slugs(workspace: Path) -> list[dict]:
    logged: dict[str, dict] = {}
    logs_root = workspace / "agent-logs"
    if logs_root.is_dir():
        for child in logs_root.iterdir():
            if not child.is_dir() or child.name.startswith("."):
                continue
            runs_dir = child / "runs"
            run_count = 0
            has_events = False
            if runs_dir.is_dir():
                for run in runs_dir.iterdir():
                    if run.is_dir() and run.name.startswith("run-"):
                        run_count += 1
                        if (run / "events.jsonl").is_file():
                            has_events = True
            logged[child.name] = {
                "slug": child.name,
                "has_agent_logs": run_count > 0,
                "has_events": has_events,
                "run_count": run_count,
            }

    slugs: dict[str, dict] = dict(logged)
    feature_slugs = set(list_feature_slugs(workspace))
    for slug in feature_slugs:
        if slug not in slugs:
            slugs[slug] = {
                "slug": slug,
                "has_agent_logs": False,
                "has_events": False,
                "run_count": 0,
            }
        else:
            slugs[slug]["in_feature_writing"] = True
    exclusive = _exclusive_pack_steps()
    for entry in slugs.values():
        entry.setdefault("in_feature_writing", entry["slug"] in feature_slugs)
        entry["pipelines"] = pipelines_for_slug(
            workspace, entry["slug"], exclusive=exclusive
        )

    def sort_key(item: dict) -> tuple:
        return (0 if item["has_agent_logs"] else 1, item["slug"])

    return sorted(slugs.values(), key=sort_key)


def fingerprint_graph(graph: dict) -> dict[str, float]:
    fp: dict[str, float] = {}
    validation_raw = graph.get("watch_paths", {}).get("validation")
    if validation_raw:
        path = Path(validation_raw)
        if path.is_file():
            fp[str(path)] = path.stat().st_mtime

    watch = graph.get("watch_paths") or {}
    for key in ("run_log", "events", "metrics", "calibration_run", "scorecard", "active_task"):
        raw = watch.get(key)
        if not raw:
            continue
        path = Path(raw)
        if path.is_file():
            fp[str(path)] = path.stat().st_mtime
        elif path.is_dir():
            fp[str(path)] = max(
                (p.stat().st_mtime for p in path.rglob("*") if p.is_file()),
                default=0.0,
            )
        else:
            fp[str(path)] = 0.0
    for group_key in ("run_logs", "events_all"):
        group = watch.get(group_key)
        if not isinstance(group, dict):
            continue
        for path_raw in group.values():
            path = Path(path_raw)
            if path.is_file():
                fp[str(path)] = path.stat().st_mtime
    dispatch_fp = (graph.get("divergence") or {}).get("fingerprint")
    if not dispatch_fp:
        dispatch_fp = graph.get("dispatch_fingerprint")
    if isinstance(dispatch_fp, dict):
        for key, mtime in dispatch_fp.items():
            fp[f"dispatch:{key}"] = float(mtime or 0)
    return fp


def make_handler(workspace: Path, defaults: Defaults):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            if args and "200" in str(args[1]):
                return
            super().log_message(fmt, *args)

        def _send_json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)

        def _send_file(self, path: Path, content_type: str) -> None:
            if not path.is_file():
                self.send_error(404)
                return
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _query_params(self, qs: dict[str, list[str]]) -> tuple[str, str, str]:
            slug = (qs.get("slug") or [defaults.slug])[0]
            pipeline = _normalize_pipeline((qs.get("pipeline") or [defaults.pipeline])[0])
            run_id = (qs.get("run_id") or [defaults.run_id])[0]
            return slug, pipeline, run_id

        def _build(self, slug: str, pipeline: str, run_id: str) -> dict:
            if not slug:
                return build_pack_target_graph(pipeline)
            if pipeline == "spec" and slug:
                try:
                    sync_session(workspace, slug, cli="qwen")
                except Exception:
                    pass
            return build_graph(workspace, slug, run_id=run_id, pipeline=pipeline)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            qs = parse_qs(parsed.query)

            if path in ("/", "/index.html"):
                self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
                return

            if path.startswith("/static/"):
                rel = path.removeprefix("/static/")
                target = STATIC_DIR / rel
                if target.is_file() and STATIC_DIR in target.resolve().parents:
                    ctype = "text/css" if rel.endswith(".css") else "application/javascript"
                    self._send_file(target, ctype)
                else:
                    self.send_error(404)
                return

            if path == "/api/slugs":
                self._send_json({"slugs": list_available_slugs(workspace)})
                return

            if path == "/api/config":
                slugs = list_available_slugs(workspace)
                default_slug = defaults.slug
                if not default_slug and slugs:
                    with_logs = [s for s in slugs if s["has_agent_logs"]]
                    default_slug = (with_logs[0] if with_logs else slugs[0])["slug"]
                self._send_json(
                    {
                        "default_slug": default_slug,
                        "default_pipeline": defaults.pipeline,
                        "pipelines": run_pipeline_tabs(workspace),
                        "restartable_steps": list(pipeline_restartable_steps(DEFAULT_PIPELINE_ID)),
                        "restartable_steps_by_pipeline": {
                            pid: list(pipeline_restartable_steps(pid)) for pid in known_pipeline_ids()
                        },
                    }
                )
                return

            if path == "/api/graph":
                slug, pipeline, run_id = self._query_params(qs)
                try:
                    self._send_json(self._build(slug, pipeline, run_id))
                except Exception as exc:
                    self._send_json({"error": str(exc), "slug": slug}, status=500)
                return

            if path == "/api/stream":
                slug, pipeline, run_id = self._query_params(qs)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                try:
                    graph = self._build(slug, pipeline, run_id)
                    last_fp = fingerprint_graph(graph)
                    self._send_sse(graph)
                    while True:
                        time.sleep(POLL_INTERVAL)
                        graph = self._build(slug, pipeline, run_id)
                        fp = fingerprint_graph(graph)
                        if fp != last_fp:
                            last_fp = fp
                            self._send_sse(graph)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except Exception as exc:
                    self._send_sse({"error": str(exc), "slug": slug})
                return

            if path == "/api/catalog":
                self._send_json(catalog_for_viewer(workspace))
                return

            if path == "/api/pack":
                pipeline = (qs.get("pipeline") or [""])[0].strip()
                if not pipeline:
                    self._send_json({"error": "pipeline required"}, status=400)
                    return
                known = set(discover_pipeline_ids(workspace))
                if pipeline not in known:
                    self._send_json({"error": f"unknown pack: {pipeline}"}, status=404)
                    return
                try:
                    self._send_json(export_pack_json(pipeline, workspace))
                except FileNotFoundError as exc:
                    self._send_json({"error": str(exc)}, status=404)
                except Exception as exc:
                    self._send_json({"error": str(exc), "pipeline": pipeline}, status=500)
                return

            if path == "/api/pack/draft":
                pipeline = (qs.get("pipeline") or [""])[0].strip()
                if not pipeline:
                    self._send_json({"error": "pipeline required"}, status=400)
                    return
                known = set(discover_pipeline_ids(workspace))
                if pipeline not in known:
                    self._send_json({"error": f"unknown pack: {pipeline}"}, status=404)
                    return
                draft = load_authoring_draft_pack(workspace, pipeline)
                self._send_json({"ok": True, "pipeline": pipeline, "draft": draft})
                return

            if path == "/api/health":
                self._send_json(
                    {"ok": True, "version": API_VERSION, "viewer": "pipeline-viewer"}
                )
                return

            if path == "/api/restart-plan":
                slug = (qs.get("slug") or [""])[0]
                from_step = (qs.get("from_step") or [""])[0]
                from_seq_raw = (qs.get("from_seq") or [""])[0]
                from_seq = int(from_seq_raw) if from_seq_raw.isdigit() else None
                pipeline = _normalize_pipeline((qs.get("pipeline") or [DEFAULT_PIPELINE_ID])[0])
                if not slug or not from_step:
                    self._send_json({"error": "slug and from_step required"}, status=400)
                    return
                try:
                    plan = build_restart_plan(
                        workspace,
                        slug,
                        from_step,
                        from_seq=from_seq,
                        pipeline_id=pipeline,
                    )
                    self._send_json(plan_to_dict(plan))
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=400)
                except Exception as exc:
                    self._send_json({"error": str(exc)}, status=500)
                return

            self.send_error(404)

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def _read_json_body(self) -> tuple[dict | None, str | None]:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return None, "invalid JSON"
            if not isinstance(payload, dict):
                return None, "JSON object required"
            return payload, None

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/pack/validate":
                self._pack_validate()
                return
            if path == "/api/pack/apply":
                self._pack_apply()
                return
            if path == "/api/pack/init":
                self._pack_init()
                return
            if path != "/api/restart":
                self.send_error(404)
                return
            payload, err = self._read_json_body()
            if err:
                self._send_json({"error": err}, status=400)
                return
            slug = payload.get("slug", "")
            from_step = payload.get("from_step", "")
            from_seq = payload.get("from_seq")
            pipeline = _normalize_pipeline(payload.get("pipeline"))
            confirm = payload.get("confirm") is True
            if not confirm:
                self._send_json({"error": "confirm: true required"}, status=400)
                return
            if not slug or not from_step:
                self._send_json({"error": "slug and from_step required"}, status=400)
                return
            try:
                plan = build_restart_plan(
                    workspace,
                    slug,
                    from_step,
                    from_seq=from_seq,
                    pipeline_id=pipeline,
                )
                result = apply_restart_plan(workspace, plan)
                self._send_json({"plan": plan_to_dict(plan), "result": result})
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)

        def _pack_validate(self) -> None:
            from pack_authoring_api import assemble_pack_payload, preview_payload, validate_assembled

            payload, err = self._read_json_body()
            if err:
                self._send_json({"ok": False, "error": err, "errors": [{"message": err}]}, status=400)
                return
            try:
                assembled, overlay_errors, notes = assemble_pack_payload(
                    payload,
                    workspace,
                    codegen=payload.get("codegen") is True,
                )
                result = validate_assembled(assembled, workspace, overlay_errors)
                result["warnings"] = notes
                result["preview"] = preview_payload(assembled)
                self._send_json(result, status=200 if result["ok"] else 400)
            except FileNotFoundError as exc:
                self._send_json({"ok": False, "error": str(exc), "errors": [{"message": str(exc)}]}, status=404)
            except ValueError as exc:
                self._send_json({"ok": False, "error": str(exc), "errors": [{"message": str(exc)}]}, status=400)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc), "errors": [{"message": str(exc)}]}, status=500)

        def _pack_apply(self) -> None:
            from pack_authoring_api import assemble_pack_payload, apply_assembled, preview_payload, validate_assembled

            payload, err = self._read_json_body()
            if err:
                self._send_json({"ok": False, "error": err, "errors": [{"message": err}]}, status=400)
                return
            if payload.get("confirm") is not True:
                self._send_json(
                    {"ok": False, "error": "confirm: true required", "errors": [{"message": "confirm: true required"}]},
                    status=400,
                )
                return
            try:
                assembled, overlay_errors, notes = assemble_pack_payload(
                    payload,
                    workspace,
                    codegen=payload.get("codegen") is True,
                )
                checked = validate_assembled(assembled, workspace, overlay_errors)
                if not checked["ok"]:
                    checked["warnings"] = notes
                    checked["preview"] = preview_payload(assembled)
                    self._send_json(checked, status=400)
                    return
                applied = apply_assembled(
                    assembled,
                    workspace,
                    overwrite_orchestrator=payload.get("overwrite_orchestrator") is True,
                )
                self._send_json(
                    {
                        "ok": True,
                        "warnings": [*notes, *list(applied.get("notes") or [])],
                        "preview": preview_payload(assembled),
                        "written": applied["written"],
                        "compiled": applied["compiled"],
                        "pack": applied["pack"],
                        "checklist": applied.get("checklist") or [],
                        "orchestrator_notes": applied.get("orchestrator_notes") or [],
                    }
                )
            except FileNotFoundError as exc:
                self._send_json({"ok": False, "error": str(exc), "errors": [{"message": str(exc)}]}, status=404)
            except ValueError as exc:
                self._send_json({"ok": False, "error": str(exc), "errors": [{"message": str(exc)}]}, status=400)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc), "errors": [{"message": str(exc)}]}, status=500)

        def _pack_init(self) -> None:
            from pack_authoring_api import init_new_pack

            payload, err = self._read_json_body()
            if err:
                self._send_json({"ok": False, "error": err}, status=400)
                return
            pack_id = str(payload.get("id") or "").strip()
            template = str(payload.get("template") or "routing-state").strip()
            if not pack_id:
                self._send_json({"ok": False, "error": "id required"}, status=400)
                return
            try:
                result = init_new_pack(pack_id, template, workspace)
                result["ok"] = True
                self._send_json(result)
            except FileExistsError as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=409)
            except ValueError as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=500)

        def _send_sse(self, graph: dict) -> None:
            data = json.dumps(graph, ensure_ascii=False)
            msg = f"data: {data}\n\n".encode("utf-8")
            self.wfile.write(msg)
            self.wfile.flush()

    return Handler


def _bind_server(
    host: str, port: int, handler: type
) -> tuple[ThreadingHTTPServer, int]:
    for attempt in range(20):
        candidate = port + attempt
        try:
            return ThreadingHTTPServer((host, candidate), handler), candidate
        except OSError as exc:
            if exc.errno != 48:
                raise
    raise SystemExit(
        f"Ports {port}–{port + 19} are in use. Stop old viewer (lsof -i :{port}) or pick --port."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", default="", help="Default feature slug (optional)")
    parser.add_argument("--workspace", type=Path, default=None, help="Workspace root")
    parser.add_argument("--run-id", default="auto", help="agent-logs run id")
    parser.add_argument(
        "--pipeline",
        choices=("spec", "calibration"),
        default="spec",
        help="Default pipeline tab",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workspace = (args.workspace or workspace_root()).resolve()
    defaults = Defaults(slug=args.slug, pipeline=args.pipeline, run_id=args.run_id)

    handler = make_handler(workspace, defaults)
    server, port = _bind_server(args.host, args.port, handler)

    url = f"http://{args.host}:{port}/"
    print("")
    print("=" * 60)
    print(f"  ОТКРОЙТЕ В БРАУЗЕРЕ:  {url}")
    print(f"  API v{API_VERSION} — dispatch, validate, pack schema, перезапуск с шага")
    print("=" * 60)
    if port != args.port:
        print("")
        print(f"  ⚠ Порт {args.port} занят другим процессом!")
        print(f"    Не открывайте http://{args.host}:{args.port}/ — там может быть старый API.")
        print(f"    Остановите: ./pipeline-viewer/start.sh  (убьёт процессы на 8765–8769)")
    print(f"  workspace: {workspace}")
    print("  Ctrl+C to stop.")
    print("")
    (Path(__file__).parent / "LAST_URL.txt").write_text(url + "\n", encoding="utf-8")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
