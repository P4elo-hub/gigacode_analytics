"""HTTP checks for the localhost music track screen."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from music_production.orchestration.state_store import StateStore, read_jsonl
from music_production.services.version_store import VersionRecord, VersionStore
import music_production.ui.server as ui_server
from music_production.ui.server import TrackHttpServer, _propose_decision
from music_production.ui.view_model import GATE_ACTIONS, MOCK_AUDIO_MESSAGE, build_view_model
from music_production.ui.engine_factory import open_engine
from tests.music_production.test_orchestration import NOW, Harness

STATIC = Path(__file__).resolve().parents[2] / "music_production" / "ui" / "static"


class ApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.server = TrackHttpServer(
            ("127.0.0.1", 0),
            self.root,
            clock=lambda: "2026-09-28T18:00:00Z",
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.temporary.cleanup()

    def request(self, path, *, method="GET", payload=None, headers=None, raw=None):
        data = raw
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        request = Request(self.base + path, data=data, method=method)
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            with urlopen(request, timeout=10) as response:
                body = response.read()
                return response.status, dict(response.headers), body
        except HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()

    def csrf(self) -> str:
        status, _headers, body = self.request("/api/session")
        self.assertEqual(status, 200)
        return json.loads(body)["csrf_token"]

    def post_decision(self, track_id, payload, *, token=None, origin=None, raw=None, content_type="application/json"):
        headers = {}
        if token is not None:
            headers["X-CSRF-Token"] = token
        if origin is not None:
            headers["Origin"] = origin
        if content_type is not None:
            headers["Content-Type"] = content_type
        return self.request(
            f"/api/tracks/{track_id}/decisions",
            method="POST",
            payload=payload,
            headers=headers,
            raw=raw,
        )

    def test_health_empty_list_and_static_contract(self) -> None:
        status, headers, body = self.request("/api/health")
        self.assertEqual(status, 200)
        self.assertNotIn("access-control-allow-origin", {key.lower() for key in headers})
        self.assertEqual(json.loads(body)["ok"], True)
        status, session_headers, _body = self.request("/api/session")
        self.assertEqual(status, 200)
        self.assertEqual(_header(session_headers, "Cache-Control"), "no-store")
        self.assertEqual(_header(session_headers, "X-Content-Type-Options"), "nosniff")
        status, page_headers, _page = self.request("/")
        self.assertEqual(status, 200)
        policy = _header(page_headers, "Content-Security-Policy")
        self.assertIn("default-src 'self'", policy)
        self.assertIn("script-src 'self'", policy)
        self.assertIn("style-src 'self'", policy)
        self.assertIn("media-src 'self'", policy)
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertNotIn("mock:", policy.lower())
        self.assertNotIn("http://", policy)
        self.assertNotIn("https://", policy)
        self.assertNotIn("*", policy)
        status, _headers, body = self.request("/api/tracks")
        self.assertEqual(json.loads(body)["tracks"], [])
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in STATIC.iterdir()
            if path.is_file()
        )
        self.assertNotIn("cdn", combined.lower())
        self.assertNotRegex(combined, r"https?://")
        self.assertNotIn("innerHTML", combined)
        self.assertNotRegex(combined, r"\b(ACCEPT|REJECT|REVISE)\b")
        self.assertEqual(
            MOCK_AUDIO_MESSAGE,
            "Mock URI: аудиобайты отсутствуют; прослушивание недоступно",
        )
        self.assertIn("mock_audio_message", combined)
        self.assertIn("audio.disabled", combined)
        persisted = {
            verdict
            for actions in GATE_ACTIONS.values()
            for verdict, _label in actions
        }
        self.assertEqual(
            persisted,
            {
                "APPROVE_PACKAGE",
                "CHANGE_LYRICS",
                "CHANGE_PRODUCTION",
                "STOP",
                "SELECT_AS_BASE",
                "REGENERATE_BATCH",
                "COMBINE_DIRECTION",
                "ACCEPT_REVISION",
                "RETRY_REVISION",
                "ROLLBACK",
                "APPROVE_FINAL",
                "REQUEST_REVISION",
            },
        )
        for gate, actions in GATE_ACTIONS.items():
            self.assertIn(gate, combined)
            for verdict, _label in actions:
                self.assertIn(verdict, combined)

    def test_unknown_track_traversal_and_static_escape(self) -> None:
        status, _headers, body = self.request("/api/tracks/missing-track")
        self.assertEqual(status, 404)
        self.assertNotIn(str(self.root), body.decode("utf-8"))
        for path in (
            "/api/tracks/%2e%2e",
            "/api/tracks/..%2fsecrets",
            "/api/tracks/%2e%2e%2fetc",
            "/static/../server.py",
            "/static/%2e%2e/server.py",
            "/static/..%2fserver.py",
        ):
            status, _headers, body = self.request(path)
            self.assertEqual(status, 404, path)
            text = body.decode("utf-8")
            self.assertNotIn("TrackHttpServer", text)
            self.assertNotIn(str(self.root), text)

    def test_symlink_track_is_hidden(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        StateStore(outside, "hidden-track", clock=lambda: NOW)
        link = self.root / "hidden-track"
        link.symlink_to(outside / "hidden-track", target_is_directory=True)
        status, _headers, body = self.request("/api/tracks")
        self.assertEqual(json.loads(body)["tracks"], [])
        status, _headers, body = self.request("/api/tracks/hidden-track")
        self.assertEqual(status, 404)
        self.assertNotIn(str(outside), body.decode("utf-8"))

    def test_audio_allowlist_and_mock_uri(self) -> None:
        runs = self.root
        StateStore(runs, "track-audio", clock=lambda: NOW)
        audio = runs / "track-audio" / "audio"
        audio.mkdir()
        payload = b"RIFF-local-marker"
        (audio / "clip.wav").write_bytes(payload)
        outside = self.root / "outside.wav"
        outside.write_bytes(b"outside-secret")
        (audio / "escape.wav").symlink_to(outside)
        versions = VersionStore(
            runs / "track-audio" / "versions.json",
            track_id="track-audio",
            clock=lambda: NOW,
        )
        versions.add(_version("ver-local", "audio/clip.wav"))
        versions.add(_version("ver-mock", "mock://audio/job.wav"))
        versions.add(_version("ver-abs", "/etc/passwd"))
        versions.add(_version("ver-dot", "../outside.wav"))
        versions.add(_version("ver-link", "audio/escape.wav"))
        versions.set_current("ver-local")
        status, headers, body = self.request("/api/tracks/track-audio/audio/ver-local")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Type"), "audio/wav")
        self.assertEqual(body, payload)
        status, _headers, body = self.request("/api/tracks/track-audio/audio/ver-mock")
        self.assertEqual(status, 409)
        self.assertEqual(json.loads(body)["error"], "AUDIO_NOT_AVAILABLE")
        for version_id in ("ver-abs", "ver-dot", "ver-link", "missing-version", "..", "%2e%2e"):
            status, _headers, body = self.request(
                f"/api/tracks/track-audio/audio/{version_id}"
            )
            self.assertIn(status, {404, 409}, version_id)
            self.assertNotIn(b"outside-secret", body)
            self.assertNotIn(b"root:", body)

    def test_post_guards_and_single_capture(self) -> None:
        harness = Harness(self.root)
        harness.reach_package_gate()
        token = self.csrf()
        view = json.loads(self.request(f"/api/tracks/{harness.track_id}")[2])
        self.assertEqual(view["outcome"], "WAITING_FOR_HUMAN")
        payload = {
            "expected_view_token": view["view_token"],
            "verdict": "APPROVE_PACKAGE",
            "decided_by": "Nina",
            "comment": "берём пакет",
        }
        status, _headers, body = self.post_decision(harness.track_id, payload)
        self.assertEqual(status, 403)
        status, _headers, body = self.post_decision(
            harness.track_id,
            payload,
            token=token,
            origin="http://evil.example",
        )
        self.assertEqual(status, 403)
        status, _headers, body = self.post_decision(
            harness.track_id,
            None,
            token=token,
            raw=b"{" * (32 * 1024 + 1),
        )
        self.assertEqual(status, 413)
        stale = dict(payload, expected_view_token="0" * 64)
        status, _headers, body = self.post_decision(harness.track_id, stale, token=token)
        self.assertEqual(status, 409)
        self.assertEqual(json.loads(body)["error"], "STALE_VIEW")
        wrong = dict(payload, verdict="APPROVE_FINAL")
        status, _headers, body = self.post_decision(harness.track_id, wrong, token=token)
        self.assertEqual(status, 422)
        self.assertEqual(json.loads(body)["error"], "invalid_verdict")
        foreign = dict(payload, version_id="ver-not-allowed")
        status, _headers, body = self.post_decision(harness.track_id, foreign, token=token)
        self.assertEqual(status, 422)
        self.assertEqual(json.loads(body)["error"], "invalid_reference")

        status, saved_headers, body = self.post_decision(harness.track_id, payload, token=token)
        self.assertEqual(status, 200, body)
        self.assertEqual(_header(saved_headers, "Cache-Control"), "no-store")
        self.assertEqual(_header(saved_headers, "X-Content-Type-Options"), "nosniff")
        self.assertNotIn("access-control-allow-origin", {key.lower() for key in saved_headers})
        saved = json.loads(body)
        self.assertEqual(saved["applied_step"], "capture-knowledge")
        self.assertEqual(saved["step"], "prompt-compile")
        self.assertEqual(saved["outcome"], "READY")
        self.assertFalse(
            (self.root / harness.track_id / "artifacts" / "generation-request").exists()
        )
        decisions = read_jsonl(self.root / harness.track_id / "decisions.jsonl")
        cases = read_jsonl(self.root / harness.track_id / "expert-cases.jsonl")
        events = read_jsonl(self.root / harness.track_id / "events.jsonl")
        self.assertEqual(len(decisions), 1)
        self.assertEqual(len(cases), 1)
        self.assertEqual(decisions[0]["payload"]["comment"], "берём пакет")
        self.assertEqual(decisions[0]["payload"]["decided_by"], "Nina")
        self.assertIn(decisions[0]["payload"]["decision_id"], saved["captured_decision_ids"])

        status, _headers, body = self.post_decision(harness.track_id, payload, token=token)
        self.assertEqual(status, 200, body)
        self.assertEqual(len(read_jsonl(self.root / harness.track_id / "decisions.jsonl")), 1)
        self.assertEqual(len(read_jsonl(self.root / harness.track_id / "expert-cases.jsonl")), 1)
        self.assertEqual(len(read_jsonl(self.root / harness.track_id / "events.jsonl")), len(events))
        reloaded = json.loads(self.request(f"/api/tracks/{harness.track_id}")[2])
        self.assertEqual(reloaded["decisions"][0]["comment"], "берём пакет")
        self.assertIn(reloaded["decisions"][0]["decision_id"], reloaded["captured_decision_ids"])
        self.assertNotEqual(reloaded["outcome"], "WAITING_FOR_HUMAN")

    def test_invalid_candidate_and_stop_and_recovery(self) -> None:
        harness = Harness(self.root)
        harness.reach_package_gate()
        harness.approve_package()
        harness.reach_base_gate()
        token = self.csrf()
        view = json.loads(self.request(f"/api/tracks/{harness.track_id}")[2])
        self.assertEqual(view["outcome"], "WAITING_FOR_HUMAN")
        status, _headers, body = self.post_decision(
            harness.track_id,
            {
                "expected_view_token": view["view_token"],
                "verdict": "SELECT_AS_BASE",
                "decided_by": "Nina",
                "comment": "",
                "candidate_id": "not-in-batch",
            },
            token=token,
        )
        self.assertEqual(status, 422)
        self.assertEqual(json.loads(body)["error"], "invalid_reference")
        self.assertEqual(
            json.loads(self.request(f"/api/tracks/{harness.track_id}")[2])["outcome"],
            "WAITING_FOR_HUMAN",
        )

        stop_harness = Harness(self.root, track_id="track-stop")
        stop_harness.reach_package_gate()
        stop_view = json.loads(self.request("/api/tracks/track-stop")[2])
        self.assertEqual(stop_view["outcome"], "WAITING_FOR_HUMAN")
        self.assertNotEqual(stop_view["state"], "PAUSED")
        status, _headers, body = self.post_decision(
            "track-stop",
            {
                "expected_view_token": stop_view["view_token"],
                "verdict": "STOP",
                "decided_by": "Nina",
                "comment": "стоп",
            },
            token=token,
        )
        self.assertEqual(status, 200, body)
        stopped = json.loads(body)
        self.assertEqual(stopped["state"], "PAUSED")
        self.assertEqual(stopped["applied_step"], "capture-knowledge")

        recovery = Harness(self.root, track_id="track-recover")
        recovery.reach_package_gate()
        engine = open_engine(self.root, "track-recover", clock=self.server.clock)
        view = build_view_model(engine)
        proposed = _propose_decision(
            engine,
            "PACKAGE_APPROVAL",
            "APPROVE_PACKAGE",
            "Nina",
            "снова",
            {"verdict": "APPROVE_PACKAGE", "decided_by": "Nina", "comment": "снова"},
        )
        engine.record_decision(proposed)
        self.assertEqual(len(read_jsonl(self.root / "track-recover" / "expert-cases.jsonl")), 0)
        status, _headers, body = self.post_decision(
            "track-recover",
            {
                "expected_view_token": view["view_token"],
                "verdict": "APPROVE_PACKAGE",
                "decided_by": "Nina",
                "comment": "снова",
            },
            token=token,
        )
        self.assertEqual(status, 200, body)
        self.assertEqual(json.loads(body)["applied_step"], "capture-knowledge")
        self.assertEqual(len(read_jsonl(self.root / "track-recover" / "decisions.jsonl")), 1)
        self.assertEqual(len(read_jsonl(self.root / "track-recover" / "expert-cases.jsonl")), 1)

    def test_conflicting_decision_id_is_rejected(self) -> None:
        harness = Harness(self.root, track_id="track-conflict")
        harness.reach_package_gate()
        token = self.csrf()
        engine = open_engine(self.root, harness.track_id, clock=self.server.clock)
        view = build_view_model(engine)
        proposed = _propose_decision(
            engine,
            "PACKAGE_APPROVAL",
            "STOP",
            "Nina",
            "стоп",
            {"verdict": "STOP", "decided_by": "Nina", "comment": "стоп"},
        )
        tampered = dict(proposed)
        tampered["comment"] = "другой"
        engine.record_decision(tampered)
        status, _headers, body = self.post_decision(
            harness.track_id,
            {
                "expected_view_token": view["view_token"],
                "verdict": "STOP",
                "decided_by": "Nina",
                "comment": "стоп",
            },
            token=token,
        )
        self.assertEqual(status, 409)
        self.assertEqual(json.loads(body)["error"], "DECISION_CONFLICT")
        snapshot = json.loads(
            (self.root / harness.track_id / "expert-decision.json").read_text(encoding="utf-8")
        )
        self.assertEqual(snapshot["comment"], "другой")
        self.assertEqual(len(read_jsonl(self.root / harness.track_id / "decisions.jsonl")), 1)
        self.assertEqual(len(read_jsonl(self.root / harness.track_id / "expert-cases.jsonl")), 0)


    def test_track_locks_are_independent(self) -> None:
        first = self.server.track_lock("track-a")
        self.assertIs(first, self.server.track_lock("track-a"))
        other = self.server.track_lock("track-b")
        self.assertIsNot(first, other)
        with first:
            self.assertTrue(other.acquire(timeout=0.2))
            other.release()

    def test_host_rejects_rebinding_and_forwarded_host(self) -> None:
        status, _headers, body = self.request("/api/health", headers={"Host": "evil.example"})
        self.assertEqual(status, 421)
        self.assertEqual(json.loads(body)["error"], "host_rejected")
        status, _headers, body = self.request(
            "/api/health",
            headers={"Host": "evil.example", "X-Forwarded-Host": f"127.0.0.1:{self.port}"},
        )
        self.assertEqual(status, 421)
        self.assertEqual(json.loads(body)["error"], "host_rejected")
        status, _headers, _body = self.request(
            "/api/health",
            headers={"Host": f"127.0.0.1:{self.port}"},
        )
        self.assertEqual(status, 200)
        status, _headers, _body = self.request(
            "/api/health",
            headers={"Host": f"localhost:{self.port}"},
        )
        self.assertEqual(status, 200)
        status, _headers, _body = self.request("/api/health", headers={"Host": "127.0.0.1"})
        self.assertEqual(status, 421)
        token = self.csrf()
        harness = Harness(self.root, track_id="track-origin")
        harness.reach_package_gate()
        view = json.loads(self.request("/api/tracks/track-origin")[2])
        status, _headers, body = self.post_decision(
            "track-origin",
            {
                "expected_view_token": view["view_token"],
                "verdict": "STOP",
                "decided_by": "Nina",
                "comment": "чужой origin",
            },
            token=token,
            origin="http://evil.example",
        )
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error"], "origin_rejected")
        self.assertEqual(len(read_jsonl(self.root / "track-origin" / "decisions.jsonl")), 0)

    def test_concurrent_distinct_decisions_keep_one_capture(self) -> None:
        self._assert_concurrent_posts(
            track_id="track-distinct",
            comments=("первый вариант", "второй вариант"),
            statuses={200, 409},
        )

    def test_concurrent_identical_decisions_capture_once(self) -> None:
        self._assert_concurrent_posts(
            track_id="track-identical",
            comments=("один и тот же", "один и тот же"),
            statuses={200},
        )

    def _assert_concurrent_posts(
        self,
        *,
        track_id: str,
        comments: tuple,
        statuses: set,
    ) -> None:
        harness = Harness(self.root, track_id=track_id)
        harness.reach_package_gate()
        token = self.csrf()
        view = json.loads(self.request(f"/api/tracks/{track_id}")[2])
        barrier = threading.Barrier(2)
        original_lock = self.server.track_lock
        capture_calls = []
        original_open = ui_server.open_engine

        def gated(track):
            barrier.wait(timeout=5)
            return original_lock(track)

        def wrapped_open(*args, **kwargs):
            engine = original_open(*args, **kwargs)
            original_run = engine.run_one_step

            def run_one_step():
                capture_calls.append(engine.track_id)
                return original_run()

            engine.run_one_step = run_one_step
            return engine

        self.server.track_lock = gated
        ui_server.open_engine = wrapped_open
        results = []
        errors = []

        def worker(comment: str) -> None:
            try:
                results.append(
                    self.post_decision(
                        track_id,
                        {
                            "expected_view_token": view["view_token"],
                            "verdict": "APPROVE_PACKAGE",
                            "decided_by": "Nina",
                            "comment": comment,
                        },
                        token=token,
                    )
                )
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(comment,)) for comment in comments]
        try:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=15)
                self.assertFalse(thread.is_alive())
        finally:
            self.server.track_lock = original_lock
            ui_server.open_engine = original_open
        self.assertEqual(errors, [])
        codes = [item[0] for item in results]
        self.assertEqual(set(codes), statuses)
        self.assertEqual(codes.count(200), 1 if 409 in statuses else 2)
        if 409 in statuses:
            failed = [json.loads(item[2])["error"] for item in results if item[0] == 409]
            self.assertEqual(failed, ["STALE_VIEW"])
        self.assertEqual(sum(1 for item in results if item[0] == 200 and json.loads(item[2]).get("applied_step") == "capture-knowledge"), 1)
        decisions = read_jsonl(self.root / track_id / "decisions.jsonl")
        cases = read_jsonl(self.root / track_id / "expert-cases.jsonl")
        events = read_jsonl(self.root / track_id / "events.jsonl")
        self.assertEqual(len(decisions), 1)
        self.assertEqual(len(cases), 1)
        captured = json.loads((self.root / track_id / "knowledge.json").read_text(encoding="utf-8"))
        self.assertEqual(captured["captured_decision_ids"], [decisions[0]["payload"]["decision_id"]])
        self.assertEqual(capture_calls, [track_id])
        self.assertEqual(len(events), len({item["event_id"] for item in events}))
        self.assertEqual(len(decisions), len({item["event_id"] for item in decisions}))
        self.assertFalse((self.root / track_id / "artifacts" / "generation-request").exists())
        saved = json.loads(next(item[2] for item in results if item[0] == 200))
        self.assertEqual(saved["step"], "prompt-compile")


def _header(headers: dict, name: str):
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


def _version(version_id: str, audio_uri: str) -> VersionRecord:
    return VersionRecord(
        version_id=version_id,
        parent_version_id=None,
        operation="generate-batch",
        prompt_id="prompt-001",
        audio_uri=audio_uri,
        checksum="checksum-" + version_id,
        status="candidate",
    )


if __name__ == "__main__":
    unittest.main()
