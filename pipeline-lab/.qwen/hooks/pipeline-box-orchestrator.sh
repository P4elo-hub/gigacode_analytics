#!/usr/bin/env bash
# PreToolUse: deny main-session reads of pipelines/ and router sources.
set -euo pipefail
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
LAB="$(cd "$HOOK_DIR/../.." && pwd)"
ROOT="$(cd "$LAB/.." && pwd)"
exec python3 "$ROOT/scripts/pipeline_box_orchestrator.py"
