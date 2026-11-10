#!/usr/bin/env python3
"""Verify four public programming profiles and combine comparable solve counts."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

if __package__:
    from .update_codeforces import language_family
else:
    from update_codeforces import language_family

ROOT = Path(__file__).resolve().parents[1]
ORDER = ('codeforces', 'atcoder', 'leetcode', 'luogu')
IDENTITIES = {
    'codeforces': ('Codeforces', 'rewinery', 'https://codeforces.com/profile/rewinery'),
    'atcoder': ('AtCoder', 'qirunzeng', 'https://atcoder.jp/users/qirunzeng'),
    'leetcode': ('LeetCode', 'qirunzeng', 'https://leetcode.cn/u/qirunzeng/'),
    'luogu': ('Luogu', 'qirunzeng', 'https://www.luogu.com.cn/user/727702'),
}
TOPICS = {
    'dp': 'Dynamic programming', '动态规划': 'Dynamic programming',
    'greedy': 'Greedy', '贪心': 'Greedy', 'math': 'Math', '数学': 'Math',
    'number theory': 'Number theory', '数论': 'Number theory',
    'combinatorics': 'Combinatorics', '组合': 'Combinatorics',
    'geometry': 'Geometry', '几何': 'Geometry', 'graphs': 'Graphs', '图论': 'Graphs',
    'data structures': 'Data structures', '数据结构': 'Data structures',
    'strings': 'Strings', '字符串': 'Strings', 'binary search': 'Binary search', '二分': 'Binary search',
    'sortings': 'Sorting', '排序': 'Sorting', 'brute force': 'Brute force', '枚举': 'Brute force',
    'implementation': 'Simulation', '模拟': 'Simulation', '搜索': 'Search',
    'games': 'Game theory', '博弈': 'Game theory', 'trees': 'Trees', '树': 'Trees',
    'dfs and similar': 'Search', 'shortest paths': 'Graphs', 'graph matchings': 'Graphs',
    'dsu': 'Data structures', 'two pointers': 'Two pointers', 'bitmasks': 'Bitmasks',
    'divide and conquer': 'Divide and conquer', 'hashing': 'Hashing',
    'probabilities': 'Probability', 'ternary search': 'Search', 'interactive': 'Interactive',
    'constructive algorithms': 'Constructive algorithms', 'schedules': 'Scheduling',
}


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def integer(value, label):
    if type(value) is not int or value < 0:
        raise ValueError('Invalid ' + label)
    return value


def rows(counter):
    return [{'name': k, 'count': v} for k, v in sorted(counter.items(), key=lambda p: (-p[1], p[0])) if v]


def topic_name(name):
    name = name.strip()
    if name.casefold() in TOPICS:
        return TOPICS[name.casefold()]
    for key, label in TOPICS.items():
        if any(ord(c) > 127 for c in key) and key in name:
            return label
    return None


def solve_counts(submissions, provider):
    """A problem counts once per account and once per language family used."""
    solved = set()
    pairs = set()
    for record in submissions:
        if provider == 'codeforces':
            if record.get('verdict') != 'OK':
                continue
            problem = record['problem']
            key = (problem.get('contestId', problem.get('problemsetName')), problem['index'])
            if key[0] is None:
                raise ValueError('Missing Codeforces problem identity')
            language = record['programmingLanguage']
        else:
            if record.get('user_id') != 'qirunzeng':
                raise ValueError('Unexpected AtCoder submission identity')
            if record.get('result') != 'AC':
                continue
            key, language = record['problem_id'], record['language']
        if not language.strip():
            raise ValueError('Empty language')
        solved.add(key)
        pairs.add((key, language_family(language)))
    return len(solved), rows(Counter(language for _, language in pairs))


def account(provider, rating, peak, solved, contests, languages, topics):
    name, handle, url = IDENTITIES[provider]
    result = dict(id=provider, name=name, handle=handle, profile_url=url, updated_at=now(),
                  rating=integer(rating, 'rating'), solved=integer(solved, 'solved'),
                  languages=languages, topics=topics)
    result['metrics'] = [{'label': 'Rating', 'value': rating}]
    if peak is not None:
        if peak < rating:
            raise ValueError('Peak rating is below current rating')
        result['metrics'].append({'label': 'Peak rating', 'value': integer(peak, 'peak rating')})
    result['metrics'].append({'label': 'Problems solved', 'value': solved})
    if contests is not None:
        result['metrics'].append({'label': 'Rated contests', 'value': integer(contests, 'contest count')})
    return result


class ContextParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.active = False
        self.parts = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('id') == 'lentille-context':
            self.active = True

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == 'script':
            self.active = False


def luogu_context(html, template):
    data = json.loads(''.join(ContextParser(html).parts))
    if data.get('status') != 200 or data.get('template') != template:
        raise ValueError('Unexpected Luogu response')
    user = data['data']['user']
    if user.get('uid') != 727702 or user.get('name') != 'qirunzeng':
        raise ValueError('Unexpected Luogu identity')
    return data['data']


def luogu_topics(problems, tags):
    algorithm_tags = {tag['id']: tag for tag in tags if tag.get('type') == 2}
    counts = Counter()
    for problem in problems:
        names = set()
        for tag_id in problem['tags']:
            if tag_id not in algorithm_tags:
                continue
            current, visited = algorithm_tags[tag_id], set()
            label = topic_name(current['name'])
            while label is None and current.get('parent') in algorithm_tags:
                if current['id'] in visited:
                    raise ValueError('Cyclic Luogu tag hierarchy')
                visited.add(current['id'])
                current = algorithm_tags[current['parent']]
                label = topic_name(current['name'])
            names.add(label or 'Other algorithms')
        counts.update(names or ['Unclassified'])
    return rows(counts)


def leetcode_account(public):
    if public.get('user_slug') != 'qirunzeng':
        raise ValueError('Unexpected LeetCode identity')
    rating = public['rating']
    if type(rating) not in (int, float) or not math.isfinite(rating) or rating < 0:
        raise ValueError('Invalid LeetCode rating')
    languages = Counter()
    for row in public['languages']:
        languages[language_family(row['name'])] += integer(row['count'], 'language count')
    solved = integer(public['solved'], 'solved')
    if sum(languages.values()) < solved:
        raise ValueError('Incomplete LeetCode language distribution')
    result = account('leetcode', int(rating + .5), None, solved, None, rows(languages), None)
    rank = integer(public['global_rank'], 'contest rank')
    top = public['top_percent']
    if type(top) not in (int, float) or not math.isfinite(top) or not 0 < top <= 100:
        raise ValueError('Invalid LeetCode percentile')
    result['metrics'].extend([{'label': 'Global contest rank', 'value': rank},
                              {'label': 'Top percentile', 'value': f'{top:.2f}%'}])
    result['verification'] = public.get('verification', 'public-api')
    return result


def combine(accounts):
    by_id = {a['id']: a for a in accounts}
    if len(accounts) != len(ORDER) or set(by_id) != set(ORDER):
        raise ValueError('Expected exactly four distinct accounts')
    tags, languages = Counter(), Counter()
    for provider in ORDER:
        a = by_id[provider]
        expected = IDENTITIES[provider]
        if (a['name'], a['handle'], a['profile_url']) != expected:
            raise ValueError('Account identity mismatch')
        solved = integer(a['solved'], 'solved')
        integer(a['rating'], 'rating')
        metrics = {m['label']: m['value'] for m in a['metrics']}
        if len(metrics) != len(a['metrics']) or metrics.get('Rating') != a['rating'] or metrics.get('Problems solved') != solved:
            raise ValueError('Displayed metrics disagree with account values')
        if 'Peak rating' in metrics and integer(metrics['Peak rating'], 'peak rating') < a['rating']:
            raise ValueError('Peak rating below current rating')
        datetime.strptime(a['updated_at'], '%Y-%m-%dT%H:%M:%SZ')
        for key, target, missing in [('topics', tags, 'Unclassified'), ('languages', languages, 'Not public')]:
            data = a[key]
            if data is None:
                target[missing] += solved
                continue
            if not isinstance(data, list) or len({r['name'] for r in data}) != len(data):
                raise ValueError('Invalid or duplicate categories')
            for row in data:
                count = integer(row['count'], 'category count')
                if not row['name'] or count > solved:
                    raise ValueError('Invalid category coverage')
                target[row['name']] += count
            if sum(r['count'] for r in data) < solved:
                raise ValueError('Incomplete category coverage')
    ordered = [by_id[key] for key in ORDER]
    return {'accounts': ordered, 'solved': sum(a['solved'] for a in ordered),
            'topics': rows(tags), 'languages': rows(languages)}


class Fetcher:
    def __init__(self, fixtures=None):
        self.fixtures = fixtures

    def read(self, name, url, json_data=True, body=None):
        if self.fixtures:
            raw = (self.fixtures / name).read_text()
        else:
            headers = {'User-Agent': 'qirunzeng.github.io programming statistics updater'}
            if body is not None:
                headers.update({'Content-Type': 'application/json', 'Referer': IDENTITIES['leetcode'][2]})
                body = json.dumps(body).encode()
            try:
                with urlopen(Request(url, data=body, headers=headers), timeout=45) as response:
                    raw = response.read().decode('utf-8')
            except HTTPError as exc:
                if body is not None and exc.code in (400, 422):
                    try:
                        errors = json.loads(exc.read(16384)).get('errors', [])
                        messages = [str(e.get('message', ''))[:300] for e in errors[:4]]
                    except (ValueError, AttributeError, TypeError):
                        messages = []
                    if messages:
                        raise ValueError('LeetCode query rejected: '+'; '.join(messages)) from exc
                raise
        return json.loads(raw) if json_data else raw

    def codeforces(self):
        cf = json.loads((ROOT / '_data/codeforces.json').read_text())
        if cf['handle'] != 'rewinery':
            raise ValueError('Unexpected Codeforces snapshot')
        submissions = []
        while True:
            query = urlencode({'handle': 'rewinery', 'from': len(submissions)+1, 'count': 1000})
            data = self.read('cf-status.txt', 'https://codeforces.com/api/user.status?'+query)
            if data.get('status') != 'OK':
                raise ValueError('Codeforces API error')
            page = data['result']; submissions.extend(page)
            if len(page) < 1000:
                break
            if self.fixtures:
                raise ValueError('Fixture lacks pagination')
            time.sleep(2.1)
        solved, languages = solve_counts(submissions, 'codeforces')
        if solved != cf['solved']:
            raise ValueError('Codeforces snapshot and submissions disagree')
        unique = {}
        for sub in submissions:
            if sub.get('verdict') == 'OK':
                p = sub['problem']; unique[(p.get('contestId', p.get('problemsetName')), p['index'])] = p
        counts = Counter()
        for p in unique.values():
            counts.update({topic_name(t) or t.capitalize() for t in p['tags']} or ['Unclassified'])
        result = account('codeforces', cf['rating'], cf['max_rating'], solved, cf['rated_contests'], languages, rows(counts))
        result['updated_at'] = cf['updated_at']
        return result

    def atcoder(self):
        html = self.read('atcoder-profile.html', IDENTITIES['atcoder'][2]+'?lang=en', False)
        if not re.search(r'<title>\s*qirunzeng - AtCoder\s*</title>', html):
            raise ValueError('Unexpected AtCoder profile')
        history = self.read('atcoder-history.json', IDENTITIES['atcoder'][2]+'/history/json')
        if any(type(r.get('IsRated')) is not bool for r in history):
            raise ValueError('Invalid AtCoder rated flag')
        rated = [r for r in history if r['IsRated']]
        if not rated:
            raise ValueError('AtCoder rated history missing')
        cells = {re.sub(r'<[^>]*>', '', label).strip(): value
                 for label, value in re.findall(r'<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>', html, re.S)}
        for label, expected in [('Rating', rated[-1]['NewRating']),
                                ('Highest Rating', max(r['NewRating'] for r in rated)),
                                ('Rated Matches', len(rated))]:
            if label not in cells:
                raise ValueError('AtCoder profile statistic missing: '+label)
            text = re.sub(r'<[^>]*>', '', cells[label])
            number = re.search(r'\d[\d,]*', text)
            if not number or int(number.group().replace(',', '')) != expected:
                raise ValueError('AtCoder profile and history disagree')
        submissions, since = [], 0
        while True:
            url='https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions?'+urlencode({'user':'qirunzeng','from_second':since})
            data = self.read('atcoder-submissions.txt', url)
            submissions.extend(data)
            if len(data) < 500:
                break
            if self.fixtures:
                raise ValueError('Fixture lacks pagination')
            next_since = max(r['epoch_second'] for r in data)
            if next_since <= since:
                raise ValueError('AtCoder submission pagination stalled')
            since = next_since
            time.sleep(1.1)
        solved, languages = solve_counts(submissions, 'atcoder')
        return account('atcoder', rated[-1]['NewRating'], max(r['NewRating'] for r in rated), solved, len(rated), languages, None)

    def leetcode(self):
        if self.fixtures:
            return leetcode_account(self.read('leetcode-ui.json', ''))
        profile_query = '''query($userSlug: String!) {
          userProfilePublicProfile(userSlug: $userSlug) { profile { userSlug } }
          userProfileUserQuestionProgressV2(userSlug: $userSlug) { numAcceptedQuestions { difficulty count } }
        }'''
        contest_query = '''query($userSlug: String!) {
          userContestRanking(userSlug: $userSlug) { rating globalRanking topPercentage }
          userLanguageProblemCount(userSlug: $userSlug) { languageName problemsSolved }
        }'''
        variables = {'userSlug': 'qirunzeng'}
        # LeetCode CN's own client uses distinct schemas for these query groups.
        profile_payload = self.read('', 'https://leetcode.cn/graphql/', body={'query': profile_query, 'variables': variables})
        contest_payload = self.read('', 'https://leetcode.cn/graphql/noj-go/', body={'query': contest_query, 'variables': variables})
        if profile_payload.get('errors') or contest_payload.get('errors'):
            raise ValueError('LeetCode GraphQL errors')
        profile = profile_payload['data']
        data = contest_payload['data']; ranking = data['userContestRanking']
        accepted = profile['userProfileUserQuestionProgressV2']['numAcceptedQuestions']
        by_difficulty = {r['difficulty'].casefold(): integer(r['count'], 'accepted count') for r in accepted}
        solved = by_difficulty['all'] if 'all' in by_difficulty else sum(by_difficulty.values())
        return leetcode_account({'user_slug': profile['userProfilePublicProfile']['profile']['userSlug'],
            'rating': ranking['rating'], 'global_rank': ranking['globalRanking'], 'top_percent': ranking['topPercentage'],
            'solved': solved, 'languages': [{'name': r['languageName'], 'count': r['problemsSolved']} for r in data['userLanguageProblemCount']]})

    def luogu(self):
        profile = luogu_context(self.read('luogu-profile.txt', IDENTITIES['luogu'][2], False), 'user.show')
        practice = luogu_context(self.read('luogu-practice-full.html', IDENTITIES['luogu'][2]+'/practice', False), 'user.show')
        passed = practice['passed']
        if len({p['pid'] for p in passed}) != profile['user']['passedProblemCount']:
            raise ValueError('Incomplete Luogu solved list')
        tag_data = self.read('luogu-tags.txt', 'https://www.luogu.com.cn/_lfe/tags')
        problems = []
        for item in passed:
            pid = item['pid']
            if self.fixtures:
                p = json.loads((self.fixtures/'luogu-problem-cache'/(pid+'.json')).read_text())
            else:
                time.sleep(1.1)
                html = self.read('', 'https://www.luogu.com.cn/problem/'+pid, False)
                payload = json.loads(''.join(ContextParser(html).parts))
                if payload.get('status') != 200:
                    raise ValueError('Luogu problem unavailable')
                p = payload['data']['problem']
            if p['pid'] != pid:
                raise ValueError('Wrong Luogu problem identity')
            problems.append(p)
        elo = practice['elo']
        if not profile['elo'] or not elo:
            raise ValueError('Luogu rating history missing')
        current = profile['elo'][0]['rating']
        if elo[0]['rating'] != current or len(elo) != len(profile['elo']):
            raise ValueError('Luogu profile/history disagreement')
        return account('luogu', current, max(r['rating'] for r in elo), len(passed), len(elo), None, luogu_topics(problems, tag_data['tags']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--only', choices=ORDER, help='Refresh one account, retaining other snapshots')
    args = parser.parse_args()
    path = ROOT/'_data/programming.json'
    old = json.loads(path.read_text()) if path.exists() else {'accounts': []}
    if args.check_only:
        if combine(old['accounts']) != old:
            raise ValueError('Combined programming charts do not match account snapshots')
        print('Programming snapshot verified: four identities and chart totals')
        return
    accounts = {a['id']: a for a in old['accounts']}
    fetcher = Fetcher(args.fixtures)
    refreshed = []
    for provider in ([args.only] if args.only else ORDER):
        try:
            result = getattr(fetcher, provider)()
            if provider in accounts and result['solved'] < accounts[provider]['solved']:
                raise ValueError('Solved count decreased; inspect source before replacing')
            accounts[provider] = result
            refreshed.append(provider)
            print(f"{result['name']}: rating {result['rating']}, {result['solved']} solved", flush=True)
        except Exception as exc:
            if provider not in accounts:
                raise RuntimeError('No verified snapshot for '+provider) from exc
            print(f'::warning::{provider}: keeping snapshot from {accounts[provider]["updated_at"]}; {type(exc).__name__}: {exc}', flush=True)
    if not refreshed:
        raise RuntimeError('No programming sources refreshed')
    snapshot = combine(list(accounts.values()))
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False)+'\n')
    temporary.replace(path)
    print(f"Combined: {snapshot['solved']} platform solves across four accounts")


if __name__ == '__main__':
    main()
