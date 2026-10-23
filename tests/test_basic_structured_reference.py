"""Shared source fixtures for lispy3 and independently executed BBCSDL checks."""
from pathlib import Path
from support import REPO_DIR
from test_mini_basic_reader import ReaderTestCase

class StructuredReferenceTest(ReaderTestCase):
    def test_structured_returns_and_local_restoration(self):
        root=Path(REPO_DIR)/'basic'/'reference'/'structured'
        cases=sorted(root.glob('*.bas'))
        self.assertEqual(len(cases),11)
        for path in cases:
            with self.subTest(case=path.stem):
                self.assertEqual(self.run_bbc(path.read_text()),path.with_suffix('.out').read_text())
