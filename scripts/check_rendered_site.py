#!/usr/bin/env python3
"""Check built HTML, metadata, local links, anchors, and Scholar visibility offline."""

import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = []
        self.targets = []
        self.references = []
        self.meta = {}
        self.h1_count = 0
        self.schemas = []
        self.schema_text = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        for key in ("aria-labelledby", "aria-describedby"):
            self.references.extend(attrs.get(key, "").split())
        if tag in ("a", "link") and attrs.get("href"):
            self.targets.append(attrs["href"])
        if tag in ("img", "script") and attrs.get("src"):
            self.targets.append(attrs["src"])
        if tag == "meta":
            self.meta[attrs.get("property", attrs.get("name"))] = attrs.get("content")
        if tag == "h1":
            self.h1_count += 1
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.schema_text = ""

    def handle_data(self, data):
        if self.schema_text is not None:
            self.schema_text += data

    def handle_endtag(self, tag):
        if tag == "script" and self.schema_text is not None:
            self.schemas.append(json.loads(self.schema_text))
            self.schema_text = None


def check_site(root, scholar):
    texts = {path: path.read_text(encoding="utf-8") for path in root.rglob("*.html")}
    pages = {path: Page(text) for path, text in texts.items()}
    errors = []
    for path, page in pages.items():
        name = str(path.relative_to(root))
        duplicates = [key for key, count in Counter(page.ids).items() if count > 1]
        if duplicates:
            errors.append(f"{name}: duplicate IDs: {duplicates}")
        for reference in page.references:
            if reference not in page.ids:
                errors.append(f"{name}: missing accessibility target #{reference}")
        for href in page.targets:
            url = urlsplit(href)
            if url.scheme or url.netloc:
                continue
            target = (root / unquote(url.path).lstrip("/")) if url.path.startswith("/") else (path.parent / unquote(url.path) if url.path else path)
            target = target.resolve()
            if target.is_dir():
                target /= "index.html"
            if not target.is_relative_to(root) or not target.exists():
                errors.append(f"{name}: broken local resource {href}")
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                errors.append(f"{name}: broken anchor {href}")
        if "main-content" in page.ids:
            if page.h1_count != 1:
                errors.append(f"{name}: expected exactly one h1")
            for key in ("description", "og:title", "og:description", "og:url", "og:image", "twitter:card"):
                if not page.meta.get(key):
                    errors.append(f"{name}: missing metadata {key}")
            if not page.schemas or page.schemas[0].get("@type") != "Person":
                errors.append(f"{name}: missing Person JSON-LD")
        if not scholar:
            for marker in ("scholar.google.com", "Google Scholar", "Cited by", "<dt>Citations</dt>", "<dt>h-index</dt>", "<dt>i10-index</dt>", "page-stats__source"):
                if marker in texts[path]:
                    errors.append(f"{name}: disabled Scholar information leaked: {marker}")
    publications = texts[root / "publications/index.html"]
    if scholar and ("scholar.google.com" not in publications or "page-stats__source" not in publications):
        errors.append("Enabled Scholar profile/source missing")
    for marker in ("Conference papers", "By venue"):
        if marker not in publications:
            errors.append(f"Publication statistics missing: {marker}")
    urls = ET.parse(root / "sitemap.xml").findall("{*}url/{*}loc")
    sitemap_paths = {urlsplit(item.text).path for item in urls}
    expected_paths = set()
    for path, page in pages.items():
        relative = path.relative_to(root).as_posix()
        if "main-content" in page.ids and relative != "404.html":
            expected_paths.add("/" + (relative[:-10] if relative.endswith("index.html") else relative))
    if sitemap_paths != expected_paths or len(urls) != len(expected_paths):
        errors.append(f"Unexpected sitemap entries: {sitemap_paths}")
    if errors:
        raise ValueError("\n".join(errors))
    print(f"Rendered checks passed: {len(pages)} pages, Scholar {'enabled' if scholar else 'disabled'}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--scholar", choices=("true", "false"), required=True)
    args = parser.parse_args()
    check_site(args.directory.resolve(), args.scholar == "true")
