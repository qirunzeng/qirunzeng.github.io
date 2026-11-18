#!/usr/bin/env python3
"""Fetch complete citing-paper lists and atomically publish their per-paper union."""

import argparse
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, unquote, urlsplit
from urllib.request import Request, urlopen

from update_scholar import atomic_write, scholar_enabled


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / '_data/citation_sources.json'
SNAPSHOT = ROOT / '_data/combined_citations.json'
S2 = 'https://api.semanticscholar.org/graph/v1/'


def normalized(text):
    text = unicodedata.normalize('NFKD', html.unescape(text)).casefold()
    return ''.join(c for c in text if c.isalnum())


def nonnegative(value):
    if type(value) is not int or value < 0:
        raise ValueError('Missing or invalid citation count')
    return value


def request_json(url, params=None, body=None):
    if params:
        url += '?' + urlencode(params)
    for attempt in range(5):
        try:
            headers = {'User-Agent': 'qirunzeng.github.io citation index'}
            encoded = None
            if body is not None:
                headers['Content-Type'] = 'application/json'
                encoded = json.dumps(body).encode()
            if url.startswith(S2) and os.getenv('SEMANTIC_SCHOLAR_KEY'):
                headers['x-api-key'] = os.environ['SEMANTIC_SCHOLAR_KEY']
            with urlopen(Request(url, data=encoded, headers=headers), timeout=45) as response:
                data = json.loads(response.read(20_000_001))
            if body is not None and isinstance(data, list):
                return data
            if not isinstance(data, dict) or data.get('error'):
                raise ValueError('Provider returned an invalid response or API error')
            return data
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            if isinstance(error, HTTPError) and error.code not in (429, 500, 502, 503, 504):
                raise ValueError(f'Provider HTTP {error.code}') from None
            if attempt == 4:
                # Never print a request URL: SerpApi URLs contain the secret.
                status = f'HTTP {error.code}' if isinstance(error, HTTPError) else type(error).__name__
                raise ValueError(f'{urlsplit(url).hostname} unavailable after five attempts ({status})') from None
            time.sleep(min(60, 5 * 2 ** attempt))
    raise AssertionError('Unreachable retry state')


def serpapi(params):
    return request_json('https://serpapi.com/search.json', {
        **params, 'api_key': os.environ['SERPAPI_KEY'], 'hl': 'en',
    })


def identifiers(urls, external=None):
    result = {}
    external = external or {}
    if external.get('DOI'):
        result['doi'] = external['DOI'].lower().removeprefix('https://doi.org/')
    if external.get('ArXiv'):
        result['arxiv'] = re.sub(r'v\d+$', '', external['ArXiv'].lower())
    for url in urls:
        text = unquote(url)
        doi = re.search(r'10\.\d{4,9}/[^?#\s]+', text, re.I)
        if doi:
            result.setdefault('doi', doi[0].lower().removesuffix('.pdf'))
        arxiv = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}|[a-z.-]+/\d{7})', text, re.I)
        if arxiv:
            result['arxiv'] = arxiv[1].lower()
    if result.get('doi', '').startswith('10.48550/arxiv.'):
        result['arxiv'] = result.pop('doi').split('arxiv.', 1)[1]
    return result


def google_record(item):
    info = item.get('publication_info') or {}
    authors = [a['name'] for a in (info.get('authors') or []) if a.get('name')]
    summary = info.get('summary') or ''
    if not authors and ' - ' in summary:
        authors = [name.strip() for name in summary.split(' - ', 1)[0].split(',')]
    year = re.search(r'\b(?:19|20)\d{2}\b', summary)
    url = item.get('link') or ''
    urls = [url] + [r.get('link') or '' for r in (item.get('resources') or [])]
    return {
        'source': 'google', 'title': html.unescape(item['title']),
        'authors': authors, 'year': int(year[0]) if year else None,
        'url': url, 'ids': {**identifiers(urls), 'google': item['result_id']},
    }


def semantic_record(item):
    return {
        'source': 'semantic', 'title': item['title'],
        'authors': [a['name'] for a in item.get('authors', []) if a.get('name')],
        'year': item.get('year'),
        'url': item.get('url') or 'https://www.semanticscholar.org/paper/' + item['paperId'],
        'ids': {**identifiers([], item.get('externalIds')), 'semantic': item['paperId']},
    }


