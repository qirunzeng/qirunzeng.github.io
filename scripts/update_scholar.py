#!/usr/bin/env python3
"""Fetch and safely persist Google Scholar profile metrics.

The script intentionally exits non-zero on every fetch, parse, identity, or
validation failure. It never treats stale values as a successful refresh.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html as html_module
import json
import os
import pathlib
import re
import sys
import tempfile
import time
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = ROOT / "_data" / "scholar.yml"
MAX_RESPONSE_BYTES = 2_000_000
BTH_MIRROR_URL = "https://cse.bth.se/~fer/googlescholar-api/googlescholar.php"
METRIC_KEYS = ("total_citations", "h_index", "i10_index")
METRIC_LABELS = {
    "citations": "total_citations",
    "h-index": "h_index",
    "i10-index": "i10_index",
}
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)


class ScholarError(RuntimeError):
    """Raised when a Scholar refresh cannot be trusted."""


@dataclass(frozen=True)
class ScholarConfig:
    source_url: str
    expected_name: str
    identity_publication: str


@dataclass(frozen=True)
class ScholarSnapshot:
    name: str
    metrics: dict[str, int]
    provider: str


def yaml_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(.*?)\s*$", text, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def read_config(path: pathlib.Path) -> ScholarConfig:
    if not path.exists():
        raise ScholarError(f"Scholar data file does not exist: {path}")
    text = path.read_text(encoding="utf-8")
    source_url = yaml_scalar(text, "source_url") or ""
    expected_name = yaml_scalar(text, "expected_name") or ""
    identity_publication = yaml_scalar(text, "identity_publication") or ""
    parsed = urlparse(source_url)
    user_id = parse_qs(parsed.query).get("user", [""])[0].strip()
    if parsed.scheme != "https" or parsed.hostname != "scholar.google.com" or not user_id:
        raise ScholarError("source_url must be an HTTPS Google Scholar profile URL with a user id")
    if not expected_name:
        raise ScholarError("expected_name is required in the Scholar data file")
    if not identity_publication:
        raise ScholarError("identity_publication is required in the Scholar data file")
    return ScholarConfig(
        source_url=source_url,
        expected_name=expected_name,
        identity_publication=identity_publication,
    )


def read_existing(path: pathlib.Path) -> tuple[dict[str, int], str | None]:
    text = path.read_text(encoding="utf-8")
    metrics: dict[str, int] = {}
    for key in METRIC_KEYS:
        raw = yaml_scalar(text, key)
        if raw is None or not raw.isdigit():
            raise ScholarError(f"Existing Scholar data has no valid {key}")
        metrics[key] = int(raw)
    return metrics, yaml_scalar(text, "metrics_updated_at")


def scholar_user_id(source_url: str) -> str:
    user_id = parse_qs(urlparse(source_url).query).get("user", [""])[0].strip()
    if not user_id:
        raise ScholarError("Could not read the Scholar user id from source_url")
    return user_id


def normalized_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    return " ".join(value.casefold().split())


def clean_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ScholarError("A boolean is not a valid Scholar metric")
    if isinstance(value, int):
        return value
    digits = re.sub(r"[^0-9]", "", str(value))
    if not digits:
        raise ScholarError(f"Invalid Scholar metric value: {value!r}")
    return int(digits)


class ScholarProfileParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.in_name = False
        self.name_tag = ""
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []
        self.name_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id") == "gsc_prf_in":
            self.in_name = True
            self.name_tag = tag
        if tag == "table" and attributes.get("id") == "gsc_rsb_st":
            self.in_table = True
            return
        if not self.in_table:
            return
        if tag == "tr":
            self.in_row = True
            self.current_row = []
        elif tag == "td" and self.in_row:
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if self.in_name and tag == self.name_tag:
            self.in_name = False
        if not self.in_table:
            return
        if tag == "td" and self.in_cell:
            self.current_row.append(" ".join("".join(self.current_cell).split()))
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            if self.current_row:
                self.rows.append(self.current_row)
            self.in_row = False
        elif tag == "table":
            self.in_table = False

    def handle_data(self, data: str) -> None:
        if self.in_name:
            self.name_parts.append(data)
        if self.in_table and self.in_cell:
            self.current_cell.append(data)


def parse_scholar_html(html: str) -> ScholarSnapshot:
    lowered = html.casefold()
    challenge_markers = (
        "detected unusual traffic",
        "our systems have detected",
        "g-recaptcha",
        "not a robot",
    )
    if any(marker in lowered for marker in challenge_markers):
        raise ScholarError("Google Scholar returned an anti-bot or CAPTCHA page")

    parser = ScholarProfileParser()
    parser.feed(html)
    name = " ".join("".join(parser.name_parts).split())
    if not name:
        raise ScholarError("Google Scholar profile name was not found")

    metrics: dict[str, int] = {}
    for row in parser.rows:
        if len(row) < 2:
            continue
        key = METRIC_LABELS.get(row[0].casefold())
        if key:
            metrics[key] = clean_int(row[1])
    missing = [key for key in METRIC_KEYS if key not in metrics]
    if missing:
        raise ScholarError(f"Google Scholar metrics table is incomplete: {', '.join(missing)}")
    return ScholarSnapshot(name=name, metrics=metrics, provider="google-scholar")


def fetch_bytes(url: str, *, timeout: int = 30) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ScholarError("Scholar response exceeded the safe size limit")
    return payload


def retry(operation_name: str, operation: Any, attempts: int = 3) -> Any:
    errors: list[str] = []
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except (ScholarError, HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            errors.append(f"attempt {attempt}: {type(exc).__name__}: {exc}")
            if isinstance(exc, HTTPError) and exc.code in {400, 401, 403, 404}:
                break
            if attempt < attempts:
                time.sleep(attempt * 2)
    raise ScholarError(f"{operation_name} failed; " + " | ".join(errors))


def fetch_from_google(source_url: str) -> ScholarSnapshot:
    def operation() -> ScholarSnapshot:
        html = fetch_bytes(source_url).decode("utf-8", errors="replace")
        return parse_scholar_html(html)

    return retry("Direct Google Scholar fetch", operation)


def parse_serpapi_payload(payload: dict[str, Any]) -> ScholarSnapshot:
    if payload.get("error"):
        raise ScholarError(f"SerpApi error: {payload['error']}")
    author = payload.get("author")
    name = author.get("name", "") if isinstance(author, dict) else ""
    rows = payload.get("cited_by", {}).get("table", [])
    metrics: dict[str, int] = {}
    source_keys = {
        "citations": "total_citations",
        "h_index": "h_index",
        "i10_index": "i10_index",
    }
    for row in rows:
        if not isinstance(row, dict):
            continue
        for source_key, target_key in source_keys.items():
            value = row.get(source_key)
            if isinstance(value, dict) and "all" in value:
                metrics[target_key] = clean_int(value["all"])
    missing = [key for key in METRIC_KEYS if key not in metrics]
    if not name or missing:
        raise ScholarError(
            "SerpApi response is incomplete"
            + (f": missing {', '.join(missing)}" if missing else "")
        )
    return ScholarSnapshot(name=str(name), metrics=metrics, provider="serpapi")


def fetch_from_serpapi(source_url: str, api_key: str) -> ScholarSnapshot:
    query = urlencode(
        {
            "engine": "google_scholar_author",
            "author_id": scholar_user_id(source_url),
            "hl": "en",
            "api_key": api_key,
        }
    )

    def operation() -> ScholarSnapshot:
        raw = fetch_bytes(f"https://serpapi.com/search.json?{query}")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ScholarError("SerpApi did not return a JSON object")
        return parse_serpapi_payload(payload)

    return retry("SerpApi fetch", operation, attempts=2)


def parse_bth_payload(
    payload: dict[str, Any], *, expected_name: str, identity_publication: str
) -> ScholarSnapshot:
    publications = payload.get("publications")
    if not isinstance(publications, list) or not publications:
        raise ScholarError("BTH Scholar mirror returned no publications")
    if len(publications) >= 100:
        raise ScholarError("BTH Scholar mirror publication list may be truncated at 100")

    expected_title = normalized_name(identity_publication)
    publication_titles: list[str] = []
    citation_counts: list[int] = []
    for publication in publications:
        if not isinstance(publication, dict):
            raise ScholarError("BTH Scholar mirror returned a malformed publication")
        title = html_module.unescape(str(publication.get("title", "")))
        publication_titles.append(normalized_name(title))
        citation_counts.append(clean_int(publication.get("citations", 0)))
    if expected_title not in publication_titles:
        raise ScholarError(
            "BTH Scholar mirror identity check failed: known publication was not found"
        )

    total_citations = clean_int(payload.get("total_citations"))
    if citation_counts and max(citation_counts) > total_citations:
        raise ScholarError("BTH Scholar mirror citation totals are internally inconsistent")
    ordered_counts = sorted(citation_counts, reverse=True)
    h_index = sum(count >= rank for rank, count in enumerate(ordered_counts, start=1))
    i10_index = sum(count >= 10 for count in ordered_counts)
    return ScholarSnapshot(
        name=expected_name,
        metrics={
            "total_citations": total_citations,
            "h_index": h_index,
            "i10_index": i10_index,
        },
        provider="bth-scholar-mirror",
    )


def fetch_from_bth_mirror(config: ScholarConfig) -> ScholarSnapshot:
    # The documented legacy endpoint passes the user value through to Scholar;
    # pagesize=100 avoids silently deriving indices from only the first 20 works.
    user = quote(f"{scholar_user_id(config.source_url)}&pagesize=100", safe="")

    def operation() -> ScholarSnapshot:
        raw = fetch_bytes(f"{BTH_MIRROR_URL}?user={user}")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ScholarError("BTH Scholar mirror did not return a JSON object")
        return parse_bth_payload(
            payload,
            expected_name=config.expected_name,
            identity_publication=config.identity_publication,
        )

    return retry("BTH Scholar mirror fetch", operation, attempts=2)


def fetch_snapshot(config: ScholarConfig) -> ScholarSnapshot:
    api_key = os.environ.get("SERPAPI_KEY", "").strip()
    errors: list[str] = []
    if api_key:
        try:
            return fetch_from_serpapi(config.source_url, api_key)
        except ScholarError as exc:
            errors.append(str(exc))
            print(f"Warning: {exc}; trying Google Scholar directly.", file=sys.stderr)
    try:
        return fetch_from_google(config.source_url)
    except ScholarError as exc:
        errors.append(str(exc))
        print(f"Warning: {exc}; trying the BTH Scholar mirror.", file=sys.stderr)
    try:
        return fetch_from_bth_mirror(config)
    except ScholarError as exc:
        errors.append(str(exc))
    raise ScholarError("All Scholar providers failed: " + " || ".join(errors))


def validate_snapshot(
    snapshot: ScholarSnapshot,
    config: ScholarConfig,
    existing: dict[str, int],
    *,
    allow_decrease: bool = False,
) -> None:
    if normalized_name(snapshot.name) != normalized_name(config.expected_name):
        raise ScholarError(
            f"Scholar identity mismatch: expected {config.expected_name!r}, got {snapshot.name!r}"
        )
    for key in METRIC_KEYS:
        value = snapshot.metrics.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 10_000_000:
            raise ScholarError(f"Scholar metric {key} is outside the accepted range: {value!r}")
    citations = snapshot.metrics["total_citations"]
    if snapshot.metrics["h_index"] > citations or snapshot.metrics["i10_index"] > citations:
        raise ScholarError("Scholar metric relationships are impossible")
    decreases = [
        f"{key}: {existing[key]} -> {snapshot.metrics[key]}"
        for key in METRIC_KEYS
        if snapshot.metrics[key] < existing[key]
    ]
    if decreases and not allow_decrease:
        raise ScholarError(
            "Scholar metrics decreased unexpectedly (manual approval required): "
            + ", ".join(decreases)
        )


def quote_yaml(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_data(
    config: ScholarConfig,
    snapshot: ScholarSnapshot,
    existing: dict[str, int],
    previous_metrics_updated_at: str | None,
    checked_at: str,
) -> str:
    metrics_changed = snapshot.metrics != existing
    metrics_updated_at = checked_at if metrics_changed else previous_metrics_updated_at or checked_at
    return "\n".join(
        [
            f"source_url: {quote_yaml(config.source_url)}",
            f"expected_name: {quote_yaml(config.expected_name)}",
            f"identity_publication: {quote_yaml(config.identity_publication)}",
            f"last_checked_at: {quote_yaml(checked_at)}",
            f"metrics_updated_at: {quote_yaml(metrics_updated_at)}",
            f"total_citations: {snapshot.metrics['total_citations']}",
            f"h_index: {snapshot.metrics['h_index']}",
            f"i10_index: {snapshot.metrics['i10_index']}",
            "",
        ]
    )


def atomic_write(path: pathlib.Path, content: str) -> bool:
    if path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = pathlib.Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-file", type=pathlib.Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--html-file", type=pathlib.Path, help="Parse a saved profile page")
    parser.add_argument(
        "--allow-decrease",
        action="store_true",
        help="Allow verified metrics to decrease during an explicitly approved manual run",
    )
    parser.add_argument("--check-only", action="store_true", help="Validate without writing data")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = read_config(args.data_file)
        existing, previous_updated_at = read_existing(args.data_file)
        if args.html_file:
            snapshot = parse_scholar_html(args.html_file.read_text(encoding="utf-8"))
        else:
            snapshot = fetch_snapshot(config)
        validate_snapshot(snapshot, config, existing, allow_decrease=args.allow_decrease)
        checked_at = dt.datetime.now(dt.timezone.utc).date().isoformat()
        content = render_data(config, snapshot, existing, previous_updated_at, checked_at)
        changed = False if args.check_only else atomic_write(args.data_file, content)
    except (ScholarError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"Scholar update failed: {exc}", file=sys.stderr)
        return 1

    metrics = snapshot.metrics
    print(
        f"Scholar check succeeded via {snapshot.provider}: "
        f"citations={metrics['total_citations']}, h-index={metrics['h_index']}, "
        f"i10-index={metrics['i10_index']}; "
        + ("data file updated" if changed else "no data-file change")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
