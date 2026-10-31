"""Scheme promises (delay, force, delay-force, make-promise) and SICP lazy
streams (cons-stream, stream-car, stream-cdr and the stream helpers)."""
import contextlib
import io

from support import LispyTestCase, lispy3


class PromiseTest(LispyTestCase):

    def test_delay_is_worked_out_once(self):
        self.ev_all('(define count 0)', '(define p (delay (begin (set! count (+ count 1)) 42)))')
        self.assertEqual(self.ev('count'), 0)
        self.assertEqual(lispy3.lisp_str(self.ev('(list (force p) (force p) count)')), '(42 42 1)')

    def test_force_of_a_non_promise_is_the_value(self):
        self.assertEqual(self.ev('(force 5)'), 5)

    def test_make_promise_and_promise_p(self):
        self.assertIs(self.ev('(promise? (make-promise 1))'), True)
        self.assertIs(self.ev('(promise? 1)'), False)
        self.assertEqual(self.ev('(force (make-promise 7))'), 7)
        self.assertIs(self.ev('(let ((p (delay 1))) (eq? p (make-promise p)))'), True)

    def test_delay_force_chain_does_not_run_out_of_stack(self):
        self.ev('(define (countdown n) (if (= n 0) (make-promise "done") (delay-force (countdown (- n 1)))))')
        self.assertEqual(self.ev('(force (countdown 100000))').value, 'done')

    def test_reentrant_force_keeps_the_first_value(self):
        # R7RS: forced again while being forced, the promise keeps the value finished first
        self.ev_all('(define x 5)', '(define p (delay (begin (set! x (+ x 1)) (if (> x 6) x (force p)))))')
        self.assertEqual(lispy3.lisp_str(self.ev('(list (force p) (force p))')), '(7 7)')

    def test_promise_prints(self):
        self.assertEqual(lispy3.lisp_str(self.ev('(delay 1)')), '#<promise>')

    def test_delay_needs_one_expression(self):
        with self.assertRaisesRegex(SyntaxError, 'delay needs one expression'):
            self.ev('(delay 1 2)')


class LazyStreamTest(LispyTestCase):

    def setUp(self):
        super().setUp()
        self.ev_all('(define (integers-from n) (cons-stream n (integers-from (+ n 1))))',
                    '(define naturals (integers-from 0))')

    def result(self, code):
        return lispy3.lisp_str(self.ev(code))

    def test_infinite_stream(self):
        self.assertEqual(self.result('(stream-head naturals 5)'), '(0 1 2 3 4)')
        self.assertEqual(self.ev('(stream-ref naturals 5000)'), 5000)
        self.assertEqual(self.result('(stream-car (stream-tail naturals 3))'), '3')

    def test_the_rest_is_not_worked_out_until_asked(self):
        self.ev_all('(define count 0)', '(define s (cons-stream 1 (begin (set! count (+ count 1)) the-empty-stream)))')
        self.assertEqual(self.ev('count'), 0)
        self.ev_all('(stream-cdr s)', '(stream-cdr s)')
        self.assertEqual(self.ev('count'), 1)

    def test_map_and_filter_are_lazy(self):
        self.assertEqual(self.result('(stream-head (stream-filter odd? (stream-map * naturals naturals)) 4)'),
                         '(1 9 25 49)')

    def test_self_referring_stream(self):
        self.ev('(define fibs (cons-stream 0 (cons-stream 1 (stream-map + fibs (stream-cdr fibs)))))')
        self.assertEqual(self.ev('(stream-ref fibs 60)'), 1548008755920)

    def test_sieve_of_eratosthenes(self):
        self.ev('(define (sieve s) (cons-stream (stream-car s) (sieve (stream-filter'
                ' (lambda (x) (not (= 0 (remainder x (stream-car s))))) (stream-cdr s)))))')
        self.assertEqual(self.result('(stream-head (sieve (integers-from 2)) 10)'), '(2 3 5 7 11 13 17 19 23 29)')

    def test_finite_streams(self):
        self.assertEqual(self.result('(stream->list (stream 1 2 3))'), '(1 2 3)')
        self.assertEqual(self.result('(stream->list (list->stream (list 4 5)))'), '(4 5)')
        self.assertEqual(self.result('(stream->list naturals 3)'), '(0 1 2)')
        self.assertEqual(self.result('(stream->list (stream-map + (stream 1 2 3) (stream 10 20)))'), '(11 22)')

    def test_empty_stream_and_predicates(self):
        self.assertIs(self.ev('(stream-null? the-empty-stream)'), True)
        self.assertIs(self.ev('(stream-pair? naturals)'), True)
        self.assertIs(self.ev('(stream-pair? (list 1 2))'), False)
        with self.assertRaisesRegex(TypeError, 'not a stream'):
            self.ev('(stream-car the-empty-stream)')

    def test_stream_for_each(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.ev('(stream-for-each display (stream 1 2))')
        self.assertEqual(out.getvalue(), '1\n2\n')

    def test_stream_prints_as_a_pair_with_a_promise(self):
        self.assertEqual(self.result('naturals'), '(0 . #<promise>)')
