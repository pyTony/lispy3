#!/usr/bin/env python3
"""run_complex_checks.py - test suite for complex-number support in lispy3.py.

Run:  python tools/run_complex_checks.py [path/to/lispy3.py]
      (defaults to lispy3.py at the project root)

Cases marked KNOWN are things I believe are wrong or surprising today; they are
reported separately and do not fail the run (use --strict to make them fail).
"""
import cmath, importlib.util, math, os, sys
from fractions import Fraction
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

args = [a for a in sys.argv[1:] if not a.startswith('--')]
STRICT = '--strict' in sys.argv
path = args[0] if args else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lispy3.py')
spec = importlib.util.spec_from_file_location('lispy3', path)
L = importlib.util.module_from_spec(spec)
sys.modules['lispy3'] = L
spec.loader.exec_module(L)

def ev(src):
    """Evaluate every form in src in a fresh env; return the last value."""
    env = L.standard_env()
    tokens = L.tokenize(src)
    val = None
    while tokens:
        val = L.eval_exp(L.read_from_tokens(tokens), env)
    return val

def show(src):
    return L.lisp_str(ev(src))

passed = failed = known_bad = known_fixed = 0
fails, knowns = [], []

def close(a, b):
    if isinstance(a, complex) or isinstance(b, complex):
        return type(a) is type(b) and cmath.isclose(a, b, abs_tol=1e-9)
    return a == b and type(a) is type(b) if isinstance(a, bool) else (
        math.isclose(a, b, abs_tol=1e-9) if isinstance(a, float) or isinstance(b, float) else a == b)

def check(src, expected, known=None):
    """expected: a value, or an Exception class (must raise). known: reason string."""
    global passed, failed, known_bad, known_fixed
    try:
        got = ev(src)
        ok = (not isinstance(expected, type)) and close(got, expected)
        desc = f"got {got!r}"
    except Exception as e:
        ok = isinstance(expected, type) and isinstance(e, expected)
        desc = f"raised {type(e).__name__}: {e}"
    if known:
        if ok: known_fixed += 1
        else:
            known_bad += 1; knowns.append((src, expected, desc, known))
            if STRICT: failed += 1
        return
    if ok: passed += 1
    else: failed += 1; fails.append((src, expected, desc))

def check_str(src, expected, known=None):
    global passed, failed, known_bad, known_fixed
    try: got = show(src); ok = got == expected; desc = f"got {got!r}"
    except Exception as e: ok = False; desc = f"raised {type(e).__name__}: {e}"
    if known:
        if ok: known_fixed += 1
        else:
            known_bad += 1; knowns.append((src, expected, desc, known))
            if STRICT: failed += 1
        return
    if ok: passed += 1
    else: failed += 1; fails.append((src, expected, desc))

# ---------------------------------------------------------------- literals
for s, v in [('3+4i', 3+4j), ('3-4i', 3-4j), ('4i', 4j), ('-4i', -4j), ('+i', 1j), ('-i', -1j),
             ('1.5-2.5i', 1.5-2.5j), ('3+4j', 3+4j), ('0+0i', 0j), ('1e2+1e-1i', 100+0.1j),
             ('#C(1 2)', 1+2j), ('#c(1 2)', 1+2j), ('#C(1.5 -2)', 1.5-2j), ('#C(0 1)', 1j)]:
    check(s, v)
check("'(1 2+i)", [1, 2+1j])

# ------------------------------------------------- symbols must NOT be parsed
check('(begin (define pi 3) pi)', 3)
check('(begin (define i 5) (+ i 1))', 6)
check('(begin (define j 5) (+ j 1))', 6)
check('(let ((i 3)) (* i 2))', 6)
check('(begin (define (f loci) (* loci 2)) (f 4))', 8)
check('(begin (define taxi 7) taxi)', 7)
check('(begin (define phi 2) phi)', 2)
check('(begin (define hi 1) hi)', 1)
check('(begin (define +i2 1) +i2)', 1)
check('(begin (define a-i 9) a-i)', 9)
check("(symbol? 'pi)", True)
check("(symbol? 'i)", True)
check("(symbol? 'hi)", True)
check("(symbol? '+i)", False)           # +i is the imaginary unit now
check("(number? 'ii)", False)
check('(number? 1+i)', True)
check('(number? "3+4i")', False)
check('(begin (define nani 1) nani)', 1)      # complex('nanj') is valid Python!
check('(begin (define infi 1) infi)', 1)
check('(begin (define infinityi 1) infinityi)', 1)
check("(number? 'nani)", False)
check('(begin (define 1+ (lambda (n) (+ n 1))) (1+ 5))', 6)   # 1+ must stay a symbol

