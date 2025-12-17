#!/bin/bash
# Suivi centralisé des logs SCRIPT.IA
# Usage: ./scripts/tail-logs.sh

set -e

BACKEND_LOG=${BACKEND_LOG:-/tmp/backend.log}
WORKER_LOG=${WORKER_LOG:-/tmp/worker.log}
FRONTEND_LOG=${FRONTEND_LOG:-/tmp/frontend.log}

for f in "$BACKEND_LOG" "$WORKER_LOG" "$FRONTEND_LOG"; do
  if [ ! -f "$f" ]; then
    echo "(info) log absent pour l'instant: $f"
  fi
done

echo "--- Tailing logs (CTRL+C pour arrêter)"
echo "backend : $BACKEND_LOG"
echo "worker  : $WORKER_LOG"
echo "frontend: $FRONTEND_LOG"
echo

# tail multi-fichiers (macOS compatible)
exec tail -n 100 -F "$BACKEND_LOG" "$WORKER_LOG" "$FRONTEND_LOG"
