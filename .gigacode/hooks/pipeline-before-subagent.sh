#!/usr/bin/env bash
# PreToolUse: deny `task` when subagent_type ≠ pipeline_delegate active-task.
set -euo pipefail
ROOT="${GIGACODE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
exec python3 "$ROOT/scripts/pipeline_before_subagent.py" --cli gigacode
