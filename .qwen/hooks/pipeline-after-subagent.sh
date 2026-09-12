#!/usr/bin/env bash
# SubagentStop: append_run_log → ingest → validate → inject workflow advice.
set -euo pipefail
ROOT="${QWEN_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
exec python3 "$ROOT/scripts/pipeline_after_subagent.py" --cli qwen
