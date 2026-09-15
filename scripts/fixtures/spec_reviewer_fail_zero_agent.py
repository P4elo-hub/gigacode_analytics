#!/usr/bin/env python3
"""spec-reviewer stand-in for SubagentStop tests.

Does check-feature skill step 1 (`quality_gates.py`), then prints the last
assistant message in the live 2026-09-15 shape: ``PASS · fail 0`` without a
colon. The real spec-reviewer paraphrased gates that way; the hook must treat
it as ok, not fail.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent

# Recorded phrasing from Qwen spec-reviewer 2026-09-15T17:59Z
# (session 10aa93b0, SubagentStop last_assistant_message).
LAST_ASSISTANT_MESSAGE = """Ревизия завершена. Скилл `check-feature` выполнен по шагам. Итог ниже.

## Результат по приоритетным указаниям / alignment

Приоритетных указаний и alignment-focus во входе не было; `*-code-alignment.md` не читался (правило Шага 1). Отчёт code-alignment отсутствует — `/check-feature-code` ещё не запускался.

## Что проверено

**Структурные gates (`quality_gates.py`):** PASS · fail 0 · warn 1. Warn `QG-CONTRACT-02` (для gRPC нет маркеров `rpc`/`metadata`) — приёмлем: существующий контракт.

Фактических ошибок не выявлено — правок в `SPEC` не вносил.
"""


def run_quality_gates(root: Path, slug: str) -> int:
    """Skill step 1 — same command spec-reviewer runs in production."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "quality_gates.py"), slug, "--root", str(root)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    print(
        f"quality_gates rc={proc.returncode} stdout_chars={len(proc.stdout or '')}",
        file=sys.stderr,
    )
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--slug", required=True)
    args = parser.parse_args(argv)
    root = args.workspace.resolve()
    run_quality_gates(root, args.slug)
    sys.stdout.write(LAST_ASSISTANT_MESSAGE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
