"""Tests for Help > Update, which runs `git pull` in the program's folder.

Each test makes a throwaway "origin" repository and a clone of it, so no
network is needed.

Run:  python -m unittest discover tests
"""
import os
import shutil
import subprocess
import tempfile
import unittest

from test_machine_args import machine


def git(folder, *args):
    subprocess.run(["git", *args], cwd=folder, check=True, capture_output=True,
                   env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t"))


def commit(folder, name, text):
    with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
        f.write(text)
    git(folder, "add", name)
    git(folder, "commit", "-q", "-m", f"change {name}")


@unittest.skipUnless(shutil.which("git"), "git is not installed")
class GitPull(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.origin = os.path.join(tmp.name, "origin")
        self.clone = os.path.join(tmp.name, "clone")
        os.mkdir(self.origin)
        git(self.origin, "init", "-q")
        commit(self.origin, "a.lisp", "(+ 1 2)\n")
        git(tmp.name, "clone", "-q", self.origin, self.clone)

    def test_nothing_new_is_current(self):
        result, _ = machine.git_pull(self.clone)
        self.assertEqual(result, "current")

    def test_new_commit_is_pulled(self):
        commit(self.origin, "b.lisp", "(* 2 3)\n")
        result, _ = machine.git_pull(self.clone)
        self.assertEqual(result, "updated")
        self.assertTrue(os.path.exists(os.path.join(self.clone, "b.lisp")))

    def test_local_change_in_the_way_fails_and_is_kept(self):
        commit(self.origin, "a.lisp", "(+ 1 2 3)\n")
        with open(os.path.join(self.clone, "a.lisp"), "w", encoding="utf-8") as f:
            f.write(";; mine\n")
        result, output = machine.git_pull(self.clone)
        self.assertEqual(result, "failed")
        self.assertIn("a.lisp", output)
        with open(os.path.join(self.clone, "a.lisp"), encoding="utf-8") as f:
            self.assertEqual(f.read(), ";; mine\n")

    def test_folder_that_is_not_a_repository_fails(self):
        with tempfile.TemporaryDirectory() as plain:
            result, output = machine.git_pull(plain)
        self.assertEqual(result, "failed")
        self.assertTrue(output)

    def test_missing_git_fails_with_a_message(self):
        saved = os.environ["PATH"]
        os.environ["PATH"] = ""
        self.addCleanup(os.environ.__setitem__, "PATH", saved)
        result, output = machine.git_pull(self.clone)
        self.assertEqual(result, "failed")
        self.assertIn("git", output)


if __name__ == "__main__":
    unittest.main()
