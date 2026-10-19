"""One check per ticked item in TODO.md.

Each entry in TODO_EXAMPLES starts with words from a TODO.md line and lists
Lispy examples with the result the REPL should print. test_every_ticked_item_
has_examples fails if an item is ticked in TODO.md without examples here, so
ticking a box also means showing that it works.

Run from the repository folder:  python -m unittest discover tests
"""
import builtins
import os

from support import LispyTestCase, REPO_DIR, lispy3

# (source, what the REPL prints). A list of sources runs them in order and
# checks the last one. "!Error" means the code must raise that Python error.
TODO_EXAMPLES = {
    # --- Language
    "`cond` for a chain of tests": [
        ("(cond ((> 1 2) 'a) ((< 1 2) 'b) (else 'c))", "b"),
        ("(cond (#f 'a) (else 'c))", "c"),
        ("(cond ((= 1 1) (define t 1) (+ t 1)))", "2"),       # several expressions
        ("(cond (#f 1))", None),                             # no clause matched
        ("(cond (42))", "42"),                               # a test with no body gives the test
    ],
    "`and` / `or`, short-circuit": [
        ("(and 1 2 3)", "3"),
        ("(and)", "#t"),
        ("(or)", "#f"),
        ("(and #f (car))", "#f"),                            # (car) would be an error
        ("(or 1 (car))", "1"),
        ("(and 1 0 2)", "2"),                                # 0 is true, as in every Lisp
        ("(or '() #f 'x)", "x"), ("(or '() 0 'x)", "0"),
    ],
    "Macros: `define-macro`, quasiquote": [
        (["(define-macro (swap! a b) (let [tmp (gensym)] `(let [,tmp ,a] (set! ,a ,b) (set! ,b ,tmp))))",
          "(define x 1)", "(define y 2)", "(swap! x y)", "(list x y)"], "(2 1)"),
        (["(define-macro (unless c & body) `(if ,c #f (begin ,@body)))",
          "(unless #f 1 2 3)"], "3"),
        (["(define xs '(2 3))", "`(1 ,@xs ,(+ 2 2))"], "(1 2 3 4)"),
        ("`(a (b ,(+ 1 1)))", "(a (b 2))"),                  # nested lists
        ("(symbol? (gensym))", "#t"),
    ],
    "`(define (f x) body)` shorthand": [
        (["(define (sq x) (* x x))", "(sq 9)"], "81"),
        (["(define (zero) 0)", "(zero)"], "0"),
        (["(define (fact n) (if (< n 2) 1 (* n (fact (- n 1)))))", "(fact 20)"], "2432902008176640000"),
    ],
    "Several body expressions in `lambda` and `let`": [
        ("((lambda [x] (define y (* x 2)) (+ x y)) 3)", "9"),
        ("(let [a 1] (define b 2) (+ a b))", "3"),
        (["(define (f x) (define a 1) (define b 2) (+ x a b))", "(f 3)"], "6"),
    ],
    "Proper tail calls": [
        (["(define (down n) (if (= n 0) 'done (down (- n 1))))", "(down 100000)"], "done"),
        (["(define (even? n) (if (= n 0) #t (odd? (- n 1))))",
          "(define (odd? n) (if (= n 0) #f (even? (- n 1))))", "(even? 10001)"], "#f"),  # mutual recursion
        (["(define (sum n acc) (cond ((= n 0) acc) (else (sum (- n 1) (+ acc n)))))",
          "(sum 100000 0)"], "5000050000"),                  # tail call inside cond
        (["(define (loop n) (let [m (- n 1)] (if (= m 0) 'ok (loop m))))", "(loop 50000)"], "ok"),
        (["(define (loop n) (and #t (if (= n 0) 'ok (loop (- n 1)))))", "(loop 50000)"], "ok"),
    ],
    "`try` / `error`": [
        ('(try (error "bad" 1) (catch e e))', '"bad 1"'),
        ("(try (car 1 2) (catch e 'caught))", "caught"),
        ("(try (+ 1 1) (catch e 'never))", "2"),
        ("(try (undefined-name) 'fallback)", "fallback"),
        ('(error "stop")', "!LispyError"),
    ],
    # --- Numbers
    "`+ - * /` with any number of arguments": [
        ("(+ 1 2 3)", "6"), ("(+)", "0"), ("(*)", "1"), ("(- 10 1 2 3)", "4"),
        ("(- 5)", "-5"), ("(/ 2)", "1/2"), ("(/ 60 2 3)", "10"), ("(/ 2.0)", "0.5"), ("(+ 0.5 1 2)", "3.5"),
    ],
    "`<`, `=`, ... comparing more than two values": [
        ("(< 1 2 3)", "#t"), ("(< 1 3 2)", "#f"), ("(<= 1 1 2)", "#t"),
        ("(> 3 2 1)", "#t"), ("(>= 3 3 3)", "#t"), ("(= 1 1 1)", "#t"), ("(= 1 1 2)", "#f"),
        ('(= "a" "a" "a")', "#t"),
    ],
    "`modulo` and `quotient` on whole numbers": [
        ("(quotient 17 5)", "3"), ("(quotient -17 5)", "-3"), ("(quotient 17 -5)", "-3"),
        ("(modulo 17 5)", "2"), ("(modulo -7 3)", "2"), ("(modulo 7 -3)", "-2"),
        ("(quotient (expt 10 40) 3)", "3333333333333333333333333333333333333333"),
        ("(modulo (expt 10 40) 7)", str(10 ** 40 % 7)),
        ("(quotient 7 0)", "!ZeroDivisionError"),
    ],
    "More whole-number procedures": [
        ("(div 17 5)", "3"), ("(div -17 5)", "-4"),          # rounds down, like Python's //
        ("(mod -17 5)", "3"), ("(mod 17 -5)", "-3"),          # sign of the divisor, like Python's %
        ("(divmod 17 5)", "(3 2)"), ("(divmod -17 5)", "(-4 3)"),
        ("(divmod (expt 10 30) 7)", f"({10 ** 30 // 7} {10 ** 30 % 7})"),
        ("(remainder -17 5)", "-2"), ("(remainder 17 -5)", "2"),  # sign of the dividend
        ("(remainder 7.5 2)", "1.5"),
        ("(even? 10)", "#t"), ("(odd? -3)", "#t"), ("(even? 2.5)", "!TypeError"),
        ("(zero? 0.0)", "#t"), ("(positive? -1)", "#f"), ("(negative? -1)", "#t"),
        ("(integer? 3)", "#t"), ("(integer? 3.0)", "#t"), ("(integer? 3.5)", "#f"), ("(integer? #t)", "#f"),
        ("(exact 3.0)", "3"), ("(exact 3.5)", "7/2"), ("(inexact 3)", "3.0"),
        ("(number->string 255 16)", '"ff"'), ("(number->string -10 2)", '"-1010"'),
        ("(string->number (number->string 12345 36) 36)", "12345"),
        ("(div 1 0)", "!ZeroDivisionError"),
    ],
    # --- Lists
    "`reverse`, `nth`, `last`, `range`": [
        ("(reverse '(1 2 3))", "(3 2 1)"), ("(reverse '())", "()"),
        ("(nth '(a b c) 0)", "a"), ("(nth '(a b c) 5)", "!IndexError"),
        ("(last '(1 2 3))", "3"), ("(last '())", "()"),
        ("(range 4)", "(0 1 2 3)"), ("(range 2 5)", "(2 3 4)"), ("(range 10 0 -3)", "(10 7 4 1)"),
    ],
    "`reduce` / `fold`, `apply`, `sort`, `member`": [
        ("(reduce + '(1 2 3))", "6"), ("(reduce * 1 '(2 3 4))", "24"), ("(fold + 0 '())", "0"),
        ("(apply max '(3 9 2))", "9"), ("(apply + 1 2 '(3))", "6"),
        (["(define (add3 a b c) (+ a b c))", "(apply add3 '(1 2 3))"], "6"),
        ("(sort '(3 1 2))", "(1 2 3)"), ("(sort '(3 1 2) >)", "(3 2 1)"),
        ('(sort (list "b" "a"))', '("a" "b")'),
        ("(member 'c '(a b c d))", "(c d)"), ("(member 'z '(a b))", "#f"),
        ("(member '(1) '((1) 2))", "((1) 2)"),              # compares lists by value
    ],
    "`append` with any number of lists": [
        ("(append '(1) '(2 3) '() '(4))", "(1 2 3 4)"), ("(append)", "()"),
        ('(append "a" "b" "c")', '"abc"'),
    ],
    "`list?`, `procedure?`, `eq?`, `equal?` tests": [
        ("(list? '())", "#t"), ("(list? \"a\")", "#f"),
        ("(procedure? (lambda [x] x))", "#t"), ("(procedure? 'car)", "#f"),
        ("(eq? 'a 'a)", "#t"), (["(define l (list 1))", "(eq? l l)"], "#t"),
        ("(eq? (list 1) (list 1))", "#f"),                   # two different lists
        ("(equal? (list 1 (list 2)) (list 1 (list 2)))", "#t"), ("(equal? 1 2)", "#f"),
    ],
    "`for-each` and a counting loop": [
        (["(define total 0)", "(for-each (lambda [x] (set! total (+ total x))) '(1 2 3))", "total"], "6"),
        (["(define s 0)", "(for-each (lambda [a b] (set! s (+ s (* a b)))) '(1 2) '(3 4))", "s"], "11"),
        (["(define t 0)", "(dotimes [i 5] (set! t (+ t i)))", "t"], "10"),
        ("(dotimes [i 0] (car))", None),                     # zero times runs nothing
    ],
    # --- Strings
    "`substring`, `string-ref`, `upcase`, `downcase`, `split`, `list->string`": [
        ('(substring "hello" 1 4)', '"ell"'), ('(substring "hello" 3)', '"lo"'),
        ('(string-ref "abc" 2)', "#\\c"),
        ('(upcase "Lispy")', '"LISPY"'), ('(downcase "Lispy")', '"lispy"'),
        ('(split "a b  c")', '("a" "b" "c")'), ('(split "1,2,3" ",")', '("1" "2" "3")'),
        ("(list->string (list #\\h #\\i))", '"hi"'),
        ('(list->string (reverse (seq "abc")))', '"cba"'),
    ],
    "`string->number`": [
        ('(string->number "42")', "42"), ('(string->number " -7 ")', "-7"),
        ('(string->number "2.5")', "2.5"), ('(string->number "ff" 16)', "255"),
        ('(string->number "abc")', "#f"),
    ],
    "`str` should return a real string": [
        ('(= (str 12) "12")', "#t"), ("(string? (str 12))", "#t"),
        ('(str "a" 1 #\\b \'c)', '"a1bc"'), ("(str)", '""'),
    ],
    "More string escapes": [
        ('(length "a\\rb")', "3"), ('(string-ref "\\x41;" 0)', "#\\A"),
        ('(string-ref "\\u00e4" 0)', "#\\ä"), ('"tab\\there"', '"tab\\there"'),
    ],
    "More character names": [
        ("#\\return", "#\\return"), ("#\\nul", "#\\nul"), ("#\\x41", "#\\A"),
        ("#\\space", "#\\space"), ("#\\newline", "#\\newline"),
    ],
    "String formatting: `format`": [
        ('(format "~a + ~a = ~a" 1 2 3)', '"1 + 2 = 3"'),
        ('(format "~s and ~a" "x" "x")', '"\\"x\\" and x"'),
        ('(format "100~~ sure~%")', '"100~ sure\\n"'),
        ('(str "n=" 5)', '"n=5"'),
    ],
    # --- Maps
    "`assoc`, `dissoc`, `keys`, `vals`, `contains?`": [
        ("(assoc {:a 1} :b 2 :c 3)", "{:a 1 :b 2 :c 3}"), ("(assoc {:a 1} :a 9)", "{:a 9}"),
        (["(define m {:a 1})", "(assoc m :b 2)", "m"], "{:a 1}"),   # the original is unchanged
        ("(dissoc {:a 1 :b 2} :a :zz)", "{:b 2}"),
        ("(keys {:a 1 :b 2})", "(:a :b)"), ("(vals {:a 1 :b 2})", "(1 2)"),
        ("(contains? {:a 1} :a)", "#t"), ("(contains? {:a 1} :b)", "#f"),
        ('(get (assoc {} "k" 1) "k")', "1"),
    ],
}

