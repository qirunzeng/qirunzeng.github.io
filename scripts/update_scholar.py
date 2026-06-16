#!/usr/bin/env python3
"""Refresh Google Scholar metrics for the static site data file."""

from __future__ import annotations

import datetime as dt
import os
import pathlib
import re
import sys
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

import requests

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - exercised only on minimal local Python installs.
    BeautifulSoup = None


ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "_data" / "scholar.yml"
DEFAULT_SOURCE_URL = "https://scholar.google.com/citations?user=sITttdEAAAAJ&hl=en&oi=ao"


def read_source_url() -> str:
    if not DATA_PATH.exists():
        return DEFAULT_SOURCE_URL

    match = re.search(r'^source_url:\s*["\']?([^"\']+)["\']?\s*$', DATA_PATH.read_text(), re.MULTILINE)
    if match:
        return match.group(1).strip()
    return DEFAULT_SOURCE_URL


def read_existing_metrics() -> dict[str, int]:
    if not DATA_PATH.exists():
        return {}

    text = DATA_PATH.read_text()
    metrics: dict[str, int] = {}
    for key in ("total_citations", "h_index", "i10_index"):
        match = re.search(rf"^{key}:\s*(\d+)\s*$", text, re.MULTILINE)
        if match:
            metrics[key] = int(match.group(1))
    return metrics


def scholar_user_id(source_url: str) -> str:
    parsed = urlparse(source_url)
    user = parse_qs(parsed.query).get("user", [""])[0].strip()
    if not user:
        raise RuntimeError("Could not find the Scholar user id in source_url.")
    return user


def fetch_metrics_from_serpapi(source_url: str) -> dict[str, int] | None:
    api_key = os.environ.get("SERPAPI_KEY", "").strip()
    if not api_key:
        return None

    response = requests.get(
        "https://serpapi.com/search.json",
        params={
            "engine": "google_scholar_author",
            "author_id": scholar_user_id(source_url),
            "api_key": api_key,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    cited_by = payload.get("cited_by", {})
    rows = cited_by.get("table", [])
    metrics: dict[str, int] = {}
    key_map = {
        "citations": "total_citations",
        "h_index": "h_index",
        "i10_index": "i10_index",
    }

    for row in rows:
        if not isinstance(row, dict):
            continue
        for source_key, target_key in key_map.items():
            value = row.get(source_key)
            if isinstance(value, dict) and "all" in value:
                metrics[target_key] = clean_int(str(value["all"]))

    missing = [key for key in key_map.values() if key not in metrics]
    if missing:
        raise RuntimeError(f"SerpApi response missing Scholar metrics: {', '.join(missing)}")
    return metrics


def fetch_profile(source_url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    response = requests.get(source_url, headers=headers, timeout=30)
    response.raise_for_status()

    text = response.text
    if "detected unusual traffic" in text.lower() or "captcha" in text.lower():
        raise RuntimeError("Google Scholar returned an anti-bot or CAPTCHA page.")
    return text


def clean_int(value: str) -> int:
    value = re.sub(r"[^\d]", "", value)
    if not value:
        raise ValueError("metric value is empty")
    return int(value)


class ScholarMetricTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_metrics_table = False
        self.in_row = False
        self.in_cell = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "table" and attrs_dict.get("id") == "gsc_rsb_st":
            self.in_metrics_table = True
            return
        if not self.in_metrics_table:
            return
        if tag == "tr":
            self.in_row = True
            self.current_row = []
        elif tag == "td" and self.in_row:
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if not self.in_metrics_table:
            return
        if tag == "td" and self.in_cell:
            self.current_row.append(" ".join("".join(self.current_cell).split()))
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            self.rows.append(self.current_row)
            self.in_row = False
        elif tag == "table":
            self.in_metrics_table = False

    def handle_data(self, data: str) -> None:
        if self.in_metrics_table and self.in_cell:
            self.current_cell.append(data)


def extract_metric_rows(html: str) -> list[list[str]]:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("#gsc_rsb_st")
        if table is None:
            raise RuntimeError("Could not find the Google Scholar metrics table.")
        return [
            [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
            for row in table.select("tr")
        ]

    parser = ScholarMetricTableParser()
    parser.feed(html)
    if not parser.rows:
        raise RuntimeError("Could not find the Google Scholar metrics table.")
    return parser.rows


def parse_metrics(html: str) -> dict[str, int]:
    rows = extract_metric_rows(html)

    metrics: dict[str, int] = {}
    label_map = {
        "citations": "total_citations",
        "h-index": "h_index",
        "i10-index": "i10_index",
    }

    for row in rows:
        if len(row) < 2:
            continue

        label = row[0].lower()
        key = label_map.get(label)
        if key is None:
            continue
        metrics[key] = clean_int(row[1])

    missing = [key for key in label_map.values() if key not in metrics]
    if missing:
        raise RuntimeError(f"Missing Scholar metrics: {', '.join(missing)}")
    return metrics


def quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_metrics(source_url: str, metrics: dict[str, int]) -> None:
    updated_at = dt.datetime.now(dt.timezone.utc).date().isoformat()
    content = "\n".join(
        [
            f"source_url: {quote(source_url)}",
            f"updated_at: {quote(updated_at)}",
            f"total_citations: {metrics['total_citations']}",
            f"h_index: {metrics['h_index']}",
            f"i10_index: {metrics['i10_index']}",
            "",
        ]
    )
    DATA_PATH.write_text(content)


def github_warning(message: str) -> None:
    escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::warning title=Scholar update skipped::{escaped}", file=sys.stderr)


def main() -> int:
    source_url = read_source_url()
    try:
        metrics = fetch_metrics_from_serpapi(source_url)
        if metrics is None:
            html = fetch_profile(source_url)
            metrics = parse_metrics(html)
    except Exception as exc:
        if os.environ.get("SCHOLAR_STRICT") == "1":
            raise

        existing = read_existing_metrics()
        if {"total_citations", "h_index", "i10_index"} <= existing.keys():
            github_warning(f"Keeping existing metrics because the live fetch failed: {exc}")
            print(
                "Scholar update skipped; keeping existing metrics because the "
                f"live fetch failed: {exc}",
                file=sys.stderr,
            )
            print(
                "Existing Scholar metrics: "
                f"citations={existing['total_citations']}, "
                f"h_index={existing['h_index']}, "
                f"i10_index={existing['i10_index']}"
            )
            return 0

        raise

    write_metrics(source_url, metrics)
    print(
        "Updated Scholar metrics: "
        f"citations={metrics['total_citations']}, "
        f"h_index={metrics['h_index']}, "
        f"i10_index={metrics['i10_index']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Scholar update failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