# --------------------------------------------------------------- arithmetic
check('(+ 3+4i 1-2i)', 4+2j)
check('(- 3+4i 1-2i)', 2+6j)
check('(* 3+4i 3-4i)', 25+0j)
check('(* #C(0 1) #C(0 1))', -1+0j)
check('(/ 1+2i 3-4i)', (1+2j)/(3-4j))
check('(+ 1 2 3+i)', 6+1j)
check('(+ 1/2 1+i)', 1.5+1j)
check('(- 5i)', -5j)
check('(* 2 -i)', -2j)
check('(/ 1 0+0i)', ZeroDivisionError)
check('(= 1+0i 1)', True)
check('(= 1+2i 1+2i)', True)
check('(= 1+2i 1+3i)', False)
check('(zero? 0+0i)', True)
check('(zero? 0+1i)', False)
check('(abs 3+4i)', 5.0)
check('(magnitude 3+4i)', 5.0)
check('(magnitude -5)', 5)
check('(equal? 1+2i 1+2i)', True)
check('(equal? 1+2i 1+3i)', False)
check('(eq? 1+2i 1+2i)', True)

# -------------------------------------------------------------- predicates
check('(complex? 1+i)', True)
check('(complex? 1)', False, known='(complex? 1) is #f; in Scheme/CL every real is also complex')
check('(real? 1.5)', True)
check('(real? 1+0i)', True)
check('(real? 1+i)', False)
check('(real? "x")', False)
check('(real? #t)', False)
check('(number? #t)', False)
check('(integer? 1+0i)', False)
check('(integer? 3)', True)
check('(rational? 1+i)', False)
check('(exact? 1+i)', False)

# --------------------------------------------------------------- accessors
check('(real-part 3+4i)', 3.0)
check('(imag-part 3+4i)', 4.0)
check('(real-part 5)', 5)
check('(imag-part 5)', 0)
check('(real-part 0+4i)', 0.0, known='and/or idiom: real part 0.0 is falsy, returns the whole complex')
check('(real-part -0.0+4i)', -0.0, known='same and/or bug')
check('(imag-part 5+0i)', 0.0, known='same and/or bug (returns 0 int, harmless)')
check('(conjugate 3+4i)', 3-4j)
check('(conjugate 0+0i)', 0j, known='and/or idiom: 0j is falsy, returns x (accidentally right)')
check('(conjugate 5)', 5)
check('(angle 1+i)', math.pi/4)
check('(angle -1)', math.pi)
check('(angle 1)', 0.0)
check('(angle 0+1i)', math.pi/2)

# ------------------------------------------------------------- constructors
check('(complex 1 2)', 1+2j)
check('(complex 1)', 1+0j)
check('(make-rectangular 3 4)', 3+4j)
check('(make-polar 1 0)', 1+0j)
check('(make-polar 2 (/ 3.141592653589793 2))', 2j)
check('(complex "a" 1)', Exception)

# --------------------------------------------------------------- sqrt / log
check('(sqrt 16)', 4.0)
check('(sqrt -4)', 2j)
check('(sqrt -4.0)', 2j)
check('(sqrt -1/4)', 0.5j)
check('(sqrt 3+4i)', 2+1j)
check('(sqrt 0)', 0.0)
check('(sqrt -0.0)', 0.0)
check('(log -1)', 1j*math.pi)
check('(log 1)', 0.0)
check('(log 8 2)', 3.0)
check('(log 0)', Exception)
check('(log 1+i)', cmath.log(1+1j))
check('(log -8 2)', cmath.log(-8)/math.log(2))
check('(exp 0+i)', cmath.exp(1j), known='exp/sin/cos come from math, which rejects complex')
check('(exp (* 3.141592653589793 +i))', -1+0j, known='Euler identity; needs complex-aware exp')
check('(expt -1 0.5)', 1j, known='python (-1)**0.5 gives complex via pow; check lispy expt')
check('(expt +i 2)', -1+0j)
check('(expt 2 +i)', 2**1j)
check('(sin 1+i)', cmath.sin(1+1j), known='sin/cos/tan/atan need cmath for complex')
check('(cos 0+i)', cmath.cos(1j), known='sin/cos/tan/atan need cmath for complex')

