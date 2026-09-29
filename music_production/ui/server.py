"""Stdlib localhost API for one music track. Bind address is 127.0.0.1 only."""

from __future__ import annotations

import argparse
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

from jsonschema.exceptions import ValidationError

from music_production.orchestration.decisions import STEP_TO_GATE
from music_production.orchestration.engine import HUMAN_STEPS
from music_production.orchestration.errors import (
    DecisionConflictError,
    StepExecutionError,
    UnexpectedHumanGateError,
)
from music_production.orchestration.state_store import TRACK_ID, utc_now
from music_production.ui.engine_factory import (
    TrackNotFound,
    list_track_ids,
    open_engine,
    prepare_capture_runtime,
    require_track_dir,
)
from music_production.ui.view_model import (
    GATE_ACTIONS,
    audio_availability,
    build_view_model,
    decision_id_for,
    open_gate,
    resolve_audio_file,
    same_decision_fields,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_BODY = 32 * 1024
ALLOWED_HOST = "127.0.0.1"
AUDIO_TYPES = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}
POST_FIELDS = {
    "expected_view_token",
    "verdict",
    "decided_by",
    "comment",
    "candidate_id",
    "version_id",
}
HTML_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self'; "
    "media-src 'self'; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "object-src 'none'; "
    "base-uri 'none'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)


class TrackHttpServer(ThreadingHTTPServer):
    allow_reuse_address = False

    def __init__(self, server_address, runs_root: Path, clock=None) -> None:
        super().__init__(server_address, TrackHandler)
        self.runs_root = Path(runs_root)
        self.csrf_token = secrets.token_urlsafe(32)
        self.clock = clock or utc_now
        self._locks_guard = threading.Lock()
        self._track_locks: dict[str, threading.RLock] = {}

    def track_lock(self, track_id: str) -> threading.RLock:
        """RLock keyed by the safe track id, not by a filesystem path."""

        with self._locks_guard:
            lock = self._track_locks.get(track_id)
            if lock is None:
                lock = threading.RLock()
                self._track_locks[track_id] = lock
            return lock

    def origin(self) -> str:
        host, port = self.server_address[:2]
        return f"http://{host}:{port}"


