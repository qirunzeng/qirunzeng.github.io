import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update_citation_union as union


def record(source, title='A Learning Algorithm', author='Qirun Zeng', year=2026, **ids):
    return {'source': source, 'title': title, 'authors': [author] if author else [],
            'year': year, 'url': 'https://example.org/paper',
            'ids': {source: source + title, **ids}}


class UnionTests(unittest.TestCase):
    def test_title_and_author_variations(self):
        a = record('google', 'A Learning Algorithm!', 'Q Zeng', 2025)
        b = record('semantic', 'A learning algorithm', 'Qi-Run Zeng')
        self.assertEqual(len(union.union_groups([a, b])), 1)

    def test_different_authors_stay_separate(self):
        self.assertEqual(len(union.union_groups([
            record('google'), record('semantic', author='J Smith')
        ])), 2)

    def test_shared_id_merges_renamed_versions(self):
        a = record('google', 'Original Title', arxiv='2605.12345')
        b = record('semantic', 'Revised Title', arxiv='2605.12345')
        self.assertEqual(len(union.union_groups([a, b])), 1)

    def test_transitive_aliases_are_order_independent(self):
        a = record('google', 'Old Title', arxiv='2605.12345')
        b = record('semantic', 'New Title', arxiv='2605.12345', doi='10.1234/paper')
        c = record('google', 'New Title', doi='10.1234/paper')
        self.assertEqual(union.union_groups([a, b, c]), union.union_groups([c, b, a]))

    def test_missing_authors_require_review(self):
        with self.assertRaises(ValueError):
            union.union_groups([record('google', author=''), record('semantic')])

    def test_conflicting_years_require_review(self):
        with self.assertRaises(ValueError):
            union.union_groups([record('google', year=1990), record('semantic')])

    def test_identifiers_merge_arxiv_pdf_and_doi(self):
        self.assertEqual(union.identifiers(['https://arxiv.org/pdf/2605.12345v2.pdf']), {'arxiv': '2605.12345'})
        self.assertEqual(union.identifiers([], {'DOI': '10.48550/arXiv.2605.12345'}), {'arxiv': '2605.12345'})

    def test_sum_edges_and_recompute_h_index(self):
        paper = {'title': 'Target', 'google_count': 1, 'semantic_count': 1,
                 'records': [record('google'), record('semantic')]}
        result = union.derive({'one': paper, 'two': paper})
        self.assertEqual(result['total_citations'], 2)
        self.assertEqual(result['h_index'], 1)
        self.assertEqual(result['papers']['one']['citations'][0]['sources'], ['google', 'semantic'])

    def test_reproducible_snapshot_and_tamper_detection(self):
        config = {'google_author_id': 'g', 'semantic_author_id': 's',
                  'papers': [{'id': 'one', 'title': 'Target'}]}
        result = union.derive({'one': {'title': 'Target', 'google_count': 1, 'semantic_count': 1,
                                      'records': [record('google'), record('semantic')]}})
        snapshot = {'updated_at': '2026-11-18', 'sources': {'google_author_id': 'g', 'semantic_author_id': 's'}, **result}
        union.validate(snapshot, config)
        snapshot['total_citations'] = 99
        with self.assertRaises(ValueError):
            union.validate(snapshot, config)

    def test_google_pagination_and_missing_results(self):
        article = {'cited_by': {'value': 2, 'cites_id': '123'}}
        item = {'title': 'A', 'result_id': 'a', 'publication_info': {'authors': [{'name': 'Q Zeng'}]}}
        pages = [
            {'organic_results': [item], 'serpapi_pagination': {'next': 'https://serpapi.com/search.json?start=20'}},
            {'organic_results': [{**item, 'title': 'B', 'result_id': 'b'}]},
        ]
        with patch.object(union, 'serpapi', side_effect=pages):
            self.assertEqual(len(union.google_citations(article)[0]), 2)
        with patch.object(union, 'serpapi', return_value={'organic_results': [item]}):
            with self.assertRaises(ValueError):
                union.google_citations(article)

    def test_google_nullable_metadata(self):
        item = {'title': 'Paper', 'result_id': '123', 'link': None, 'resources': None,
                'publication_info': {'summary': None, 'authors': None}}
        result = union.google_record(item)
        self.assertEqual(result['authors'], [])
        self.assertIsNone(result['year'])

    def test_semantic_pagination(self):
        with patch.object(union.time, 'sleep'), patch.object(union, 'request_json', side_effect=[
            {'data': [1], 'next': 1}, {'data': [2]},
        ]):
            self.assertEqual(union.semantic_pages('test', 'title'), [1, 2])

    def test_partial_failure_does_not_overwrite_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'snapshot.json'
            path.write_text('old verified snapshot')
            with patch.object(sys, 'argv', ['fetch', '--output', str(path)]), \
                 patch.object(union, 'fetch', side_effect=ValueError('missing page')), \
                 patch.object(union, 'scholar_enabled', return_value=True):
                with self.assertRaises(ValueError):
                    union.main()
            self.assertEqual(path.read_text(), 'old verified snapshot')

    def test_scholar_switch_skips_all_network_calls(self):
        with patch.object(sys, 'argv', ['fetch']), patch.object(union, 'scholar_enabled', return_value=False), \
             patch.object(union, 'fetch') as fetch:
            union.main()
            fetch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
