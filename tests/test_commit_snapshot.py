"""Exercise snapshot publishing against a disposable, local Git remote."""

import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/commit_snapshot.sh"


class SnapshotCommitTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.remote = self.root / "remote.git"
        self.local = self.root / "worker"
        self.other = self.root / "editor"
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        self.git(self.root, "init", "--bare", str(self.remote))
        self.git(self.root, "clone", str(self.remote), str(self.local))
        self.git(self.local, "checkout", "-b", "main")
        (self.local / "snapshot.json").write_text('{"value": 1}\n')
        (self.local / "notes.txt").write_text("original\n")
        self.git(self.local, "add", ".")
        self.commit(self.local, "Initial")
        self.git(self.local, "push", "origin", "main")
        self.git(self.root, "clone", "--branch", "main", str(self.remote), str(self.other))

    def git(self, directory, *arguments):
        return subprocess.run(["git", *arguments], cwd=directory, env=self.env, check=True, capture_output=True, text=True).stdout.strip()

    def commit(self, directory, message):
        self.git(directory, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-am", message)

    def publish(self):
        output = self.root / "output"
        result = subprocess.run(
            ["bash", str(SCRIPT), "Update snapshot", "snapshot.json"],
            cwd=self.local, env=dict(self.env, GITHUB_OUTPUT=str(output)), capture_output=True, text=True,
        )
        return result, output.read_text() if output.exists() else ""

    def test_unchanged_snapshot_does_not_create_commit(self):
        previous = self.git(self.local, "rev-parse", "HEAD")
        result, output = self.publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git(self.local, "rev-parse", "HEAD"), previous)
        self.assertEqual(output, "changed=false\n")

    def test_remote_editor_commit_is_preserved(self):
        (self.other / "notes.txt").write_text("editor change\n")
        self.commit(self.other, "Editor update")
        self.git(self.other, "push", "origin", "main")
        (self.local / "snapshot.json").write_text('{"value": 2}\n')
        result, output = self.publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, "changed=true\n")
        self.assertEqual(self.git(self.remote, "show", "main:notes.txt"), "editor change")
        self.assertEqual(self.git(self.remote, "show", "main:snapshot.json"), '{"value": 2}')
        self.assertEqual(self.git(self.remote, "log", "-1", "--format=%cn" , "main"), "github-actions[bot]")

    def test_push_race_is_retried_without_losing_remote_edits(self):
        (self.other / "notes.txt").write_text("racing edit\n")
        self.commit(self.other, "Racing editor update")
        marker = self.root / "hook-ran"
        hook = self.local / ".git/hooks/pre-push"
        hook.write_text(
            "#!/bin/sh\n"
            f"if [ ! -f {shlex.quote(str(marker))} ]; then\n"
            f"  touch {shlex.quote(str(marker))}\n"
            f"  git -C {shlex.quote(str(self.other))} push origin main\n"
            "fi\n"
        )
        hook.chmod(0o755)
        (self.local / "snapshot.json").write_text('{"value": 2}\n')
        result, output = self.publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Push attempt 1 failed", result.stderr)
        self.assertEqual(output, "changed=true\n")
        self.assertEqual(self.git(self.remote, "show", "main:notes.txt"), "racing edit")
        self.assertEqual(self.git(self.remote, "show", "main:snapshot.json"), '{"value": 2}')

    def test_conflicting_snapshot_edit_leaves_remote_untouched(self):
        (self.other / "snapshot.json").write_text('{"value": 3}\n')
        self.commit(self.other, "Manual correction")
        self.git(self.other, "push", "origin", "main")
        previous = self.git(self.remote, "rev-parse", "main")
        (self.local / "snapshot.json").write_text('{"value": 2}\n')
        result, output = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("changed=true", output)
        self.assertEqual(self.git(self.remote, "rev-parse", "main"), previous)
        self.assertFalse((self.local / ".git/rebase-merge").exists())


if __name__ == "__main__":
    unittest.main()