class TrackHandler(BaseHTTPRequestHandler):
    server: TrackHttpServer

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if not _host_ok(self):
            self._send_json({"error": "host_rejected"}, status=421)
            return
        parsed = urlparse(self.path)
        parts = _parts(parsed.path)
        if parts == [] or parts == ["index.html"]:
            self._send_static("index.html")
            return
        if parts[:1] == ["static"]:
            self._send_static("/".join(parts[1:]))
            return
        if parts == ["api", "health"]:
            self._send_json({"ok": True, "service": "music-track-ui"})
            return
        if parts == ["api", "session"]:
            self._send_json({"csrf_token": self.server.csrf_token})
            return
        if parts == ["api", "tracks"]:
            self._send_json({"tracks": _track_summaries(self.server.runs_root)})
            return
        if len(parts) == 3 and parts[:2] == ["api", "tracks"]:
            self._send_track(parts[2])
            return
        if (
            len(parts) == 5
            and parts[:2] == ["api", "tracks"]
            and parts[3] == "audio"
        ):
            self._send_audio(parts[2], parts[4])
            return
        self._send_json({"error": "not_found"}, status=404)

    def do_POST(self) -> None:
        if not _host_ok(self):
            self._send_json({"error": "host_rejected"}, status=421)
            return
        parsed = urlparse(self.path)
        parts = _parts(parsed.path)
        if not (
            len(parts) == 4
            and parts[:2] == ["api", "tracks"]
            and parts[3] == "decisions"
        ):
            self._send_json({"error": "not_found"}, status=404)
            return
        self._post_decision(parts[2])

    def _post_decision(self, track_id: str) -> None:
        if not _csrf_ok(self):
            self._send_json({"error": "csrf_required"}, status=403)
            return
        if not _origin_ok(self):
            self._send_json({"error": "origin_rejected"}, status=403)
            return
        content_type = self.headers.get("Content-Type", "")
        if content_type.split(";", 1)[0].strip().lower() != "application/json":
            self._send_json({"error": "unsupported_media_type"}, status=415)
            return
        length = self.headers.get("Content-Length")
        if length is None or not length.isdigit():
            self._send_json({"error": "invalid_json"}, status=400)
            return
        size = int(length)
        if size > MAX_BODY:
            self._send_json({"error": "payload_too_large"}, status=413)
            return
        raw = self.rfile.read(size)
        if len(raw) > MAX_BODY:
            self._send_json({"error": "payload_too_large"}, status=413)
            return
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            self._send_json({"error": "invalid_json"}, status=400)
            return
        if not isinstance(payload, dict) or set(payload) - POST_FIELDS:
            self._send_json({"error": "invalid_json"}, status=422)
            return
        if TRACK_ID.fullmatch(track_id) is None:
            self._send_json({"error": "not_found"}, status=404)
            return
        with self.server.track_lock(track_id):
            try:
                engine = open_engine(
                    self.server.runs_root,
                    track_id,
                    clock=self.server.clock,
                )
            except TrackNotFound:
                self._send_json({"error": "not_found"}, status=404)
                return
            try:
                status, body = apply_posted_decision(engine, payload)
            except ValidationError:
                self._send_json({"error": "invalid_decision"}, status=422)
                return
            except DecisionConflictError:
                self._send_json({"error": "DECISION_CONFLICT"}, status=409)
                return
            except UnexpectedHumanGateError:
                self._send_json({"error": "DECISION_PENDING"}, status=409)
                return
            except StepExecutionError:
                self._send_json(
                    {"error": "capture_failed", "view": build_view_model(engine)},
                    status=409,
                )
                return
        self._send_json(body, status=status)

    def _send_track(self, track_id: str) -> None:
        try:
            engine = open_engine(self.server.runs_root, track_id, clock=self.server.clock)
        except TrackNotFound:
            self._send_json({"error": "not_found"}, status=404)
            return
        self._send_json(build_view_model(engine))

    def _send_audio(self, track_id: str, version_id: str) -> None:
        try:
            track_dir = require_track_dir(self.server.runs_root, track_id)
            engine = open_engine(
                self.server.runs_root,
                track_id,
                clock=self.server.clock,
            )
        except TrackNotFound:
            self._send_json({"error": "not_found"}, status=404)
            return
        try:
            record = engine.handlers.versions.get(version_id)
        except Exception:
            self._send_json({"error": "not_found"}, status=404)
            return
        availability = audio_availability(track_dir, record.audio_uri)
        if availability["audio_block_reason"] == "mock_uri":
            self._send_json({"error": "AUDIO_NOT_AVAILABLE"}, status=409)
            return
        path = resolve_audio_file(track_dir, record.audio_uri)
        if path is None:
            self._send_json({"error": "not_found"}, status=404)
            return
        body = path.read_bytes()
        suffix = path.suffix.lower()
        self._send_bytes(body, AUDIO_TYPES.get(suffix, "application/octet-stream"))

    def _send_static(self, relative: str) -> None:
        if not relative or "/" in relative or "\\" in relative or relative in {".", ".."}:
            self._send_json({"error": "not_found"}, status=404)
            return
        target = (STATIC_DIR / relative)
        if target.is_symlink():
            self._send_json({"error": "not_found"}, status=404)
            return
        try:
            resolved = target.resolve()
        except OSError:
            self._send_json({"error": "not_found"}, status=404)
            return
        root = STATIC_DIR.resolve()
        if resolved != root and root not in resolved.parents:
            self._send_json({"error": "not_found"}, status=404)
            return
        if not resolved.is_file():
            self._send_json({"error": "not_found"}, status=404)
            return
        content_type = "text/plain; charset=utf-8"
        if resolved.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif resolved.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif resolved.suffix == ".js":
            content_type = "text/javascript; charset=utf-8"
        self._send_bytes(resolved.read_bytes(), content_type)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(body, "application/json; charset=utf-8", status=status)

    def _send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if content_type.startswith("text/html"):
            self.send_header("Content-Security-Policy", HTML_CSP)
        self.end_headers()
        self.wfile.write(body)


def _parts(path: str) -> list[str]:
    return [unquote(part) for part in path.split("/") if part]


def _csrf_ok(handler: TrackHandler) -> bool:
    provided = handler.headers.get("X-CSRF-Token", "")
    expected = handler.server.csrf_token
    return bool(provided) and secrets.compare_digest(provided, expected)


def _host_ok(handler: TrackHandler) -> bool:
    """Accept only this process's localhost Host. Ignore X-Forwarded-Host."""

    raw = handler.headers.get("Host")
    if not isinstance(raw, str):
        return False
    host = raw.strip()
    if host != raw or " " in host or "," in host:
        return False
    port = int(handler.server.server_address[1])
    allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
    if port in {80, 443}:
        allowed.update({"127.0.0.1", "localhost"})
    return host in allowed