# ------------------------------------------------------- ordering must fail
check('(< 1+2i 3)', Exception)
check('(max 1 2+i)', Exception)
check('(> 1+i 0)', Exception)
check('(<= 1 1+0i)', Exception, known='Python has no ordering for complex; lispy may allow or give a cryptic error')

# ----------------------------------------------------- floor/round on complex
check('(floor 1+i)', Exception)
check('(round 1.5+2.5i)', Exception)
check('(even? 2+0i)', Exception)

# ------------------------------------------------------------- printing
check_str('3+4i', '3.0+4.0i')
check_str('#C(1 2)', '1.0+2.0i')
check_str('(* 2 3+4i)', '6.0+8.0i')
check_str("'(1 3+4i)", '(1 3.0+4.0i)')
check_str('(sqrt -4)', '0.0+2.0i')
check_str('-i', '0.0-1.0i')
check_str('(conjugate 3+4i)', '3.0-4.0i')
check_str('(* 1e308 1e308+1i)', '#C(inf 1e+308)')
check_str('(make-polar 1 0)', '1.0+0.0i')
check_str('(string-append "z=" (number->string 3+4i))', '"z=3.0+4.0i"')
check_str('(number->string 3+4i)', '"3.0+4.0i"')

# ------------------------------------------------ epsilon + noise cleanup
import sys as _s
check('epsilon', _s.float_info.epsilon)
check('(> epsilon 0)', True)
check('(= (+ 1 epsilon) 1)', False)
check('(= (+ 1 (/ epsilon 2)) 1)', True)
check_str('(expt -1 0.5)', '0.0+1.0i')
check_str('(exp (* 3.141592653589793 +i))', '-1.0+0.0i')
check_str('(exp (* 6.283185307179586 +i))', '1.0+0.0i')
check_str('(sqrt -1)', '0.0+1.0i')
check_str('1e-300+1e-300i', '1e-300+1e-300i')       # both tiny: must not be zeroed
check_str('1+1e-10i', '1.0+1e-10i')                   # real small part is data, not noise
check_str('3+4i', '3.0+4.0i')
check_str('(* 0.1 3+4i)', '0.30000000000000004+0.4i')
check('(real-part (expt -1 0.5))', 6.123233995736766e-17, known=None)   # stored value is NOT cleaned

# ---------------------------------------------------------- round trip
for z in ['3+4i', '#C(1.5 -2.5)', '-i', '0+0i', '(sqrt -2)']:
    try:
        a = ev(z); b = ev(L.lisp_str(a))
        ok = (a == b)
    except Exception as e:
        ok = False
    if ok: passed += 1
    else: failed += 1; fails.append((f'round-trip {z}', 'equal', 'differs/raised'))
check('(string->number "3+4i")', 3+4j, known='string->number does not understand complex')

# special values
check('(* +inf.0 1+i)', Exception, known='inf*complex = nan parts; just must not crash the REPL')
check('(+ 1+i #C(1 +nan.0))', Exception, known='nan parts')
check('(= 1+i 1+i)', True)
check('(if 0+0i 1 2)', 1)          # 0+0i is truthy in lisp (only #f is false)
check('(if 0 1 2)', 1)
check('(begin (define z 2+3i) (+ z z))', 4+6j)
check('(map (lambda (z) (* z z)) (list 1+i 2i))', [2j, -4+0j])
check('(apply + (list 1+i 2+2i 3+3i))', 6+6j)
check('(vector-ref (vector 1+i 2) 0)', 1+1j)
check('(let loop ((n 0) (acc 0+0i)) (if (= n 3) acc (loop (+ n 1) (+ acc +i))))', 3j)
check('(member 2i (list 1 2i 3))', [2j, 3])

total = passed + failed
print(f"{passed}/{total} passed, {failed} failed   |   known issues: {known_bad} still present, {known_fixed} now pass")
for src, exp, desc in fails:
    print(f"  FAIL  {src}\n        expected {exp!r}; {desc}")
if knowns:
    print("\nKnown issues (not counted as failures):")
    for src, exp, desc, why in knowns:
        print(f"  KNOWN {src}\n        expected {exp!r}; {desc}\n        why: {why}")
sys.exit(1 if failed else 0)
