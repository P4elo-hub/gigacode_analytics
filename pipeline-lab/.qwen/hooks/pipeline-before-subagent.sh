#!/usr/bin/env bash
# PreToolUse: deny `task` when subagent_type ≠ pipeline_delegate active-task.
set -euo pipefail
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
LAB="$(cd "$HOOK_DIR/../.." && pwd)"
ROOT="$(cd "$LAB/.." && pwd)"
exec python3 "$ROOT/scripts/pipeline_before_subagent.py" \
  --cli qwen \
  --pack-dir "$LAB/pack" \
  --workspace "$LAB"