def _allowed_origins(handler: TrackHandler) -> set[str]:
    port = int(handler.server.server_address[1])
    allowed = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
    if port == 80:
        allowed.update({"http://127.0.0.1", "http://localhost"})
    return allowed


def _origin_ok(handler: TrackHandler) -> bool:
    origin = handler.headers.get("Origin")
    if origin is None:
        return True
    return origin in _allowed_origins(handler)


def _track_summaries(runs_root: Path) -> list[dict]:
    summaries = []
    for track_id in list_track_ids(runs_root):
        engine = open_engine(runs_root, track_id)
        summaries.append(
            {
                "track_id": track_id,
                "state": engine.state_store.load()["state"],
            }
        )
    return summaries


def apply_posted_decision(engine, payload: dict) -> tuple[int, dict]:
    """Apply one decision. Caller holds the per-track lock; this re-reads state."""

    view = build_view_model(engine)
    token = payload.get("expected_view_token")
    verdict = payload.get("verdict")
    decided_by = payload.get("decided_by")
    if not isinstance(token, str) or not token:
        return 422, {"error": "invalid_decision"}
    if not isinstance(verdict, str) or not isinstance(decided_by, str) or not decided_by.strip():
        return 422, {"error": "invalid_decision"}
    comment = payload.get("comment")
    if comment is not None and not isinstance(comment, str):
        return 422, {"error": "invalid_decision"}
    decided_by = decided_by.strip()
    pending = _pending_capture(engine)
    gate = open_gate(engine)
    if gate is None and pending is not None:
        gate = str(pending["gate"])
    allowed = set(GATE_ACTIONS.get(gate or "", ()))
    allowed_verdicts = {item[0] for item in allowed}
    proposed = None
    reference_error = False
    if gate is not None and verdict in allowed_verdicts:
        try:
            proposed = _propose_decision(engine, gate, verdict, decided_by, comment, payload)
        except ValueError:
            reference_error = True
    if proposed is not None:
        stored = _find_decision(engine, proposed["decision_id"])
        if stored is not None and not same_decision_fields(stored, proposed):
            return 409, {"error": "DECISION_CONFLICT"}
        if pending is not None and pending.get("decision_id") != proposed["decision_id"]:
            return 409, {"error": "DECISION_PENDING"}
        if stored is not None and _is_captured(engine, stored["decision_id"]):
            return 200, view
    elif pending is not None:
        return 409, {"error": "DECISION_PENDING"}
    elif gate is None:
        stored_match = _matching_stored(engine, payload, gate_hint=None)
        if stored_match is not None and _is_captured(engine, stored_match["decision_id"]):
            return 200, view
    if token != view["view_token"]:
        return 409, {"error": "STALE_VIEW"}
    if gate is None:
        return 409, {"error": "gate_conflict"}
    if verdict not in allowed_verdicts:
        return 422, {"error": "invalid_verdict"}
    if proposed is None or reference_error:
        return 422, {"error": "invalid_reference"}
    stored = _find_decision(engine, proposed["decision_id"])
    document = stored if stored is not None else proposed
    recorded = engine.record_decision(document)
    if _is_captured(engine, recorded["decision_id"]):
        return 200, build_view_model(engine)
    dispatch = engine.dispatch()
    if dispatch.next_step != "capture-knowledge":
        return 409, {"error": "capture_not_ready", "view": build_view_model(engine)}
    prepare_capture_runtime(engine, recorded)
    outcome = engine.run_one_step()
    fresh = build_view_model(engine)
    if outcome.executed_step != "capture-knowledge" or not _is_captured(
        engine, recorded["decision_id"]
    ):
        return 409, {
            "error": "capture_failed",
            "outcome": outcome.outcome.value,
            "view": fresh,
        }
    fresh["applied_step"] = outcome.executed_step
    return 200, fresh


def _matching_stored(engine, payload: dict, gate_hint: Optional[str]) -> Optional[dict]:
    del gate_hint
    verdict = payload.get("verdict")
    decided_by = payload.get("decided_by")
    if not isinstance(verdict, str) or not isinstance(decided_by, str):
        return None
    for item in engine.decisions.all():
        if item.get("verdict") == verdict and item.get("decided_by") == decided_by.strip():
            if (item.get("comment") or None) == _comment(payload.get("comment")):
                return item
    return None


