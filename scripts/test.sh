#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHONPATH=backend .venv/bin/pytest -q backend/tests
npm --prefix frontend run typecheck
