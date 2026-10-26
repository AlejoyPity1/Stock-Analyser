#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check --cache-dir /workspace/.pip-cache -r backend/requirements.lock.txt
npm --prefix frontend ci --cache /workspace/.npm-cache --no-audit --no-fund
npm --prefix frontend run build
