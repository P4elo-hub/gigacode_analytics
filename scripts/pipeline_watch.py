#!/usr/bin/env python3
"""External controller: poll dispatch + viewer graph every N seconds."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline_dispatch import build_dispatch  # noqa: E402

VIEWER = "http://127.0.0.1:8765"


def fetch_graph(slug: str, pipeline: str) -> dict | None:
    url = f"{VIEWER}/api/graph?slug={slug}&pipeline={pipeline}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except OSError:
        return None


def snapshot(slug: str) -> str:
    d = build_dispatch(ROOT, slug)
    lines = [
        f"dispatch: {d.get('next_step')} → {d.get('next_subagent')} "
        f"[{d.get('orchestrator_mode')}] must_continue={d.get('must_continue')}",
        f"reason: {d.get('next_reason', '')}",
    ]
    for pipe in ("spec", "calibration"):
        g = fetch_graph(slug, pipe)
        if not g:
            lines.append(f"viewer/{pipe}: offline")
            continue
        tl = g.get("timeline") or []
        last = tl[-1] if tl else None
        last_s = (
            f"#{last.get('seq')} {last.get('step')} {last.get('result')}"
            if last
            else "—"
        )
        lines.append(f"viewer/{pipe}: timeline={len(tl)} last={last_s}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.once:
        print(snapshot(args.slug))
        return 0
    print(f"Watching {args.slug} (Ctrl+C to stop)\n")
    try:
        while True:
            print("---")
            print(snapshot(args.slug))
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
