#!/usr/bin/env bash
# PreToolUse: deny main-session reads of pipelines/ and router sources.
set -euo pipefail
ROOT="${QWEN_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
exec python3 "$ROOT/scripts/pipeline_box_orchestrator.py"
