import unittest
from scripts.update_codeforces import aggregate


class AggregationTests(unittest.TestCase):
    def setUp(self):
        self.profile = dict(handle='rewinery', rating=1630, maxRating=1648, rank='expert', maxRank='expert')

    def submission(self, contest=1, index='A', verdict='OK', language='C++17'):
        return dict(problem=dict(contestId=contest, index=index, tags=['math', 'dp']), verdict=verdict, programmingLanguage=language)

    def test_repeat_solves_and_failed_attempts(self):
        data = aggregate(self.profile, [self.submission(), self.submission(language='Python 3'), self.submission(index='B', verdict='WRONG_ANSWER'), self.submission(contest=2)], [])
        self.assertEqual(data['solved'], 2)
        self.assertEqual(data['accepted_submissions'], 3)
        self.assertEqual(data['tags'], [{'name': 'dp', 'count': 2}, {'name': 'math', 'count': 2}])
        self.assertEqual(sum(row['count'] for row in data['languages']), 3)

    def test_wrong_identity_rejected(self):
        self.profile['handle'] = 'someone-else'
        with self.assertRaises(ValueError):
            aggregate(self.profile, [], [])

    def test_inconsistent_rating_rejected(self):
        with self.assertRaises(ValueError):
            aggregate(self.profile, [], [dict(newRating=1600)])

    def test_missing_problem_identity_rejected(self):
        submission = self.submission()
        del submission['problem']['contestId']
        with self.assertRaises(ValueError):
            aggregate(self.profile, [submission], [])
