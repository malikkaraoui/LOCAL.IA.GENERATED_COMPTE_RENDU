#!/usr/bin/env python
"""Script pour démarrer un worker RQ."""

import os
import sys
from pathlib import Path

# Fix for macOS fork() issue with Objective-C libraries
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.workers.report_worker import start_worker

if __name__ == "__main__":
    print("🚀 Démarrage du RQ worker...")
    start_worker()
