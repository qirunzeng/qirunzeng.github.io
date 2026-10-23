#!/usr/bin/env python3
"""Build a small, verified Codeforces snapshot; no browser API requests needed."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
HANDLE = 'rewinery'


def api(method, **params):
    url = 'https://codeforces.com/api/' + method + '?' + urlencode(params)
    with urlopen(url, timeout=45) as response:
        payload = json.load(response)
    if payload.get('status') != 'OK':
        raise ValueError('Codeforces API failed: ' + str(payload.get('comment')))
    return payload['result']


def language_family(language):
    name = language.strip()
    if re.match(r'^(?:GNU\s+)?C\+\+', name, re.IGNORECASE):
        return 'C++'
    if re.match(r'^(?:Python|PyPy)(?=\s|\d|$)', name, re.IGNORECASE):
        return 'Python'
    return name


def aggregate(profile, submissions, ratings):
    if profile['handle'].casefold() != HANDLE:
        raise ValueError('Unexpected Codeforces identity')
    solved = {}
    languages = Counter()
    accepted = 0
    for submission in submissions:
        if submission.get('verdict') != 'OK':
            continue
        problem = submission['problem']
        # API identifies contest problems by contestId + index (not title).
        key = (problem.get('contestId', problem.get('problemsetName')), problem['index'])
        if key[0] is None:
            raise ValueError('Problem has no stable identity')
        solved[key] = problem
        languages[language_family(submission['programmingLanguage'])] += 1
        accepted += 1
    tags = Counter(tag for problem in solved.values() for tag in set(problem['tags']))
    def rows(counter):
        return [{'name': name, 'count': count} for name, count in sorted(counter.items(), key=lambda pair: (-pair[1], pair[0]))]
    for key in ('rating', 'maxRating'):
        if not isinstance(profile.get(key), int) or profile[key] < 0:
            raise ValueError('Invalid profile rating')
    if ratings and ratings[-1]['newRating'] != profile['rating']:
        raise ValueError('Profile and rating history disagree; retry later')
    return {
        'handle': HANDLE, 'profile_url': 'https://codeforces.com/profile/' + HANDLE,
        'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'rating': profile['rating'], 'max_rating': profile['maxRating'],
        'rank': profile['rank'], 'max_rank': profile['maxRank'],
        'solved': len(solved), 'accepted_submissions': accepted,
        'rated_contests': len(ratings), 'tags': rows(tags), 'languages': rows(languages),
        'rating_history': [{'contest': r['contestName'], 'rating': r['newRating'],
                            'timestamp': r['ratingUpdateTimeSeconds']} for r in ratings],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-dir', type=Path, help='Read previously downloaded official API responses')
    args = parser.parse_args()
    if args.fixture_dir:
        def read(name):
            payload = json.loads((args.fixture_dir / ('cf-' + name + '.json')).read_text())
            if payload['status'] != 'OK':
                raise ValueError('Invalid API response')
            return payload['result']
        profile, submissions, ratings = read('info')[0], read('status'), read('rating')
    else:
        profile = api('user.info', handles=HANDLE)[0]
        submissions = []
        page_size = 1000
        while True:
            time.sleep(2.1)
            page = api('user.status', handle=HANDLE, **{'from': len(submissions) + 1, 'count': page_size})
            submissions.extend(page)
            if len(page) < page_size:
                break
        time.sleep(2.1)
        ratings = api('user.rating', handle=HANDLE)
    snapshot = aggregate(profile, submissions, ratings)
    # Fail before replacing the last good snapshot on malformed or partial data.
    output = ROOT / '_data/codeforces.json'
    if output.exists():
        old = json.loads(output.read_text())
        if snapshot['solved'] < old['solved']:
            raise ValueError('Solved count decreased; inspect upstream data before replacing snapshot')
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(output)
    print(f"Codeforces: {snapshot['solved']} unique problems, {snapshot['rated_contests']} rated contests")


if __name__ == '__main__':
    main()
