"""BASIC TIME is a live, assignable centisecond clock, not an ordinary variable."""
from support import lispy3
from test_mini_basic_reader import ReaderTestCase


class BasicTimeTest(ReaderTestCase):
    def setUp(self):
        super().setUp()
        self.ticks = 100_000
        self.units = lispy3.global_env['internal-time-units-per-second']
        lispy3.global_env['get-internal-real-time'] = lambda: self.ticks

    def advance(self, centiseconds):
        self.ticks += centiseconds * self.units // 100

    def test_time_counts_elapsed_centiseconds(self):
        self.run_bbc('TIME=0')
        self.advance(235)
        self.assertEqual(self.run_bbc('PRINT ;TIME'), '235\n')

    def test_resolution_is_whole_centiseconds(self):
        self.run_bbc('TIME=0')
        self.ticks += self.units * 9 // 1000
        self.assertEqual(self.run_bbc('PRINT ;TIME'), '0\n')
        self.ticks += self.units // 1000
        self.assertEqual(self.run_bbc('PRINT ;TIME'), '1\n')

    def test_assignment_offset_and_compound_updates(self):
        self.run_bbc('LET TIME=123.9')
        self.advance(7)
        self.assertEqual(self.run_bbc('PRINT ;TIME'), '130\n')
        self.assertEqual(self.run_bbc(
            'TIME+=20 : TIME-=5 : PRINT ;TIME'), '145\n')
        self.assertEqual(self.run_bbc('TIME=TIME+10 : PRINT ;TIME'), '155\n')

    def test_clock_persists_between_programs_without_reset(self):
        self.run_bbc('TIME=0 : END')
        self.advance(50)
        self.run_bbc('x=1 : END')
        self.advance(25)
        self.assertEqual(self.run_bbc('PRINT ;TIME'), '75\n')

    def test_time_reading_function_is_not_memoized(self):
        self.run_bbc('TIME=0\nDEF FNnow(n)=TIME')
        self.advance(10)
        self.assertEqual(self.run_bbc('PRINT ;FNnow(1)'), '10\n')
        self.advance(20)
        self.assertEqual(self.run_bbc('PRINT ;FNnow(1)'), '30\n')

    def test_clock_is_reset_at_execution_not_expansion(self):
        self.ev('(define timer-program (bbc-expand "TIME=0"))')
        self.advance(250)
        self.ev('(eval timer-program)')
        self.advance(75)
        self.assertEqual(self.run_bbc('PRINT ;TIME'), '75\n')

    def test_lowercase_time_remains_a_distinct_variable(self):
        self.assertEqual(self.run_bbc('time=7 : TIME=0 : PRINT ;time'), '7\n')


class InitialTimeTest(ReaderTestCase):
    def test_time_is_readable_without_assignment(self):
        self.assertRegex(self.run_bbc('PRINT ;TIME'), r'^\d+\n$')
