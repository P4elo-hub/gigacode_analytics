#!/usr/bin/env bash
# SubagentStop: append_run_log → ingest → validate → inject workflow advice.
set -euo pipefail
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
LAB="$(cd "$HOOK_DIR/../.." && pwd)"
ROOT="$(cd "$LAB/.." && pwd)"
exec python3 "$ROOT/scripts/pipeline_after_subagent.py" \
  --cli qwen \
  --pack-dir "$LAB/pack" \
  --workspace "$LAB"
