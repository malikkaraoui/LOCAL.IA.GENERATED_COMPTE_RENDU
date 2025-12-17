#!/bin/bash
# Script legacy: conservé pour compatibilité, délègue au script principal.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "ℹ️  start_all.sh est déprécié. Utilisez plutôt: ./scripts/start-all.sh"
exec ./scripts/start-all.sh
