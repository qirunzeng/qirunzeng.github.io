from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "update_scholar", ROOT / "scripts" / "update_scholar.py"
)
assert SPEC and SPEC.loader
scholar = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scholar
SPEC.loader.exec_module(scholar)


class ScholarUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = scholar.ScholarConfig(
            source_url="https://scholar.google.com/citations?user=sITttdEAAAAJ&hl=en",
            expected_name="Qirun Zeng",
            identity_publication="Fusing Reward and Dueling Feedback in Stochastic Bandits",
        )

    def test_parses_profile_identity_and_all_time_metrics(self) -> None:
        html = (ROOT / "tests" / "fixtures" / "scholar_profile.html").read_text()
        snapshot = scholar.parse_scholar_html(html)
        self.assertEqual(snapshot.name, "Qirun Zeng")
        self.assertEqual(
            snapshot.metrics,
            {"total_citations": 1234, "h_index": 12, "i10_index": 34},
        )

    def test_rejects_captcha_instead_of_using_stale_values(self) -> None:
        with self.assertRaisesRegex(scholar.ScholarError, "CAPTCHA"):
            scholar.parse_scholar_html("<html>Our systems have detected unusual traffic</html>")

    def test_rejects_wrong_profile(self) -> None:
        snapshot = scholar.ScholarSnapshot(
            name="Someone Else",
            metrics={"total_citations": 6, "h_index": 1, "i10_index": 0},
            provider="test",
        )
        with self.assertRaisesRegex(scholar.ScholarError, "identity mismatch"):
            scholar.validate_snapshot(
                snapshot,
                self.config,
                {"total_citations": 6, "h_index": 1, "i10_index": 0},
            )

    def test_rejects_metric_decrease_without_manual_override(self) -> None:
        snapshot = scholar.ScholarSnapshot(
            name="Qirun Zeng",
            metrics={"total_citations": 5, "h_index": 1, "i10_index": 0},
            provider="test",
        )
        existing = {"total_citations": 6, "h_index": 1, "i10_index": 0}
        with self.assertRaisesRegex(scholar.ScholarError, "decreased unexpectedly"):
            scholar.validate_snapshot(snapshot, self.config, existing)
        scholar.validate_snapshot(snapshot, self.config, existing, allow_decrease=True)

    def test_atomic_write_does_not_rewrite_identical_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "scholar.yml"
            path.write_text("value: 1\n")
            self.assertFalse(scholar.atomic_write(path, "value: 1\n"))
            self.assertTrue(scholar.atomic_write(path, "value: 2\n"))
            self.assertEqual(path.read_text(), "value: 2\n")

    def test_derives_indices_from_validated_mirror_publications(self) -> None:
        payload = {
            "total_citations": 21,
            "publications": [
                {
                    "title": "Fusing reward and dueling feedback in stochastic bandits",
                    "citations": 12,
                },
                {"title": "Another paper", "citations": 7},
                {"title": "Third paper", "citations": 2},
            ],
        }
        snapshot = scholar.parse_bth_payload(
            payload,
            expected_name=self.config.expected_name,
            identity_publication=self.config.identity_publication,
        )
        self.assertEqual(
            snapshot.metrics,
            {"total_citations": 21, "h_index": 2, "i10_index": 1},
        )

    def test_rejects_mirror_response_for_another_profile(self) -> None:
        payload = {
            "total_citations": 50,
            "publications": [{"title": "Unrelated paper", "citations": 50}],
        }
        with self.assertRaisesRegex(scholar.ScholarError, "identity check failed"):
            scholar.parse_bth_payload(
                payload,
                expected_name=self.config.expected_name,
                identity_publication=self.config.identity_publication,
            )


if __name__ == "__main__":
    unittest.main()
