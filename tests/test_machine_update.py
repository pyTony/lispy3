"""Tests for Help > Update, which runs `git pull` in the program's folder.

Each test makes a throwaway "origin" repository and a clone of it, so no
network is needed.

Run:  python -m unittest discover tests
"""
import os
import shutil
import subprocess
import sys
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
        """Help > Update reports current when there is nothing new."""
        result, _ = machine.git_pull(self.clone)
        self.assertEqual(result, "current")

    def test_new_commit_is_pulled(self):
        """A new commit is pulled and reported as updated."""
        commit(self.origin, "b.lisp", "(* 2 3)\n")
        result, _ = machine.git_pull(self.clone)
        self.assertEqual(result, "updated")
        self.assertTrue(os.path.exists(os.path.join(self.clone, "b.lisp")))

    def test_local_change_in_the_way_fails_and_is_kept(self):
        """A local edit that blocks the pull fails the update and is kept."""
        commit(self.origin, "a.lisp", "(+ 1 2 3)\n")
        with open(os.path.join(self.clone, "a.lisp"), "w", encoding="utf-8") as f:
            f.write(";; mine\n")
        result, output = machine.git_pull(self.clone)
        self.assertEqual(result, "failed")
        self.assertIn("a.lisp", output)
        with open(os.path.join(self.clone, "a.lisp"), encoding="utf-8") as f:
            self.assertEqual(f.read(), ";; mine\n")

    def test_folder_that_is_not_a_repository_fails(self):
        """Updating a folder that is not a git checkout fails with a message."""
        with tempfile.TemporaryDirectory() as plain:
            result, output = machine.git_pull(plain)
        self.assertEqual(result, "failed")
        self.assertTrue(output)

    def test_missing_git_fails_with_a_message(self):
        """Without git installed, the update fails with a message naming git."""
        saved = os.environ["PATH"]
        os.environ["PATH"] = ""
        self.addCleanup(os.environ.__setitem__, "PATH", saved)
        result, output = machine.git_pull(self.clone)
        self.assertEqual(result, "failed")
        self.assertIn("git", output)



class RestartCommand(unittest.TestCase):
    def test_same_python_runs_the_editor_with_the_open_files(self):
        """Restart runs the same Python on the editor with the open files."""
        cmd = machine.restart_command(["/a/x.lisp", "/b/y.lisp"], False)
        self.assertEqual(cmd[0], sys.executable)
        self.assertEqual(os.path.basename(cmd[1]), "lispy_machine.pyw")
        self.assertTrue(os.path.isabs(cmd[1]))
        self.assertEqual(cmd[2:], ["/a/x.lisp", "/b/y.lisp"])

    def test_plain_repl_mode_is_kept(self):
        """Restart keeps the plain REPL mode."""
        self.assertEqual(machine.restart_command([], True)[2:], ["--repl"])


if __name__ == "__main__":
    unittest.main()
