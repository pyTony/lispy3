"""BBC BASIC random-number forms and stateful FN behavior."""
from test_mini_basic_reader import ReaderTestCase
from support import lispy3 as L


class BasicRndTest(ReaderTestCase):
    def setUp(self):
        workspace = L.workspaces.create('RND regression')
        self.addCleanup(L.workspaces.discard, workspace)
        self.enterContext(L.workspaces.use(workspace))
        super().setUp()

    def test_bare_rnd_is_signed_32_bit_and_can_be_used_in_arithmetic(self):
        values = [int(x) for x in self.run_bbc('FOR i=1 TO 8:PRINT ;RND:NEXT i').splitlines()]
        self.assertTrue(all(-2147483648 <= x <= 2147483647 for x in values))
        self.assertGreater(len(set(values)), 1)
        self.run_bbc('n=RND+1')

    def test_fractional_and_bounded_forms(self):
        values = [float(x) for x in self.run_bbc('FOR i=1 TO 12:PRINT ;RND(1):NEXT i').splitlines()]
        self.assertTrue(all(0 <= x < 1 for x in values))
        dice = [int(x) for x in self.run_bbc('FOR i=1 TO 40:PRINT ;RND(6):NEXT i').splitlines()]
        self.assertTrue(all(1 <= x <= 6 for x in dice))
        self.assertGreater(len(set(dice)), 1)

    def test_zero_repeats_without_advancing_and_state_persists_between_calls(self):
        self.run_bbc('seed=RND(-7)')
        first = self.run_bbc('PRINT ;RND(1)')
        self.assertEqual(self.run_bbc('PRINT ;RND(0)'), first)
        self.assertEqual(self.run_bbc('PRINT ;RND(0)'), first)
        second = self.run_bbc('PRINT ;RND(1)')
        self.run_bbc('seed=RND(-7)')
        self.assertEqual(self.run_bbc('PRINT ;RND(1)'), first)
        self.assertEqual(self.run_bbc('PRINT ;RND(1)'), second)

    def test_negative_argument_reseeds_and_is_returned(self):
        self.assertEqual(self.run_bbc('PRINT ;RND(-123)'), '-123\n')
        first = self.run_bbc('PRINT ;RND:PRINT ;RND(100):PRINT ;RND(1)')
        self.run_bbc('seed=RND(-123)')
        self.assertEqual(self.run_bbc('PRINT ;RND:PRINT ;RND(100):PRINT ;RND(1)'), first)

    def test_fn_reading_random_is_not_memoized(self):
        output = self.run_bbc('DEF FNr(n)=RND\nPRINT ;FNr(1)\nPRINT ;FNr(1)')
        a, b = output.splitlines()
        self.assertNotEqual(a, b)

    def test_argument_is_evaluated_once(self):
        output = self.run_bbc('DEF FNbound(n)\n calls=calls+1\n=6\nPRINT ;RND(FNbound(1))\nPRINT ;calls')
        self.assertEqual(output.splitlines()[-1], '1')

    def test_bad_arity_and_type_report_clear_errors(self):
        for source in ('PRINT RND()', 'PRINT RND(1,2)', 'PRINT RND("bad")'):
            with self.subTest(source=source), self.assertRaisesRegex(Exception, 'RND'):
                self.run_bbc(source)
