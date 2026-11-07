from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "update_scholar", ROOT / "scripts" / "update_scholar.py"
)
assert SPEC and SPEC.loader
scholar = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scholar
SPEC.loader.exec_module(scholar)


class ScholarSwitchTests(unittest.TestCase):
    def test_recovery_window_skips_successful_day_but_retries_stale_day(self):
        with tempfile.TemporaryDirectory() as directory:
            features = pathlib.Path(directory) / "features.json"
            data = pathlib.Path(directory) / "scholar.yml"
            features.write_text('{"scholar_enabled": true}')
            today = scholar.dt.datetime.now(scholar.dt.timezone.utc).date()
            for day, expected in ((today, "false"), (today - scholar.dt.timedelta(days=1), "true")):
                data.write_text(f'last_checked_at: "{day.isoformat()}"\n')
                with self.subTest(day=day), contextlib.redirect_stdout(io.StringIO()) as output, mock.patch.object(scholar, "fetch_snapshot") as fetch:
                    self.assertEqual(scholar.main(["--features-file", str(features), "--data-file", str(data), "--print-refresh-needed"]), 0)
                    self.assertEqual(output.getvalue().strip(), expected)
                    fetch.assert_not_called()
            features.write_text('{"scholar_enabled": false}')
            data.unlink()
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(scholar.main(["--features-file", str(features), "--data-file", str(data), "--print-refresh-needed"]), 0)
                self.assertEqual(output.getvalue().strip(), "false")

    def test_disabled_skips_fetch_and_writes_even_for_manual_options(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            features = pathlib.Path(directory) / "features.json"
            features.write_text('{"scholar_enabled": false}\n')
            for options in ([], ["--check-only"], ["--allow-decrease"], ["--html-file", "missing.html"]):
                with self.subTest(options=options), mock.patch.object(
                    scholar, "read_config"
                ) as read_config, mock.patch.object(
                    scholar, "fetch_snapshot"
                ) as fetch, mock.patch.object(
                    scholar, "atomic_write"
                ) as write, contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(scholar.main(["--features-file", str(features), *options]), 0)
                    self.assertIn("disabled", output.getvalue())
                    read_config.assert_not_called()
                    fetch.assert_not_called()
                    write.assert_not_called()

    def test_print_enabled_matches_switch_without_fetching(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            features = pathlib.Path(directory) / "features.json"
            for enabled in (False, True):
                features.write_text(json.dumps({"scholar_enabled": enabled}))
                with self.subTest(enabled=enabled), mock.patch.object(
                    scholar, "read_config"
                ) as read_config, contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(scholar.main(["--features-file", str(features), "--print-enabled"]), 0)
                    self.assertEqual(output.getvalue(), f"{str(enabled).lower()}\n")
                    read_config.assert_not_called()

    def test_invalid_or_missing_switch_fails_before_fetching(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            features = pathlib.Path(directory) / "features.json"
            for content in (None, "{", "{}", "[]", '{"scholar_enabled": "false"}', '{"scholar_enabled": 1}'):
                if content is not None:
                    features.write_text(content)
                with self.subTest(content=content), mock.patch.object(
                    scholar, "fetch_snapshot"
                ) as fetch, contextlib.redirect_stderr(io.StringIO()) as output:
                    self.assertEqual(scholar.main(["--features-file", str(features)]), 1)
                    self.assertIn("Scholar update failed", output.getvalue())
                    fetch.assert_not_called()

    def test_reenabled_switch_runs_normal_refresh(self) -> None:
        config = scholar.read_config(scholar.DEFAULT_DATA_PATH)
        existing, _ = scholar.read_existing(scholar.DEFAULT_DATA_PATH)
        publication_data = scholar.read_publication_data(scholar.DEFAULT_PUBLICATION_DATA_PATH, config)
        snapshot = scholar.ScholarSnapshot(
            name=config.expected_name,
            metrics=existing,
            provider="test",
            publications=tuple(
                scholar.ScholarPublication(**paper)
                for paper in publication_data["papers"].values()
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            features = pathlib.Path(directory) / "features.json"
            features.write_text('{"scholar_enabled": false}\n')
            with mock.patch.object(scholar, "fetch_snapshot", return_value=snapshot) as fetch, mock.patch.object(
                scholar, "atomic_write"
            ) as write, contextlib.redirect_stdout(io.StringIO()):
                arguments = ["--features-file", str(features)]
                self.assertEqual(scholar.main(arguments), 0)
                fetch.assert_not_called()
                features.write_text('{"scholar_enabled": true}\n')
                self.assertEqual(scholar.main(arguments), 0)
                fetch.assert_called_once_with(config)
                self.assertEqual(write.call_count, 2)


class ScholarUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = scholar.ScholarConfig(
            source_url="https://scholar.google.com/citations?user=sITttdEAAAAJ&hl=en",
            expected_name="Qirun Zeng",
            identity_publication="Fusing Reward and Dueling Feedback in Stochastic Bandits",
        )

    def test_rate_limit_falls_through_without_immediate_retries(self):
        error = HTTPError("https://scholar.google.com", 429, "Too Many Requests", {}, None)
        with mock.patch.object(scholar, "fetch_bytes", side_effect=error) as fetch, mock.patch.object(scholar.time, "sleep") as sleep:
            with self.assertRaises(scholar.ScholarError):
                scholar.fetch_from_google(self.config.source_url)
            fetch.assert_called_once()
            sleep.assert_not_called()

    def test_blocked_google_can_recover_through_mirror(self):
        snapshot = scholar.ScholarSnapshot(name="Qirun Zeng", metrics={}, provider="test", publications=(scholar.ScholarPublication("", "Paper", 0),))
        with mock.patch.dict(scholar.os.environ, {"SERPAPI_KEY": ""}), mock.patch.object(scholar, "fetch_from_google", side_effect=scholar.ScholarError("HTTP 429")), mock.patch.object(scholar, "fetch_from_bth_mirror", return_value=snapshot), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(scholar.fetch_snapshot(self.config), snapshot)

    def test_all_providers_exhausted_is_a_fetch_error(self):
        with mock.patch.dict(scholar.os.environ, {"SERPAPI_KEY": ""}), mock.patch.object(scholar, "fetch_from_google", side_effect=scholar.ScholarError("HTTP 403")), mock.patch.object(scholar, "fetch_from_bth_mirror", side_effect=scholar.ScholarError("timeout")), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(scholar.ScholarFetchError):
                scholar.fetch_snapshot(self.config)

    def test_fetch_recovers_after_delayed_round(self):
        snapshot = scholar.ScholarSnapshot("Qirun Zeng", {}, "test")
        with mock.patch.object(scholar, "fetch_snapshot", side_effect=[scholar.ScholarFetchError("timeout"), snapshot]) as fetch, mock.patch.object(scholar.time, "sleep") as sleep, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(scholar.fetch_with_recovery(self.config, attempts=3), snapshot)
            self.assertEqual(fetch.call_count, 2)
            sleep.assert_called_once_with(60)

    def test_fetch_recovery_is_bounded_and_keeps_failure(self):
        with mock.patch.object(scholar, "fetch_snapshot", side_effect=scholar.ScholarFetchError("timeout")) as fetch, mock.patch.object(scholar.time, "sleep") as sleep, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(scholar.ScholarFetchError):
                scholar.fetch_with_recovery(self.config, attempts=3)
            self.assertEqual(fetch.call_count, 3)
            self.assertEqual(sleep.call_args_list, [mock.call(60), mock.call(60)])

    def test_validation_errors_are_not_retried(self):
        with mock.patch.object(scholar, "fetch_snapshot", side_effect=scholar.ScholarError("identity mismatch")) as fetch, mock.patch.object(scholar.time, "sleep") as sleep:
            with self.assertRaisesRegex(scholar.ScholarError, "identity mismatch"):
                scholar.fetch_with_recovery(self.config, attempts=3)
            fetch.assert_called_once()
            sleep.assert_not_called()

    def test_parses_profile_identity_and_all_time_metrics(self) -> None:
        html = (ROOT / "tests" / "fixtures" / "scholar_profile.html").read_text()
        snapshot = scholar.parse_scholar_html(html)
        self.assertEqual(snapshot.name, "Qirun Zeng")
        self.assertEqual(
            snapshot.metrics,
            {"total_citations": 1234, "h_index": 12, "i10_index": 34},
        )

    def test_parses_publication_ids_titles_and_citations(self) -> None:
        html = (ROOT / "tests" / "fixtures" / "scholar_profile.html").read_text()
        html += """
        <table>
          <tr class="gsc_a_tr">
            <td><a class="gsc_a_at" href="/citations?view_op=view_citation&amp;citation_for_view=sITttdEAAAAJ:u5HHmVD_uO8C">Fusing Reward and Dueling Feedback in Stochastic Bandits</a></td>
            <td><a class="gsc_a_ac gs_ibl">5</a></td>
          </tr>
          <tr class="gsc_a_tr">
            <td><a class="gsc_a_at" href="/citations?view_op=view_citation&amp;citation_for_view=sITttdEAAAAJ:qjMakFHDy7sC">One Rounding Fits All</a></td>
            <td><a class="gsc_a_ac gs_ibl"></a></td>
          </tr>
        </table>
        """
        snapshot = scholar.parse_scholar_html(html)
        self.assertEqual(
            snapshot.publications,
            (
                scholar.ScholarPublication(
                    scholar_id="sITttdEAAAAJ:u5HHmVD_uO8C",
                    title="Fusing Reward and Dueling Feedback in Stochastic Bandits",
                    citations=5,
                ),
                scholar.ScholarPublication(
                    scholar_id="sITttdEAAAAJ:qjMakFHDy7sC",
                    title="One Rounding Fits All",
                    citations=0,
                ),
            ),
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

    def test_reconciles_publication_citations_by_stable_scholar_id(self) -> None:
        existing = {
            "source": "Google Scholar",
            "source_url": self.config.source_url,
            "last_checked_at": "2026-09-13",
            "metrics_updated_at": "2026-09-13",
            "papers": {
                "fusing": {
                    "scholar_id": "sITttdEAAAAJ:u5HHmVD_uO8C",
                    "title": "Fusing Reward and Dueling Feedback in Stochastic Bandits",
                    "citations": 5,
                }
            },
        }
        snapshot = scholar.ScholarSnapshot(
            name="Qirun Zeng",
            metrics={"total_citations": 7, "h_index": 1, "i10_index": 0},
            provider="test",
            publications=(
                scholar.ScholarPublication(
                    scholar_id="sITttdEAAAAJ:u5HHmVD_uO8C",
                    title="Fusing Reward and Dueling Feedback in Stochastic Bandits",
                    citations=6,
                ),
            ),
        )
        updated = scholar.reconcile_publication_citations(
            snapshot, existing, checked_at="2026-09-14"
        )
        self.assertEqual(updated["papers"]["fusing"]["citations"], 6)
        self.assertEqual(updated["last_checked_at"], "2026-09-14")
        self.assertEqual(updated["metrics_updated_at"], "2026-09-14")

    def test_rejects_publication_citation_decrease(self) -> None:
        existing = {
            "papers": {
                "fusing": {
                    "scholar_id": "sITttdEAAAAJ:u5HHmVD_uO8C",
                    "title": "Fusing Reward and Dueling Feedback in Stochastic Bandits",
                    "citations": 5,
                }
            }
        }
        snapshot = scholar.ScholarSnapshot(
            name="Qirun Zeng",
            metrics={"total_citations": 6, "h_index": 1, "i10_index": 0},
            provider="test",
            publications=(
                scholar.ScholarPublication(
                    scholar_id="sITttdEAAAAJ:u5HHmVD_uO8C",
                    title="Fusing Reward and Dueling Feedback in Stochastic Bandits",
                    citations=4,
                ),
            ),
        )
        with self.assertRaisesRegex(scholar.ScholarError, "decreased unexpectedly"):
            scholar.reconcile_publication_citations(
                snapshot, existing, checked_at="2026-09-14"
            )


if __name__ == "__main__":
    unittest.main()
