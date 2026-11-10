"""Exercise publication references in both full and compact news copy."""

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NewsContentTests(unittest.TestCase):
    def check_news(self, news):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            for relative in (
                "_data/publications.yml", "_data/features.json", "_data/assets.json",
                "assets/css/main.css", "assets/js/site.js",
            ):
                target = fixture / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            home = {
                "selected_publications": ["werewolf"],
                "research": {"interests": []},
                "news": [news],
            }
            # JSON is valid YAML, so fixtures need no additional Python dependency.
            (fixture / "_data/home.yml").write_text(json.dumps(home), encoding="utf-8")
            return subprocess.run(
                ["ruby", "-r", str(ROOT / "scripts/check_content.rb"),
                 "-e", "ContentChecks.check(ARGV.fetch(0))", str(fixture)],
                text=True, capture_output=True, check=False,
            )

    def test_compact_copy_is_optional(self):
        result = self.check_news({"text": "[WEREWOLF][paper:werewolf]"})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_compact_copy_can_reference_a_known_paper(self):
        result = self.check_news({"text": "Full news", "home_text": "[Paper][paper:werewolf]"})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unknown_compact_reference_is_rejected(self):
        result = self.check_news({"text": "Full news", "home_text": "[Paper][paper:missing-paper]"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown publication reference: missing-paper", result.stderr)

    def test_full_copy_is_still_validated(self):
        result = self.check_news({"text": "[Paper][paper:missing-paper]", "home_text": "Short news"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown publication reference: missing-paper", result.stderr)

    def test_compact_copy_must_be_text(self):
        result = self.check_news({"text": "Full news", "home_text": 42})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("News home_text must be a string", result.stderr)
