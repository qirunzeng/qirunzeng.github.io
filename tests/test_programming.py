import copy
from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.update_programming import (
    Fetcher, account, combine, leetcode_account, luogu_context, luogu_topics, solve_counts,
)
from scripts import update_programming as updater


class ProgrammingTests(unittest.TestCase):
    def test_leetcode_uses_each_cn_graphql_schema_for_its_supported_fields(self):
        profile = {'data': {'userProfilePublicProfile': {'profile': {'userSlug': 'qirunzeng'}},
                            'userProfileUserQuestionProgressV2': {'numAcceptedQuestions': [
                                {'difficulty': 'EASY', 'count': 1}, {'difficulty': 'MEDIUM', 'count': 1}]}}}
        contest = {'data': {'userContestRanking': {'rating': 1920, 'globalRanking': 100, 'topPercentage': 5.87},
                            'userLanguageProblemCount': [{'languageName': 'C++', 'problemsSolved': 2},
                                                         {'languageName': 'Python3', 'problemsSolved': 1}]}}
        fetcher = Fetcher()
        with patch.object(fetcher, 'read', side_effect=[profile, contest]) as read:
            result = fetcher.leetcode()
        self.assertEqual(result['solved'], 2)
        self.assertEqual(result['verification'], 'public-api')
        self.assertEqual(read.call_args_list[0].args[1], 'https://leetcode.cn/graphql/')
        self.assertEqual(read.call_args_list[1].args[1], 'https://leetcode.cn/graphql/noj-go/')

    def test_atcoder_rated_count_ignores_unrated_history_and_tooltip_markup(self):
        html = ('<title>qirunzeng - AtCoder</title><table>'
                '<th>Rating</th><td><span>1000</span></td>'
                '<th>Highest Rating</th><td>1100</td>'
                '<th>Rated Matches <span class="tooltip"></span></th><td>2</td></table>')
        history = [dict(IsRated=True, NewRating=1100), dict(IsRated=False, NewRating=5000),
                   dict(IsRated=True, NewRating=1000)]
        subs = [dict(user_id='qirunzeng', problem_id='abc_a', language='C++ 20', result='AC')]
        fetcher = Fetcher()
        with patch.object(fetcher, 'read', side_effect=[html, history, subs]):
            result = fetcher.atcoder()
        self.assertEqual(result['rating'], 1000)
        self.assertEqual(result['metrics'][1]['value'], 1100)
        self.assertEqual(result['metrics'][3]['value'], 2)

    def accounts(self):
        return [account(provider, 1000, 1100, 2, 1,
                        [{'name': 'C++', 'count': 2}],
                        [{'name': 'Math', 'count': 2}])
                for provider in ('codeforces', 'atcoder', 'leetcode', 'luogu')]

    def test_accounts_are_not_deduplicated_by_shared_handle(self):
        combined = combine(self.accounts())
        self.assertEqual(combined['solved'], 8)
        self.assertEqual(len(combined['accounts']), 4)
        self.assertEqual(combined['languages'], [{'name': 'C++', 'count': 8}])

    def test_missing_categories_are_explicit_not_zero(self):
        accounts = self.accounts()
        accounts[1]['topics'] = None
        accounts[3]['languages'] = None
        combined = combine(accounts)
        self.assertIn({'name': 'Unclassified', 'count': 2}, combined['topics'])
        self.assertIn({'name': 'Not public', 'count': 2}, combined['languages'])

    def test_duplicate_platforms_are_rejected(self):
        accounts = self.accounts()
        accounts[-1] = copy.deepcopy(accounts[0])
        with self.assertRaises(ValueError):
            combine(accounts)

    def test_wrong_profile_is_rejected(self):
        accounts = self.accounts()
        accounts[2]['profile_url'] = 'https://leetcode.com/u/qirunzeng/'
        with self.assertRaises(ValueError):
            combine(accounts)

    def test_displayed_metrics_cannot_disagree_with_counts(self):
        accounts = self.accounts()
        accounts[0]['metrics'][2]['value'] = 999
        with self.assertRaises(ValueError):
            combine(accounts)

    def test_failed_source_preserves_its_verified_date(self):
        original = self.accounts()
        original[2]['updated_at'] = '2020-01-01T00:00:00Z'
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            path = root/'_data/programming.json'
            path.parent.mkdir()
            path.write_text(json.dumps(combine(original)))
            stack.enter_context(patch.object(updater, 'ROOT', root))
            stack.enter_context(patch('sys.argv', ['update_programming.py']))
            stack.enter_context(redirect_stdout(io.StringIO()))
            for i, provider in enumerate(updater.ORDER):
                if provider == 'leetcode':
                    stack.enter_context(patch.object(updater.Fetcher, provider, side_effect=ValueError('blocked')))
                else:
                    stack.enter_context(patch.object(updater.Fetcher, provider, return_value=original[i]))
            updater.main()
            saved = json.loads(path.read_text())
            self.assertEqual(saved['accounts'][2], original[2])
            self.assertEqual(saved['solved'], 8)

    def test_total_failure_leaves_snapshot_unchanged(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            path = root/'_data/programming.json'
            path.parent.mkdir()
            before = json.dumps(combine(self.accounts()))
            path.write_text(before)
            stack.enter_context(patch.object(updater, 'ROOT', root))
            stack.enter_context(patch('sys.argv', ['update_programming.py']))
            stack.enter_context(redirect_stdout(io.StringIO()))
            for provider in updater.ORDER:
                stack.enter_context(patch.object(updater.Fetcher, provider, side_effect=ValueError('blocked')))
            with self.assertRaises(RuntimeError):
                updater.main()
            self.assertEqual(path.read_text(), before)

    def test_incomplete_language_coverage_is_rejected(self):
        accounts = self.accounts()
        accounts[0]['languages'][0]['count'] = 1
        with self.assertRaises(ValueError):
            combine(accounts)

    def test_multiple_languages_can_cover_one_problem(self):
        records = [dict(problem=dict(contestId=1, index='A'), verdict='OK', programmingLanguage=lang)
                   for lang in ('C++17', 'GNU C++20', 'Python 3', 'PyPy 3')]
        solved, languages = solve_counts(records, 'codeforces')
        self.assertEqual(solved, 1)
        self.assertEqual(languages, [{'name': 'C++', 'count': 1}, {'name': 'Python', 'count': 1}])

    def test_failed_submissions_do_not_count(self):
        records = [dict(problem=dict(contestId=1, index='A'), verdict='WRONG_ANSWER', programmingLanguage='C++17')]
        self.assertEqual(solve_counts(records, 'codeforces'), (0, []))

    def test_atcoder_identity_and_repeated_solves(self):
        records = [dict(user_id='qirunzeng', problem_id='abc_a', language='C++ 20 (gcc)', result='AC')]*2
        self.assertEqual(solve_counts(records, 'atcoder'), (1, [{'name': 'C++', 'count': 1}]))
        records[0] = dict(records[0], user_id='someone-else')
        with self.assertRaises(ValueError):
            solve_counts(records, 'atcoder')

    def test_topic_parent_mapping_ignores_origin_and_year(self):
        tags = [dict(id=3, name='动态规划 DP', type=2, parent=None),
                dict(id=8, name='子集', type=2, parent=3),
                dict(id=9, name='2026', type=4, parent=None)]
        problems = [dict(tags=[3, 8, 9]), dict(tags=[9])]
        self.assertEqual(luogu_topics(problems, tags),
                         [{'name': 'Dynamic programming', 'count': 1},
                          {'name': 'Unclassified', 'count': 1}])

    def test_wrong_luogu_user_is_rejected(self):
        html = '<script id="lentille-context">{"status":200,"template":"user.show","data":{"user":{"uid":1,"name":"qirunzeng"}}}</script>'
        with self.assertRaises(ValueError):
            luogu_context(html, 'user.show')

    def test_peak_cannot_be_lower_than_current_rating(self):
        with self.assertRaises(ValueError):
            account('atcoder', 1000, 900, 0, 1, [], [])

    def test_leetcode_language_counts_can_overlap(self):
        data = dict(user_slug='qirunzeng', rating=1920.2, solved=2, global_rank=100,
                    top_percent=5.87, languages=[dict(name='C++', count=2), dict(name='Python3', count=1)])
        result = leetcode_account(data)
        self.assertEqual(result['rating'], 1920)
        self.assertEqual(sum(r['count'] for r in result['languages']), 3)
        self.assertIsNone(result['topics'])

    def test_nonfinite_rating_is_rejected(self):
        data = dict(user_slug='qirunzeng', rating=float('nan'), solved=0, global_rank=1, top_percent=1, languages=[])
        with self.assertRaises(ValueError):
            leetcode_account(data)
