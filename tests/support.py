"""Shared set-up for the Lispy tests.

Run every test from the repository folder with either of:

    python -m unittest discover tests
    python -m pytest tests

Python's turtle module is replaced by tests/turtle_stub.py before lispy3 is
imported, so no window opens and tkinter does not need to be installed.
Every test module that needs lispy3 should import it from here
(`from support import lispy3`), so all of them share the one stub.
"""
import os
import sys
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(TESTS_DIR)
for _path in (TESTS_DIR, REPO_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import turtle_stub  # noqa: E402

sys.modules['turtle'] = turtle_stub

import lispy3  # noqa: E402


def fresh_global_env() -> None:
    """Put the global environment back to its start-up state.

    eval_exp and (eval ...) both use lispy3.global_env, so it is emptied and
    refilled in place rather than replaced.
    """
    lispy3.global_env.clear()
    lispy3.global_env.update(lispy3.standard_env())
    lispy3.clear_poses()
    turtle_stub.reset_stub()


class LispyTestCase(unittest.TestCase):
    """A test case with a clean global environment and an `ev` helper."""

    def setUp(self) -> None:
        fresh_global_env()

    def ev(self, source: str):
        """Parse and evaluate one expression in the global environment."""
        return lispy3.eval_exp(lispy3.parse(source), lispy3.global_env)

    def ev_all(self, *sources: str):
        """Evaluate several expressions in order and return the last value."""
        result = None
        for source in sources:
            result = self.ev(source)
        return result

    def show(self, source: str) -> str:
        """Evaluate and return the result as the REPL would print it."""
        return lispy3.lisp_str(self.ev(source))