def _comment(value: object) -> Optional[str]:
    if isinstance(value, str) and value != "":
        return value
    return None


def _find_decision(engine, decision_id: str) -> Optional[dict]:
    return next(
        (item for item in engine.decisions.all() if item.get("decision_id") == decision_id),
        None,
    )


def _pending_capture(engine) -> Optional[dict]:
    """Decision already journaled, waiting for the single capture step."""

    current = engine.decisions.current()
    decision_id = current.get("decision_id")
    if not isinstance(decision_id, str) or not decision_id:
        return None
    if _is_captured(engine, decision_id):
        return None
    if engine.dispatch().next_step != "capture-knowledge":
        return None
    return current


def _is_captured(engine, decision_id: str) -> bool:
    path = engine.state_store.track_dir / "knowledge.json"
    if not path.is_file():
        return False
    captured = read_captured(path)
    return decision_id in captured


def read_captured(path: Path) -> list[str]:
    from music_production.orchestration.state_store import read_json as load

    raw = load(path).get("captured_decision_ids")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, str)]


def _propose_decision(
    engine,
    gate: str,
    verdict: str,
    decided_by: str,
    comment: object,
    payload: dict,
) -> dict:
    view = build_view_model(engine)
    references = view["references"]
    document = {
        "schema_version": "1.0",
        "track_id": engine.track_id,
        "gate": gate,
        "verdict": verdict,
        "decided_by": decided_by,
    }
    stored_comment = _comment(comment)
    if stored_comment is not None:
        document["comment"] = stored_comment
    if gate == "PACKAGE_APPROVAL":
        package_id = references.get("song_package_version_id")
        if not isinstance(package_id, str) or not package_id:
            raise ValueError("package reference missing")
        if payload.get("candidate_id") or payload.get("version_id"):
            raise ValueError("unexpected reference")
        document["song_package_version_id"] = package_id
    elif gate == "BASE_SELECTION":
        candidate_id = payload.get("candidate_id")
        if payload.get("version_id"):
            raise ValueError("unexpected reference")
        if candidate_id not in references["candidate_ids"]:
            raise ValueError("candidate is not in the batch")
        document["candidate_id"] = candidate_id
    elif gate == "FINAL_APPROVAL":
        version_id = references.get("current_version_id")
        if not isinstance(version_id, str):
            raise ValueError("current version missing")
        if payload.get("version_id") not in {None, version_id}:
            raise ValueError("unexpected version")
        if payload.get("candidate_id"):
            raise ValueError("unexpected reference")
        document["version_id"] = version_id
    elif gate == "REVISION_ESCALATION":
        if payload.get("candidate_id"):
            raise ValueError("unexpected reference")
        if verdict == "ROLLBACK":
            version_id = payload.get("version_id")
            if version_id not in references["rollback_version_ids"]:
                raise ValueError("version is not the current parent")
            document["version_id"] = version_id
        else:
            version_id = references.get("current_version_id")
            if not isinstance(version_id, str):
                raise ValueError("current version missing")
            if payload.get("version_id") not in {None, version_id}:
                raise ValueError("unexpected version")
            document["version_id"] = version_id
    else:
        raise ValueError("unsupported gate")
    identity = {
        "track_id": document["track_id"],
        "gate": document["gate"],
        "verdict": document["verdict"],
        "decided_by": document["decided_by"],
        "comment": document.get("comment"),
        "candidate_id": document.get("candidate_id"),
        "version_id": document.get("version_id"),
        "song_package_version_id": document.get("song_package_version_id"),
    }
    document["decision_id"] = decision_id_for(identity)
    document["created_at"] = engine.state_store.clock()
    pending = _pending_capture(engine)
    if pending is not None:
        if pending.get("gate") != gate:
            raise ValueError("gate mismatch")
        return document
    if engine.dispatch().next_step not in HUMAN_STEPS:
        raise ValueError("gate is not open")
    if STEP_TO_GATE.get(engine.dispatch().next_step) != gate:
        raise ValueError("gate mismatch")
    return document


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Local music track screen")
    parser.add_argument("--runs-root", default="Music-runs")
    parser.add_argument("--host", default=ALLOWED_HOST)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args(argv)
    if args.host != ALLOWED_HOST:
        raise SystemExit("host must be 127.0.0.1")
    server = TrackHttpServer((args.host, args.port), Path(args.runs_root))
    host, port = server.server_address[:2]
    print(f"music track ui http://{host}:{port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