def google_citations(article):
    cited_by = article.get('cited_by') or {}
    value = cited_by.get('value')
    expected = nonnegative(0 if value is None else value)
    if not expected:
        return [], 0
    cites = cited_by.get('cites_id') or parse_qs(urlsplit(cited_by.get('link', '')).query).get('cites', [''])[0]
    if not cites:
        raise ValueError('Google article has citations but no citing-list identifier')
    records, seen = [], set()
    start = 0
    while True:
        data = serpapi({'engine': 'google_scholar', 'cites': cites, 'num': 20, 'start': start})
        items = data.get('organic_results')
        if not isinstance(items, list) or not items:
            raise ValueError('Google returned an incomplete citing list')
        for item in items:
            record = google_record(item)
            key = record['ids']['google']
            if key in seen:
                raise ValueError('Google pagination repeated a citing record')
            records.append(record)
            seen.add(key)
        next_url = data.get('serpapi_pagination', {}).get('next')
        if not next_url:
            break
        next_start = int(parse_qs(urlsplit(next_url).query)['start'][0])
        if next_start <= start or next_start > 10000:
            raise ValueError('Invalid Google pagination')
        start = next_start
    if len(records) != expected:
        raise ValueError(f'Google citing-list coverage differs from article count: {len(records)} / {expected}')
    return records, expected


def semantic_pages(path, fields):
    records, offset = [], 0
    while True:
        time.sleep(1.1)
        data = request_json(S2 + path, {'fields': fields, 'limit': 100, 'offset': offset})
        items = data.get('data')
        if not isinstance(items, list):
            raise ValueError('Semantic Scholar returned an incomplete list')
        records.extend(items)
        next_offset = data.get('next')
        if next_offset is None:
            return records
        if type(next_offset) is not int or next_offset <= offset or next_offset > 10000:
            raise ValueError('Invalid Semantic Scholar pagination')
        offset = next_offset


def uniquely_match(papers, title):
    matches = [p for p in papers if normalized(p['title']) == normalized(title)]
    if len(matches) != 1:
        raise ValueError(f'Could not uniquely match publication: {title}')
    return matches[0]


def fetch(config):
    if not os.getenv('SERPAPI_KEY'):
        raise ValueError('SERPAPI_KEY is required for the complete Google citing lists')
    semantic = semantic_pages('author/' + config['semantic_author_id'] + '/papers', 'title,externalIds,citationCount')
    targets = [uniquely_match(semantic, p['title']) for p in config['papers']]
    time.sleep(3)
    # One batch avoids a separate API request for every small citation list.
    batch = request_json(S2 + 'paper/batch', {
        'fields': 'title,citationCount,citations.title,citations.authors,citations.year,citations.externalIds,citations.url',
    }, body={'ids': [p['paperId'] for p in targets]})
    if not isinstance(batch, list) or len(batch) != len(targets) or any(not p for p in batch):
        raise ValueError('Incomplete Semantic Scholar paper batch')
    print('Fetched Semantic Scholar paper batch', flush=True)
    google = serpapi({'engine': 'google_scholar_author', 'author_id': config['google_author_id'], 'num': 100})
    if normalized(google.get('author', {}).get('name', '')) != normalized('Qirun Zeng'):
        raise ValueError('Google author identity mismatch')
    if google.get('serpapi_pagination', {}).get('next'):
        raise ValueError('Google author list requires additional pagination')
    articles = google.get('articles', [])
    result = {}
    for paper in config['papers']:
        ga = uniquely_match(articles, paper['title'])
        sa = uniquely_match(batch, paper['title'])
        print(f"Collecting citing lists for {paper['id']}", flush=True)
        google_rows, google_count = google_citations(ga)
        expected = nonnegative(sa.get('citationCount'))
        semantic_rows = sa.get('citations')
        if not isinstance(semantic_rows, list):
            raise ValueError('Semantic Scholar paper has no citation list')
        if len(semantic_rows) != expected:
            pages = semantic_pages('paper/' + sa['paperId'] + '/citations', 'title,authors,year,externalIds,url')
            semantic_rows = [item['citingPaper'] for item in pages]
        semantic_rows = [semantic_record(item) for item in semantic_rows]
        if len(semantic_rows) != expected or len({r['ids']['semantic'] for r in semantic_rows}) != expected:
            raise ValueError('Semantic Scholar citing-list coverage differs from article count')
        result[paper['id']] = {
            'title': paper['title'], 'google_count': google_count, 'semantic_count': expected,
            'records': google_rows + semantic_rows,
        }
        print(f"Fetched {paper['id']}: Google {google_count}, Semantic {expected}")
    return result


