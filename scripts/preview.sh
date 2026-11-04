#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/update_assets.py
bundle exec jekyll serve "$@"
