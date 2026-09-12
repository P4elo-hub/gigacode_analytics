#!/usr/bin/env bash
# Останавливает старые viewer на 8765–8769 и запускает актуальный сервер.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

stop_port() {
  local port=$1
  local pids
  pids=$(lsof -ti ":$port" 2>/dev/null || true)
  [[ -z "$pids" ]] && return 0
  echo "Stopping old viewer on port $port (PID $pids)"
  kill $pids 2>/dev/null || true
  sleep 0.4
  pids=$(lsof -ti ":$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "Force kill on port $port (PID $pids)"
    kill -9 $pids 2>/dev/null || true
    sleep 0.2
  fi
}

for port in 8765 8766 8767 8768 8769; do
  stop_port "$port"
done

exec python3 pipeline-viewer/server.py "$@"