def first_author_key(record):
    if not record['authors']:
        return ''
    words = re.findall(r'[^\W_]+', record['authors'][0], re.UNICODE)
    return normalized(words[-1]) if words else ''


def same_work(a, b):
    if any(a['ids'][key] == b['ids'].get(key) for key in a['ids']):
        return True
    if normalized(a['title']) != normalized(b['title']):
        return False
    author = first_author_key(a)
    if not author or not first_author_key(b):
        raise ValueError('Matching titles without author evidence need review: ' + a['title'])
    if author != first_author_key(b):
        return False
    if a['year'] and b['year'] and abs(a['year'] - b['year']) > 2:
        raise ValueError('Matching titles have conflicting years: ' + a['title'])
    return True


def union_groups(records):
    groups = []
    for record in records:
        matches = [group for group in groups if any(same_work(record, other) for other in group)]
        merged = [record]
        for group in matches:
            groups.remove(group)
            merged.extend(group)
        groups.append(merged)
    for group in groups:
        group.sort(key=lambda record: (record['source'], json.dumps(record['ids'], sort_keys=True)))
    return sorted(groups, key=lambda group: normalized(group[0]['title']))


def derive(papers):
    result = {}
    for paper_id, paper in papers.items():
        records = paper['records']
        for record in records:
            if record['source'] not in ('google', 'semantic') or not record['title'].strip() or not record['ids']:
                raise ValueError('Malformed citing record')
            if record['url'] and urlsplit(record['url']).scheme not in ('http', 'https'):
                raise ValueError('Invalid citing-paper URL')
        for source in ('google', 'semantic'):
            if sum(r['source'] == source for r in records) != nonnegative(paper[source + '_count']):
                raise ValueError('Source count differs from saved citing records')
        groups = union_groups(records)
        citations = []
        for group in groups:
            preferred = next((r for r in group if r['source'] == 'semantic'), group[0])
            citations.append({
                'title': preferred['title'], 'authors': preferred['authors'],
                'year': preferred['year'], 'url': preferred['url'],
                'sources': sorted({r['source'] for r in group}),
                'records': group,
            })
        result[paper_id] = {
            'title': paper['title'], 'google_count': paper['google_count'],
            'semantic_count': paper['semantic_count'], 'citations': citations,
            'count': len(citations),
        }
    counts = sorted((p['count'] for p in result.values()), reverse=True)
    return {
        'total_citations': sum(counts),
        'h_index': sum(count >= rank for rank, count in enumerate(counts, 1)),
        'papers': result,
    }


def validate(snapshot, config):
    dt.date.fromisoformat(snapshot['updated_at'])
    if snapshot['sources'] != {k: config[k] for k in ('google_author_id', 'semantic_author_id')}:
        raise ValueError('Snapshot source identity mismatch')
    papers = {}
    if set(snapshot['papers']) != {p['id'] for p in config['papers']}:
        raise ValueError('Snapshot must cover every configured publication')
    for paper in config['papers']:
        saved = snapshot['papers'][paper['id']]
        if saved['title'] != paper['title']:
            raise ValueError('Snapshot publication title mismatch')
        papers[paper['id']] = {
            **saved, 'records': [r for c in saved['citations'] for r in c['records']],
        }
    expected = derive(papers)
    if any(snapshot[key] != value for key, value in expected.items()):
        raise ValueError('Saved union or metrics cannot be reproduced from source records')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--output', type=Path, default=SNAPSHOT)
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    if args.check_only:
        validate(json.loads(args.output.read_text()), config)
        print('Combined citations verified from complete source records')
        return
    if not scholar_enabled(ROOT / '_data/features.json'):
        print('Scholar is disabled; skipping combined citation collection')
        return
    papers = fetch(config)
    snapshot = {
        'updated_at': dt.datetime.now(dt.timezone.utc).date().isoformat(),
        'sources': {k: config[k] for k in ('google_author_id', 'semantic_author_id')},
        **derive(papers),
    }
    validate(snapshot, config)
    atomic_write(args.output, json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n')
    print(f"Verified union: {snapshot['total_citations']} citations, h-index {snapshot['h_index']}")


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError) as error:
        raise SystemExit('Combined citation refresh failed; previous snapshot retained. ' + str(error)) from None