def ticked_items() -> list[str]:
    """The ticked TODO.md lines from the feature sections (not the Tests section)."""
    items, section = [], ''
    with open(os.path.join(REPO_DIR, 'TODO.md'), encoding='utf-8') as f:
        for line in f:
            if line.startswith('## '):
                section = line[3:].strip()
            elif line.startswith('- [x] ') and section != 'Tests':
                items.append(line[6:].strip())
    return items


class TodoItemsTest(LispyTestCase):

    def check(self, source, expected):
        sources = source if isinstance(source, list) else [source]
        if expected and expected.startswith('!'):
            for s in sources[:-1]:
                self.ev(s)
            error = getattr(lispy3, expected[1:], None) or getattr(builtins, expected[1:])
            with self.assertRaises(error):
                self.ev(sources[-1])
            return
        value = self.ev_all(*sources)
        if expected is None:
            self.assertIsNone(value)
        else:
            self.assertEqual(lispy3.lisp_str(value), expected)

    def test_every_ticked_item_has_examples(self):
        """Every item ticked in TODO.md has examples in this file."""
        for item in ticked_items():
            with self.subTest(item):
                self.assertTrue(any(item.startswith(key) for key in TODO_EXAMPLES),
                                "ticked in TODO.md but no examples in tests/test_todo.py")

    def test_examples(self):
        """Each TODO example gives its expected result, starting from a clean Lispy."""
        for item, examples in TODO_EXAMPLES.items():
            for source, expected in examples:
                with self.subTest(item=item, source=source):
                    self.setUp()                     # each example starts from a clean Lispy
                    self.check(source, expected)


if __name__ == '__main__':
    import unittest
    unittest.main()
