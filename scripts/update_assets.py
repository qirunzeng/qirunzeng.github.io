#!/usr/bin/env python3
"""Refresh content-based CSS/JS versions used by GitHub Pages (no plugins needed)."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {"css": "assets/css/main.css", "js": "assets/js/site.js"}


def main():
    versions = {
        name: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:16]
        for name, path in ASSETS.items()
    }
    output = ROOT / "_data/assets.json"
    content = json.dumps(versions, indent=2) + "\n"
    if not output.exists() or output.read_text() != content:
        output.write_text(content)
        print("Updated CSS/JS content versions in _data/assets.json")
    else:
        print("CSS/JS content versions are current")


if __name__ == "__main__":
    main()
