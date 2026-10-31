"""docs/FEATURE_MATRIX.md keeps up with the code, one PR at a time.

Each check fails when a feature PR forgets the matrix: a new or grown help
topic, a new docs page, or a change in the MBASIC golden results.

Run:  python -m unittest tests.test_feature_matrix -v
"""
import os
import re
import unittest
from collections import Counter

from support import REPO_DIR, lispy3
from test_mbasic_compat import EXPECTED, PASS, SPACING

DOCS = os.path.join(REPO_DIR, 'docs')
MATRIX = os.path.join(DOCS, 'FEATURE_MATRIX.md')


def matrix_text():
    with open(MATRIX, encoding='utf-8') as f:
        return f.read()


class FeatureMatrixTest(unittest.TestCase):
    def test_help_topic_counts_match(self):
        """Every (help) topic is listed with its current number of names."""
        text = matrix_text()
        listed = dict(re.findall(r'^\| ([^|]+?) \| (\d+) \|$', text, re.M))
        for topic, entries in lispy3.HELP_TOPICS.items():
            name = topic.split(' (')[0]
            with self.subTest(topic=name):
                self.assertIn(name, listed, f'add "| {name} | {len(entries)} |" to the '
                              'built-ins table in docs/FEATURE_MATRIX.md and a feature row for it')
                self.assertEqual(int(listed[name]), len(entries),
                                 f'{name} now has {len(entries)} names: update its count and '
                                 'the feature rows in docs/FEATURE_MATRIX.md')

    def test_every_docs_page_is_linked(self):
        """A new docs page is a new feature or guide: the matrix links to it."""
        text = matrix_text()
        for page in sorted(os.listdir(DOCS)):
            if page.endswith('.md') and page != 'FEATURE_MATRIX.md':
                with self.subTest(page=page):
                    self.assertIn(f']({page}', text, f'link docs/{page} from docs/FEATURE_MATRIX.md')

    def test_mbasic_golden_counts_match_expected(self):
        """The MBASIC golden line agrees with EXPECTED in test_mbasic_compat."""
        counts = Counter('pass' if v == PASS else 'spacing' if v == SPACING else 'fail'
                         for v in EXPECTED.values())
        line = (f"MBASIC 5.21 golden programs: {counts['pass']} pass, {counts['spacing']} "
                f"spacing only, {counts['fail']} fail (of {len(EXPECTED)})")
        self.assertIn(line, matrix_text(), 'update the MBASIC line in docs/FEATURE_MATRIX.md')

    def test_has_last_checked_line(self):
        """The page says when it was last brought up to date."""
        self.assertRegex(matrix_text(), r'\*\*Last checked: \d{4}-\d\d-\d\d, ')


if __name__ == '__main__':
    unittest.main()
