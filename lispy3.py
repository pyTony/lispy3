from typing import Any, TypeAlias, Callable, Union
from dataclasses import dataclass
import functools
import itertools
import math
import operator as op
import re
import shutil
import sys
import time
import turtle

# --- Types and Data Structures ---
Symbol: TypeAlias = str
Number: TypeAlias = int | float
Atom: TypeAlias = Union[Symbol, Number, 'String', 'Char']
List: TypeAlias = list['Exp']
Exp: TypeAlias = Union[Atom, List, tuple['Exp', ...], dict['Exp', 'Exp']]

@dataclass(frozen=True)
class String:
    """A wrapper to distinguish pure string literals from Lisp symbols."""
    value: str

    def __repr__(self) -> str:
        return self.value

@dataclass(frozen=True)
class Char:
    """A wrapper to distinguish characters from strings and symbols."""
    value: str

    def __repr__(self) -> str:
        return self.value

class LispyError(Exception):
    """User-raised error from within Lisp via (error ...)."""
    pass

class Procedure:
    """A user-defined or wrapped native Lisp/Scheme procedure that knows how to serialize itself."""
    def __init__(self, parms: Union[list[Symbol], Symbol], body: Any, env: 'Env', native_fn: Callable = None, name: str = None):
        self.parms = parms
        self.body = body
        self.env = env
        self.native_fn = native_fn
        self.name = name

    def bind_env(self, args: list[Any]) -> 'Env':
        """Create a local environment supporting standard and variadic (rest) parameters."""
        if isinstance(self.parms, str):
            return Env([self.parms], [list(args)], self.env)
        if '.' in self.parms:
            idx = self.parms.index('.')
            fixed = self.parms[:idx]
            rest_sym = self.parms[idx + 1]
            return Env(fixed + [rest_sym], list(args[:idx]) + [list(args[idx:])], self.env)
        if '&' in self.parms:
            idx = self.parms.index('&')
            fixed = self.parms[:idx]
            rest_sym = self.parms[idx + 1]
            return Env(fixed + [rest_sym], list(args[:idx]) + [list(args[idx:])], self.env)
        return Env(self.parms, list(args), self.env)

    def __call__(self, *args: Any) -> Any:
        if self.native_fn:
            return self.native_fn(*args)
        return eval_exp(self.body, self.bind_env(list(args)))

class Env(dict):
    """An environment for lexical scoping, inheriting from dict."""
    def __init__(self, parms: list[Symbol] = None, args: list[Any] = None, outer: 'Env' = None):
        super().__init__()
        self.outer = outer
        if parms and args is not None:
            self.update(zip(parms, args))

    def find(self, var: Symbol) -> 'Env':
        """Find the innermost environment where var is defined."""
        if var in self:
            return self
        if self.outer is None:
            raise NameError(f"Undefined symbol: {var}")
        return self.outer.find(var)

# --- Macro Table and Gensym State ---
macro_table: dict[Symbol, Procedure] = {}
_gensym_counter = itertools.count(1)

def gensym(prefix: Any = "G__") -> Symbol:
    p = prefix.value if isinstance(prefix, (String, Char)) else str(prefix)
    return Symbol(f"{p}{next(_gensym_counter)}")

# --- Built-in help: (help) lists everything, (help 'name) explains one name ---
HELP_TOPICS: dict[str, list[tuple[str, str]]] = {
    "Special forms (write them as code, quote the name to ask about one: (help 'if))": [
        ("define", "(define name value) or (define (f a b) body...) - give a name to a value or a function"),
        ("set!", "(set! name value) - change an existing variable"),
        ("lambda", "(lambda [a b] body...) - a function; (lambda [a & more] ...) or (lambda args ...) takes any number"),
        ("if", "(if test then else) - the else part may be left out"),
        ("cond", "(cond (test1 exp1...) (test2 exp2...) (else expN...)) - the first true test wins"),
        ("and", "(and e1 e2 ...) - stops at the first false value, else gives the last"),
        ("or", "(or e1 e2 ...) - stops at the first true value"),
        ("begin", "(begin e1 e2 ...) - run each, return the last value"),
        ("let", "(let [a 1 b 2] body...) - local names; later ones may use earlier ones"),
        ("while", "(while test body...) - loop while test is true, no recursion depth used"),
        ("dotimes", "(dotimes [i count] body...) - run body with i = 0, 1, ... count-1"),
        ("try", "(try exp (catch e handler...)) - run exp; on an error, run handler with e = the message"),
        ("quote", "(quote x) or 'x - x itself, not evaluated"),
        ("quasiquote", "`(a ,b ,@c) - a template: ,b puts in the value of b, ,@c splices the list c"),
        ("define-macro", "(define-macro (name parms...) body) - a function that writes code, run before evaluation"),
        ("#t", "#t and #f - true and false. False in a test: #f, 0 and (); everything else is true"),
        ("save", "(save \"name\") - write your definitions to name.lisp"),
        ("load", "(load \"name\") - run name.lisp"),
    ],
    "Lists and sequences": [
        ("car", "(car lst) - first item; same as first. () for an empty list"),
        ("first", "(first lst) - first item (the head)"),
        ("cdr", "(cdr lst) - everything but the first item; same as rest"),
        ("rest", "(rest lst) - everything but the first item (the tail)"),
        ("cons", "(cons x lst) - a new list with x in front"),
        ("list", "(list a b ...) - a list of the values"),
        ("length", "(length x) - number of items in a list or characters in a string"),
        ("null?", "(null? lst) - true for the empty list; same as empty?"),
        ("empty?", "(empty? x) - true for an empty list, string or map"),
        ("append", "(append a b ...) - join lists, or join strings"),
        ("last", "(last lst) - the last item"),
        ("nth", "(nth lst i) - item i, counting from 0; also works on a string"),
        ("reverse", "(reverse lst) - the items backwards; also works on a string"),
        ("range", "(range 5), (range 1 6), (range 0 10 2) - a list of whole numbers"),
        ("seq", "(seq \"abc\") - a string as a list of characters (#\\a #\\b #\\c)"),
        ("map", "(map f lst ...) - a list of (f item) for each item; several lists go side by side"),
        ("filter", "(filter f lst) - the items for which (f item) is true"),
        ("for-each", "(for-each f lst ...) - call f on each item, for its side effects"),
        ("reduce", "(reduce f lst) or (reduce f init lst) - combine the items with f; also fold"),
        ("apply", "(apply f a ... lst) - call f with the items of lst as its arguments"),
        ("sort", "(sort lst) or (sort lst less?) - a sorted copy"),
        ("member", "(member x lst) - the tail of lst starting at x, or #f"),
        ("list?", "(list? x) - true for a list"),
        ("procedure?", "(procedure? x) - true for a function"),
        ("eq?", "(eq? a b) - the same thing (numbers, symbols, strings compare by value)"),
        ("equal?", "(equal? a b) - equal values, lists compared item by item"),
    ],
    "Numbers and comparison": [
        ("+", "(+ a b ...) - add any number of numbers (also plus)"),
        ("-", "(- a b ...) - subtract; (- a) is minus a"),
        ("*", "(* a b ...) - multiply"),
        ("/", "(/ a b ...) - divide, gives a decimal"),
        ("div", "(div a b) - whole-number division rounding down, like Python's //"),
        ("mod", "(mod a b) - what is left over after div, like Python's %; same as modulo"),
        ("divmod", "(divmod a b) - both at once: (div mod), e.g. (divmod 17 5) gives (3 2)"),
        ("quotient", "(quotient a b) - whole-number division rounding toward zero"),
        ("remainder", "(remainder a b) - what is left over after quotient, with the sign of a"),
        ("modulo", "(modulo a b) - remainder with the sign of b; same as mod"),
        ("expt", "(expt a b) - a to the power b, exact for whole numbers"),
        ("gcd", "(gcd a b ...) - greatest common divisor; also lcm, isqrt, factorial, comb from math"),
        ("even?", "(even? n), (odd? n) - true for an even or odd whole number"),
        ("zero?", "(zero? x), (positive? x), (negative? x) - compare with 0"),
        ("integer?", "(integer? x) - true for a whole number, also 3.0"),
        ("exact", "(exact x) - a decimal as a whole number, 3.0 gives 3; (inexact x) the other way"),
        ("=", "(= a b ...) - equal; works on numbers, symbols, strings and characters"),
        ("<", "(< a b ...), also > <= >= - true when each value is in order with the next"),
        ("not", "(not x) - #t if x is #f, 0 or empty, else #f"),
        ("abs", "(abs x) - absolute value"),
        ("min", "(min a b ...) - smallest"),
        ("max", "(max a b ...) - largest"),
        ("round", "(round x) - nearest whole number"),
        ("number?", "(number? x) - true for a number"),
        ("boolean?", "(boolean? x) - true for #t and #f"),
        ("math", "every name in Python's math module: sqrt floor fmod log sin cos pi e ... try (help 'sqrt)"),
    ],
    "Strings and characters": [
        ("str", "(str a b ...) - the values joined as one string"),
        ("format", "(format \"~a is ~s~%\" x y) - ~a value, ~s value as written, ~% newline"),
        ("substring", "(substring s start end) - part of s; end may be left out"),
        ("string-ref", "(string-ref s i) - character i of s"),
        ("upcase", "(upcase s), (downcase s) - change the case"),
        ("split", "(split s) or (split s sep) - a list of the parts"),
        ("list->string", "(list->string chars) - join characters into a string; string->list goes back"),
        ("string->number", "(string->number \"42\") - the number, or #f"),
        ("number->string", "(number->string 42) - the string \"42\"; (number->string 255 16) gives \"ff\""),
        ("string?", "(string? x) - true for a string; also char?, symbol?"),
        ("string->symbol", "(string->symbol \"car\") - the symbol car"),
        ("symbol->string", "(symbol->string 'car) - the string \"car\""),
    ],
    "Maps": [
        ("get", "(get map key) or (get map key default) - look up a key; also (:key map)"),
        ("assoc", "(assoc map k v ...) - a copy of map with the keys set"),
        ("dissoc", "(dissoc map k ...) - a copy of map without the keys"),
        ("keys", "(keys map), (vals map) - the keys or the values as a list"),
        ("contains?", "(contains? map k) - true if map has the key k"),
        ("map?", "(map? x) - true for a map"),
    ],
    "Vectors, time and output": [
        ("make-vector", "(make-vector n fill) - n items, all fill (0 if left out), numbered from 0"),
        ("vector-ref", "(vector-ref v i) - item i of v"),
        ("vector-set!", "(vector-set! v i x) - put x into item i of v"),
        ("clock", "(clock) - seconds as a decimal number, for timing"),
        ("display", "(display a b ...) - print the values with nothing between them, then a new line"),
        ("print", "(print a b ...) - print the values with spaces between them"),
        ("newline", "(newline) - print an empty line"),
        ("pretty-print", "(pretty-print x) - print x indented; also pprint"),
        ("help", "(help) - this list; (help 'name) or (help name) - explain one name"),
        ("eval", "(eval code) - run code held as data, e.g. (eval '(+ 1 2)) gives 3; runs in the global environment"),
        ("read", "(read \"(+ 1 2)\") - turn text into code (data) for eval"),
        ("error", "(error \"message\" ...) - stop with an error; try can catch it"),
        ("gensym", "(gensym) - a new, unused symbol, for macros"),
    ],
    "Turtle graphics": [
        ("turtle", "every name in Python's turtle module: fd bk lt rt pu pd goto ... try (help 'fd)"),
        ("push-pose", "(push-pose) - remember position, heading and pen"),
        ("pop-pose", "(pop-pose) - go back to the last remembered pose, without drawing"),
        ("clear-poses", "(clear-poses) - forget all remembered poses"),
        ("reinit-turtle", "(reinit-turtle) - reopen a closed turtle window; also reset"),
    ],
}

_HELP_INDEX = {name: text for entries in HELP_TOPICS.values() for name, text in entries}
for _alias, _name in {'#f': '#t', 'plus': '+', 'pprint': 'pretty-print', 'reset': 'reinit-turtle',
                      '>': '<', '<=': '<', '>=': '<', 'fold': 'reduce', 'downcase': 'upcase',
                      'string->list': 'list->string', 'vals': 'keys', 'char?': 'string?',
                      'symbol?': 'string?', 'else': 'cond', 'catch': 'try',
                      'odd?': 'even?', 'positive?': 'zero?', 'negative?': 'zero?', 'inexact': 'exact',
                      'exact->inexact': 'exact', 'inexact->exact': 'exact'}.items():
    _HELP_INDEX[_alias] = _HELP_INDEX[_name]

def lisp_help(*args: Any) -> None:
    """(help) lists the built-ins; (help 'name) or (help name) explains one of them."""
    if not args:
        for topic, entries in HELP_TOPICS.items():
            print(f"{topic}:")
            print("  " + " ".join(name for name, _ in entries))
        print("More: docs/QUICK_START.md, docs/LISPY_BY_EXAMPLE.md, docs/QUICK_REFERENCE.md")
        return
    what = args[0]
    if isinstance(what, Procedure):
        if what.native_fn is None:
            print(pretty_print(what, width=60))
            return
        name = what.name
    else:
        name = what.value if isinstance(what, String) else lisp_str(what)
    if name in _HELP_INDEX:
        print(_HELP_INDEX[name])
        return
    for module in (math, turtle):
        obj = getattr(module, name, None)
        doc = obj.__doc__ if callable(obj) else None
        if doc:
            print(f"({name} ...) - from Python's {module.__name__}: {doc.strip().splitlines()[0]}")
            return
    print(f"No help for {name}. Type (help) for the list of built-ins.")

# --- Pretty Printer ---
def pretty_print(exp: Any, indent: int = 0, width: int = 40) -> str:
    """Format an AST or value into an indented string fitting within `width` columns."""
    pad = "  " * indent
    type_name = type(exp).__name__

    if type_name == 'Procedure':
        if exp.native_fn is not None:
            return exp.name if exp.name else "<native-function>"
        parms = '[' + ' '.join(exp.parms) + ']' if isinstance(exp.parms, (list, tuple)) else str(exp.parms)
        if getattr(exp, 'name', None):
            # the body sits two levels in, under (define name / (lambda ...
            body_s = pretty_print(exp.body, indent + 2, width).lstrip()
            return f"(define {exp.name}\n{pad}  (lambda {parms}\n{pad}    {body_s}))"
        body_s = pretty_print(exp.body, indent + 1, width).lstrip()
        return f"(lambda {parms}\n{pad}  {body_s})"

    if type_name in ('String', 'Char'):
        return lisp_str(exp)

    if isinstance(exp, Env):
        return "<env>"

    flat_str = lisp_str(exp)
    if '\n' not in flat_str and (len(flat_str) + len(pad) <= width):
        return flat_str

    if isinstance(exp, tuple):
        if not exp:
            return "[]"
        items = "\n".join(f"{pad}  {pretty_print(x, indent + 1, width).lstrip()}" for x in exp)
        return f"[\n{items}\n{pad}]"

    if isinstance(exp, dict):
        if not exp:
            return "{}"
        pairs = "\n".join(
            f"{pad}  {lisp_str(k)} {pretty_print(v, indent + 1, width).lstrip()}"
            for k, v in exp.items()
        )
        return f"{{\n{pairs}\n{pad}}}"

    if isinstance(exp, list):
        if not exp:
            return "()"

        head = exp[0]

        if head == 'define' and len(exp) >= 3:
            var_name = lisp_str(exp[1])
            val_s = "\n".join(f"{pad}  {pretty_print(e, indent + 1, width).lstrip()}" for e in exp[2:])
            return f"(define {var_name}\n{val_s})"

        if head == 'lambda' and len(exp) >= 3:
            parms_s = lisp_str(exp[1])
            body_s = "\n".join(f"{pad}  {pretty_print(b, indent + 1, width).lstrip()}" for b in exp[2:])
            return f"(lambda {parms_s}\n{body_s})"

        if head == 'if' and len(exp) >= 3:
            test_s = pretty_print(exp[1], indent + 1, width).lstrip()
            conseq_s = pretty_print(exp[2], indent + 1, width).lstrip()
            if len(exp) == 4:
                alt_s = pretty_print(exp[3], indent + 1, width).lstrip()
                return f"(if {test_s}\n{pad}  {conseq_s}\n{pad}  {alt_s})"
            return f"(if {test_s}\n{pad}  {conseq_s})"

        if head == 'let' and len(exp) >= 3:
            bindings_s = pretty_print(exp[1], indent + 1, width).lstrip()
            body_s = "\n".join(f"{pad}  {pretty_print(b, indent + 1, width).lstrip()}" for b in exp[2:])
            return f"(let {bindings_s}\n{body_s})"

        if head == 'begin':
            body_s = "\n".join(f"{pad}  {pretty_print(e, indent + 1, width).lstrip()}" for e in exp[1:])
            return f"(begin\n{body_s})"

        head_s = pretty_print(exp[0], 0, width)
        rest_s = "\n".join(f"{pad}  {pretty_print(e, indent + 1, width).lstrip()}" for e in exp[1:])
        return f"({head_s}\n{rest_s})"

    return lisp_str(exp)

# --- Helper Functions for Workspace Save and Load ---
def save_workspace(filename: str) -> str:
    """Saves only user-defined variables and Lisp Procedures to a file, ignoring Python built-ins."""
    real_filename = filename if filename.endswith('.lisp') else f"{filename}.lisp"
    std = standard_env()
    
    with open(real_filename, 'w', encoding='utf-8') as f:
        for key, value in global_env.items():
            # Skip built-ins, but keep a user's own function even if it reuses a built-in name
            user_fn = isinstance(value, Procedure) and value.native_fn is None
            if (key in std and not user_fn) or key == 'nan':
                continue
            if callable(value) and type(value).__name__ != 'Procedure':
                continue
            # Lists and symbols are data: quote them so loading does not run them as code
            quote = "'" if isinstance(value, (list, str)) and value != [] else ""
            f.write(f"(define {key} {quote}{lisp_str(value)})\n")
            
    return f"Workspace saved to {real_filename}"

def load_workspace(filename: str) -> str:
    """Loads and evaluates all Lisp definitions from a file safely, preventing REPL leaks."""
    real_filename = filename if filename.endswith('.lisp') else f"{filename}.lisp"
    
    with open(real_filename, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    full_program = f"(begin {content})"
    ast = parse(full_program)
    
    defined_symbols = []
    if isinstance(ast, list) and ast and ast[0] == 'begin':
        for exp in ast[1:]:
            if isinstance(exp, list) and len(exp) >= 2 and exp[0] in ('define', 'define-macro'):
                sym = exp[1][0] if isinstance(exp[1], (list, tuple)) else exp[1]
                defined_symbols.append(str(sym))

    _ = eval_exp(expand(ast, toplevel=True), global_env)

    if defined_symbols:
        return f"Workspace loaded from {real_filename}. Defined: {', '.join(defined_symbols)}"
    return f"Workspace loaded from {real_filename}"
_turtle_pose_stack: list[tuple[float, float, float]] = []

def push_pose() -> None:
    """Remember the turtle's position, heading and pen state."""
    _turtle_pose_stack.append((turtle.position(), turtle.heading(), turtle.isdown()))

def pop_pose() -> None:
    """Move the turtle back to the last remembered pose without drawing."""
    if not _turtle_pose_stack:
        raise IndexError("pop-pose: no pose to return to")
    position, heading, pen_down = _turtle_pose_stack.pop()
    turtle.penup()
    turtle.setposition(position)
    turtle.setheading(heading)
    if pen_down:
        turtle.pendown()

def clear_poses() -> None:
    """Forget all remembered poses."""
    _turtle_pose_stack.clear()

def reinit_turtle():
    """Completely recreates the Turtle window if it was closed."""
    turtle.TurtleScreen._RUNNING = True
    try:
        turtle.Screen().bye()  # Clean up any lingering Tk context
    except Exception:
        pass
    turtle.Turtle._screen = None  # Reset singleton reference
    s = turtle.Screen()
    s.setup()
    s.title("Lispy3 Graphics")
    turtle.resetscreen()
    # bye() above leaves turtle's "running" flag False, which would make the very
    # next drawing call raise Terminator again. The new window is alive, so say so.
    turtle.TurtleScreen._RUNNING = True
    return "Turtle window reopened."

# --- Variadic & Primitive Helpers ---
def _unwrap_str(x: Any) -> str:
    if isinstance(x, (String, Char)):
        return x.value
    if x is None or x == []:
        return ""
    return str(x)

def _variadic_sub(*args: Number) -> Number:
    if not args:
        raise TypeError("- requires at least 1 argument")
    if len(args) == 1:
        return -args[0]
    return functools.reduce(op.sub, args)

def _variadic_div(*args: Number) -> Number:
    if not args:
        raise TypeError("/ requires at least 1 argument")
    if len(args) == 1:
        return 1 / args[0]
    return functools.reduce(op.truediv, args)

def _variadic_cmp(cmp_fn: Callable[[Any, Any], bool]) -> Callable[..., bool]:
    def compare(*args: Any) -> bool:
        if len(args) < 2:
            return True
        return all(cmp_fn(args[i], args[i + 1]) for i in range(len(args) - 1))
    return compare

def _lisp_eq(a: Any, b: Any) -> bool:
    if isinstance(a, (String, Char)) and isinstance(b, (String, Char)):
        return type(a) is type(b) and a.value == b.value
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    return a == b

def _quotient(a: Number, b: Number) -> int:
    """Whole-number division rounding toward zero, exact for big whole numbers."""
    if isinstance(a, int) and isinstance(b, int):
        q = abs(a) // abs(b)
        return q if (a < 0) == (b < 0) else -q
    return int(math.trunc(a / b))

def _remainder(a: Number, b: Number) -> Number:
    """What is left over after quotient: a - b * (quotient a b), with the sign of a."""
    if isinstance(a, int) and isinstance(b, int):
        return a - b * _quotient(a, b)
    return math.fmod(a, b)

def _div(a: Number, b: Number) -> Number:
    """Division rounding down, like Python's //; a whole number for whole numbers."""
    return a // b

def _whole(n: Any, name: str) -> int:
    """n as a Python int, or an error naming the procedure that needed a whole number."""
    if isinstance(n, int) and not isinstance(n, bool):
        return n
    if isinstance(n, float) and n.is_integer():
        return int(n)
    raise TypeError(f"{name} needs a whole number, got {lisp_str(n)}")

def _exact(x: Number) -> int:
    """A decimal with no fraction as a whole number: (exact 3.0) gives 3."""
    return _whole(x, 'exact')

_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"

def _number_to_string(n: Number, base: int = 10) -> String:
    """(number->string n) or (number->string n base) for a whole number in base 2 to 36."""
    if base == 10:
        return String(str(n))
    if not 2 <= base <= 36:
        raise ValueError("number->string: base must be from 2 to 36")
    m = _whole(n, 'number->string')
    digits, k = [], abs(m)
    while True:
        k, d = divmod(k, base)
        digits.append(_DIGITS[d])
        if k == 0:
            break
    return String(('-' if m < 0 else '') + ''.join(reversed(digits)))

def _modulo(a: Number, b: Number) -> Number:
    res = a % b
    if isinstance(a, int) and isinstance(b, int):
        return int(res)
    return res

def _member(item: Any, lst: list[Any]) -> Any:
    if not isinstance(lst, (list, tuple)):
        return False
    for i, x in enumerate(lst):
        if _lisp_eq(item, x):
            return list(lst[i:])
    return False

def _reduce_fn(proc: Callable, *args: Any) -> Any:
    if len(args) == 1:
        return functools.reduce(proc, args[0])
    elif len(args) == 2:
        # Support both (reduce proc init lst) and (reduce proc lst init)
        if isinstance(args[0], (list, tuple)) and not isinstance(args[1], (list, tuple)):
            return functools.reduce(proc, args[0], args[1])
        return functools.reduce(proc, args[1], args[0])
    raise TypeError("reduce expects (proc lst) or (proc init lst)")

def _sort_fn(items: list[Any], key_or_cmp: Callable = None) -> list[Any]:
    if key_or_cmp is None:
        return sorted(items, key=lambda x: x.value if isinstance(x, (String, Char)) else x)
    # Try comparator of 2 args, fallback to key function of 1 arg
    try:
        def cmp(a: Any, b: Any) -> int:
            res = key_or_cmp(a, b)
            if isinstance(res, bool):
                return -1 if res else (1 if key_or_cmp(b, a) else 0)
            return int(res)
        return sorted(items, key=functools.cmp_to_key(cmp))
    except TypeError:
        return sorted(items, key=key_or_cmp)

def _string_to_number(s: Any, base: int = 10) -> Any:
    raw = _unwrap_str(s).strip()
    try:
        return int(raw, base)
    except ValueError:
        try:
            return float(raw) if base == 10 else False
        except ValueError:
            return False

def _format_lisp(fmt: Any, *args: Any) -> String:
    raw_fmt = _unwrap_str(fmt)
    out = []
    arg_idx = 0
    i = 0
    while i < len(raw_fmt):
        if raw_fmt[i] == '~' and i + 1 < len(raw_fmt):
            directive = raw_fmt[i + 1].lower()
            if directive == 'a':
                val = args[arg_idx] if arg_idx < len(args) else ""
                arg_idx += 1
                out.append(_unwrap_str(val) if isinstance(val, (String, Char)) else lisp_str(val))
                i += 2
                continue
            elif directive == 's':
                val = args[arg_idx] if arg_idx < len(args) else ""
                arg_idx += 1
                out.append(lisp_str(val))
                i += 2
                continue
            elif directive == '%':
                out.append('\n')
                i += 2
                continue
            elif directive == '~':
                out.append('~')
                i += 2
                continue
        out.append(raw_fmt[i])
        i += 1
    res = "".join(out)
    # Support Python {} formatting if no ~ directives were used
    if '~' not in raw_fmt and '{}' in raw_fmt:
        unwrapped_args = [_unwrap_str(a) if isinstance(a, (String, Char)) else a for a in args]
        res = raw_fmt.format(*unwrapped_args)
    return String(res)

def _first(x: Any) -> Any:
    """(first lst): the head of a list, or the first character of a string; () when empty."""
    if isinstance(x, String):
        return Char(x.value[0]) if x.value else []
    return x[0] if isinstance(x, (list, tuple)) and x else []

def _rest(x: Any) -> Any:
    """(rest lst): all but the head of a list, or of a string; () when empty."""
    if isinstance(x, String):
        return String(x.value[1:]) if x.value else []
    return list(x[1:]) if isinstance(x, (list, tuple)) else []

def _append(*items: Any) -> Any:
    """(append a b ...) joins lists, or joins strings when every argument is a string."""
    if items and all(isinstance(x, (String, str)) for x in items):
        return String("".join(_unwrap_str(x) for x in items))
    return [elem for lst in items for elem in lst]

def _assoc(d: dict, *kvs: Any) -> dict:
    if len(kvs) % 2 != 0:
        raise ValueError("assoc requires an even number of key-value arguments")
    new_d = dict(d) if isinstance(d, dict) else {}
    for i in range(0, len(kvs), 2):
        new_d[kvs[i]] = kvs[i + 1]
    return new_d

def _dissoc(d: dict, *keys: Any) -> dict:
    new_d = dict(d) if isinstance(d, dict) else {}
    for k in keys:
        new_d.pop(k, None)
    return new_d

# --- Standard Environment Definitions ---
def standard_env() -> Env:
    """Create a global environment where ALL operations are wrapped inside Procedure objects."""
    env = Env()
    
    # 1. Wrap math library functions
    for key, value in vars(math).items():
        if callable(value):
            env[key] = Procedure(parms=['*args'], body=None, env=env, native_fn=value, name=key)
        else:
            env[key] = value
            
    # 2. Core Primitives (including all TODO items)
    primitives = {
        # Variadic Arithmetic & Numbers
        '+': lambda *args: sum(args, 0),
        'plus': lambda *args: sum(args, 0),
        '-': _variadic_sub,
        '*': lambda *args: functools.reduce(op.mul, args, 1),
        '/': _variadic_div,
        'quotient': _quotient,
        'remainder': _remainder,
        'modulo': _modulo,
        'div': _div,
        'mod': _modulo,
        'divmod': lambda a, b: [_div(a, b), _modulo(a, b)],
        'even?': lambda n: _whole(n, 'even?') % 2 == 0,
        'odd?': lambda n: _whole(n, 'odd?') % 2 == 1,
        'zero?': lambda x: x == 0,
        'positive?': lambda x: x > 0,
        'negative?': lambda x: x < 0,
        'integer?': lambda x: isinstance(x, int) and not isinstance(x, bool) or isinstance(x, float) and x.is_integer(),
        'exact': _exact,
        'inexact': float,
        'exact->inexact': float,
        'inexact->exact': _exact,
        'expt': pow,
        'abs': abs,
        'min': min,
        'max': max,
        'round': round,

        # Variadic Comparisons
        '>': _variadic_cmp(op.gt),
        '<': _variadic_cmp(op.lt),
        '>=': _variadic_cmp(op.ge),
        '<=': _variadic_cmp(op.le),
        '=': _variadic_cmp(_lisp_eq),
        'not': op.not_,

        # Type & Equality Predicates
        'null?': lambda x: x == [],
        'empty?': lambda x: len(_unwrap_str(x) if isinstance(x, String) else x) == 0 if isinstance(x, (list, tuple, dict, str, String)) else False,
        'number?': lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
        'symbol?': lambda x: isinstance(x, str),
        'string?': lambda x: isinstance(x, String),
        'char?': lambda x: isinstance(x, Char),
        'list?': lambda x: isinstance(x, list),
        'vector?': lambda x: isinstance(x, tuple),
        'map?': lambda x: isinstance(x, dict) and not isinstance(x, Env),
        'procedure?': lambda x: isinstance(x, Procedure) or callable(x),
        'boolean?': lambda x: isinstance(x, bool),
        'eq?': lambda a, b: _lisp_eq(a, b) if isinstance(a, (int, float, str, String, Char, bool)) else (a is b),
        'equal?': _lisp_eq,

        # Lists & Sequences
        'append': _append,
        'car': _first,
        'cdr': _rest,
        'cons': lambda x, y: [x] + (list(y) if isinstance(y, tuple) else (y if isinstance(y, list) else [y])),
        'length': lambda x: len(x.value) if isinstance(x, String) else len(x),
        'list': lambda *x: list(x),
        'first': _first,
        'rest': _rest,
        'last': lambda x: Char(x.value[-1]) if isinstance(x, String) and x.value else (x[-1] if isinstance(x, (list, tuple)) and x else []),
        'nth': lambda lst, idx: lst[idx] if isinstance(lst, (list, tuple)) else (Char(lst.value[idx]) if isinstance(lst, String) else []),
        'reverse': lambda x: list(reversed(x)) if isinstance(x, (list, tuple)) else (String(x.value[::-1]) if isinstance(x, String) else []),
        'range': lambda *args: list(range(*args)),
        'map': lambda proc, *lists: list(map(proc, *lists)),
        'filter': lambda proc, items: list(filter(proc, items)),
        'for-each': lambda proc, *lists: (list(map(proc, *lists)), None)[1],
        'reduce': _reduce_fn,
        'fold': _reduce_fn,
        'apply': lambda proc, *args: proc(*(list(args[:-1]) + list(args[-1]))),
        'sort': _sort_fn,
        'member': _member,
        'seq': lambda x: [Char(c) for c in x.value] if isinstance(x, String) else ([Char(c) for c in x] if isinstance(x, str) else list(x)),

        # Strings
        'str': lambda *args: String("".join(_unwrap_str(a) for a in args)),
        'substring': lambda s, start, end=None: String(_unwrap_str(s)[start:end]),
        'string-ref': lambda s, k: Char(_unwrap_str(s)[k]),
        'upcase': lambda s: String(_unwrap_str(s).upper()),
        'downcase': lambda s: String(_unwrap_str(s).lower()),
        'split': lambda s, sep=None: [String(p) for p in _unwrap_str(s).split(_unwrap_str(sep) if sep is not None else None)],
        'list->string': lambda lst: String("".join(_unwrap_str(c) for c in lst)),
        'string->list': lambda s: [Char(c) for c in _unwrap_str(s)],
        'string->number': _string_to_number,
        'number->string': _number_to_string,
        'format': _format_lisp,

        # Maps / Dictionaries
        'get': lambda collection, key, default=[]: collection.get(key, default) if isinstance(collection, dict) else default,
        'assoc': _assoc,
        'dissoc': _dissoc,
        'keys': lambda d: list(d.keys()) if isinstance(d, dict) else [],
        'vals': lambda d: list(d.values()) if isinstance(d, dict) else [],
        'contains?': lambda d, k: (k in d) if isinstance(d, dict) else False,

        # Meta, I/O, Error & Workspace
        'gensym': gensym,
        'eval': lambda x: eval_exp(expand(x, toplevel=True), global_env),
        'error': lambda *args: (_ for _ in ()).throw(LispyError(" ".join(_unwrap_str(a) for a in args))),
        'print': lambda *args: print(*(_unwrap_str(a) if isinstance(a, (String, Char)) else lisp_str(a) for a in args)),
        'display': lambda *x: print(*(_unwrap_str(a) if isinstance(a, (String, Char)) else lisp_str(a) for a in x), sep=''),
        # Mutable vectors (Python lists) and a timer
        'make-vector': lambda n, fill=0: [fill] * int(n),
        'vector-ref': lambda v, i: v[i],
        'vector-set!': lambda v, i, x: v.__setitem__(i, x),
        'clock': time.perf_counter,
        'newline': lambda: print(),
        'pretty-print': lambda exp: print(pretty_print(exp, width=40)),
        'pprint': lambda exp: print(pretty_print(exp, width=40)),
        'help': lisp_help,
        'read': lambda text: parse(_unwrap_str(text)),
        'string->symbol': lambda text: Symbol(_unwrap_str(text)),
        'symbol->string': lambda sym: String(str(sym)),
        'vector': lambda *x: list(x),
        'push-pose': push_pose,
        'pop-pose': pop_pose,
        'clear-poses': clear_poses,
        'reinit-turtle': reinit_turtle,
        'reset': reinit_turtle,
    }
    
    for key, value in primitives.items():
        env[key] = Procedure(parms=['*args'], body=None, env=env, native_fn=value, name=key)

    # Boolean and Lisp constants
    env['#t'] = True
    env['#f'] = False
    env['true'] = True
    env['false'] = False
    env['nil'] = []
    env['else'] = True

    # 3. Add turtle graphics support dynamically
    def _call_turtle(k: str, *args: Any) -> Any:
        # Unwrap String/Char dataclasses so (title "Tree") or (color "green") get pure Python strings
        clean_args = [a.value if isinstance(a, (String, Char)) else a for a in args]
        was_uninitialized = turtle.Turtle._screen is None
        res = getattr(turtle, k)(*clean_args)
        if was_uninitialized and turtle.Turtle._screen is not None and k != 'title':
            turtle.title("Lispy3 Graphics")
        return res

    for key in turtle.__all__:
        if key in primitives:
            continue
        value = getattr(turtle, key)
        if callable(value):
            env[key] = Procedure(
                parms=['*args'],
                body=None,
                env=env,
                native_fn=lambda *args, k=key: _call_turtle(k, *args),
                name=key
            )
        else:
            env[key] = value

    return env

global_env = standard_env()

# --- Quasiquote and Macro Expansion ---
def is_pair(x: Any) -> bool:
    return isinstance(x, list) and len(x) > 0

def expand_quasiquote(x: Exp) -> Exp:
    """Expand `x into code that constructs x, handling , and ,@."""
    if isinstance(x, tuple):
        return ['apply', 'vector', expand_quasiquote(list(x))]
    if not is_pair(x):
        return ['quote', x]
    if x[0] == 'unquote':
        if len(x) != 2:
            raise SyntaxError("unquote requires 1 argument")
        return x[1]
    if is_pair(x[0]) and x[0][0] == 'unquote-splicing':
        if len(x[0]) != 2:
            raise SyntaxError("unquote-splicing requires 1 argument")
        return ['append', x[0][1], expand_quasiquote(x[1:])]
    return ['cons', expand_quasiquote(x[0]), expand_quasiquote(x[1:])]

def expand(x: Exp, toplevel: bool = False) -> Exp:
    """Walk the AST to expand macros, quasiquotes, and syntactic sugar."""
    if not isinstance(x, list) or len(x) == 0:
        return x

    head = x[0]

    if head == 'quote':
        return x

    if head == 'quasiquote':
        if len(x) != 2:
            raise SyntaxError("quasiquote requires 1 argument")
        return expand(expand_quasiquote(x[1]), toplevel)

    if head == 'define-macro':
        if not toplevel:
            raise SyntaxError("define-macro only allowed at top-level")
        # Support (define-macro (name args...) body...) and (define-macro name (lambda ...))
        if isinstance(x[1], (list, tuple)):
            name = x[1][0]
            parms = list(x[1][1:])
            body = x[2] if len(x) == 3 else ['begin'] + list(x[2:])
            proc = eval_exp(expand(['lambda', parms, body]), global_env)
        else:
            name = x[1]
            proc = eval_exp(expand(x[2]), global_env)
        if not isinstance(proc, Procedure):
            raise TypeError("macro must evaluate to a procedure")
        macro_table[name] = proc
        return None

    if head == 'define':
        # Support shorthand: (define (f x y) body1 body2...)
        if isinstance(x[1], (list, tuple)):
            name = x[1][0]
            parms = list(x[1][1:])
            body = x[2] if len(x) == 3 else ['begin'] + list(x[2:])
            return expand(['define', name, ['lambda', parms, body]], toplevel)
        if len(x) > 3:
            return ['define', x[1], expand(['begin'] + list(x[2:]), False)]
        return ['define', x[1], expand(x[2], False)]

    if head == 'lambda':
        if len(x) < 3:
            raise SyntaxError("lambda requires parameters and a body")
        parms = x[1]
        body = x[2] if len(x) == 3 else ['begin'] + list(x[2:])
        return ['lambda', parms, expand(body, False)]

    if head == 'let':
        if len(x) < 3:
            raise SyntaxError("let requires bindings and a body")
        bindings = x[1]
        expanded_bindings = [
            expand(b, False) if i % 2 == 1 else b
            for i, b in enumerate(bindings)
        ]
        body = x[2] if len(x) == 3 else ['begin'] + list(x[2:])
        return ['let', expanded_bindings, expand(body, False)]

    if head == 'begin':
        if len(x) == 1:
            return None
        return ['begin'] + [expand(e, toplevel) for e in x[1:]]

    # Macro invocation
    if isinstance(head, str) and head in macro_table:
        expanded = macro_table[head](*x[1:])
        return expand(expanded, toplevel)

    return [expand(e, False) for e in x]

SPECIAL_FORMS = frozenset({'quote', 'quasiquote', 'if', 'cond', 'and', 'or', 'define', 'define-macro',
                           'set!', 'lambda', 'begin', 'let', 'dotimes', 'while', 'try', 'save', 'load'})

# --- Evaluation Engine with Proper Tail Call Optimization (TCO) ---
def eval_exp(x: Exp, env: 'Env' = global_env) -> Any:
    """Evaluate an expression in an environment with TCO loop and Structural Pattern Matching."""
    while True:
        # Fast path for the commonest cases: variables and numbers
        kind = type(x)
        if kind is str:
            return x if x.startswith(':') else env.find(x)[x]
        if kind is int or kind is float:
            return x
        # (proc args...): function application, unless the head is a special form,
        # a :keyword lookup or an obj/method call. TCO: a Lisp procedure's body
        # replaces x in this loop instead of growing the Python call stack.
        if kind is list and x:
            proc_exp = x[0]
            if not (type(proc_exp) is str and (proc_exp in SPECIAL_FORMS or proc_exp.startswith(':')
                                               or ('/' in proc_exp and proc_exp != '/'))):
                if type(proc_exp) is str and proc_exp in macro_table:
                    x = macro_table[proc_exp](*x[1:])
                    continue
                proc = eval_exp(proc_exp, env)
                args = [eval_exp(arg, env) for arg in x[1:]]
                if isinstance(proc, Procedure):
                    if proc.native_fn is not None:
                        # If calling `apply`, unpack and trampoline if the target is a Lisp Procedure
                        if proc.name == 'apply' and len(args) >= 2 and isinstance(args[0], Procedure) and args[0].native_fn is None:
                            target_proc = args[0]
                            flat_args = list(args[1:-1]) + list(args[-1])
                            x = target_proc.body
                            env = target_proc.bind_env(flat_args)
                            continue
                        return proc.native_fn(*args)
                    x = proc.body
                    env = proc.bind_env(args)
                    continue
                if callable(proc):
                    return proc(*args)
                hint = " (a string is data; use (string->symbol ...) to make a name)" if isinstance(proc, String) else ""
                raise TypeError(f"{lisp_str(proc)} is not a function{hint}")
        match x:
            case None:
                return None

            case bool():
                return x

            # 1. Clojure-style Keywords: keywords starting with ':' evaluate to themselves
            case str(symbol) if symbol.startswith(':'):
                return x

            # 2. Variable reference
            case str(symbol):
                return env.find(symbol)[symbol]
                
            # 3. Constant numeric literal
            case int() | float():
                return x
                
            # 4. Pure string literals (dataclass String) and Characters (dataclass Char)
            case String() | Char():
                return x
                
            # 5. Clojure-style data Vector [1 2 3] (tuple in Python) -> evaluates its contents
            case tuple(elements):
                return [eval_exp(e, env) for e in elements]
                
            # 6. Clojure-style Map {key val} (dict in Python) -> evaluates values, keeps string keys raw
            case dict(d):
                evaluated_dict = {}
                for k, v in d.items():
                    eval_k = k if isinstance(k, str) else eval_exp(k, env)
                    eval_v = eval_exp(v, env)
                    evaluated_dict[eval_k] = eval_v
                return evaluated_dict

            # 7. (quote exp)
            case ['quote', exp]:
                return exp

            # 7b. (quasiquote exp)
            case ['quasiquote', exp]:
                x = expand_quasiquote(exp)
                continue
                
            # 8. (if test conseq [alt]) - TCO enabled
            case ['if', test, conseq, *alt]:
                if eval_exp(test, env):
                    x = conseq
                else:
                    x = alt[0] if alt else None
                continue

            # 8b. (cond (test1 body1...) (test2 body2...) (else bodyN...)) - TCO enabled
            case ['cond', *clauses]:
                matched = False
                for clause in clauses:
                    if not isinstance(clause, (list, tuple)) or len(clause) == 0:
                        raise SyntaxError(f"Invalid cond clause: {clause}")
                    test_exp = clause[0]
                    is_true = True if test_exp == 'else' else bool(eval_exp(test_exp, env))
                    if is_true:
                        if len(clause) == 1:
                            return eval_exp(test_exp, env) if test_exp != 'else' else True
                        for exp in clause[1:-1]:
                            eval_exp(exp, env)
                        x = clause[-1]
                        matched = True
                        break
                if not matched:
                    return None
                continue

            # 8c. (and exp1 exp2 ...) - Short-circuit & TCO enabled
            case ['and', *exps]:
                if not exps:
                    return True
                for exp in exps[:-1]:
                    val = eval_exp(exp, env)
                    if not val:
                        return val
                x = exps[-1]
                continue

            # 8d. (or exp1 exp2 ...) - Short-circuit & TCO enabled
            case ['or', *exps]:
                if not exps:
                    return False
                for exp in exps[:-1]:
                    val = eval_exp(exp, env)
                    if val:
                        return val
                x = exps[-1]
                continue
                
            # 9. (define var exp) or (define (f x) body...)
            case ['define', target, *rest_exp]:
                if isinstance(target, (list, tuple)):
                    var = target[0]
                    parms = list(target[1:])
                    body = rest_exp[0] if len(rest_exp) == 1 else ['begin'] + list(rest_exp)
                    val = Procedure(parms, expand(body, False), env, name=var)
                    env[var] = val
                    return None
                else:
                    var = str(target)
                    body = rest_exp[0] if len(rest_exp) == 1 else ['begin'] + list(rest_exp)
                    val = eval_exp(expand(body, False), env)
                    if isinstance(val, Procedure) and val.name is None:
                        val.name = var
                    env[var] = val
                    return None

            # 9b. (define-macro ...)
            case ['define-macro', *_]:
                expand(x, toplevel=True)
                return None
                        
            # 10. (set! var exp)
            case ['set!', str(var), exp]:
                env.find(var)[var] = eval_exp(exp, env)
                return None
                
            # 11. (lambda (parms...) body1 body2...)
            case ['lambda', parms, *body_exps]:
                actual_parms = list(parms) if isinstance(parms, tuple) else parms
                body = body_exps[0] if len(body_exps) == 1 else ['begin'] + list(body_exps)
                return Procedure(actual_parms, body, env)

            # 12. (begin exp1 exp2 ... expN) - TCO enabled
            case ['begin', *exps]:
                if not exps:
                    return None
                for exp in exps[:-1]:
                    eval_exp(exp, env)
                x = exps[-1]
                continue

            # 13. (let [var1 val1...] body1 body2...) - TCO enabled
            case ['let', list(bindings) | tuple(bindings), *body_exps]:
                if len(bindings) % 2 != 0:
                    raise SyntaxError("Let bindings must have an even number of elements")
                local_env = Env(outer=env)
                for i in range(0, len(bindings), 2):
                    local_env[bindings[i]] = eval_exp(bindings[i + 1], local_env)
                for exp in body_exps[:-1]:
                    eval_exp(exp, local_env)
                x = body_exps[-1] if body_exps else None
                env = local_env
                continue

            # 13b. (dotimes [var count] body...)
            case ['dotimes', list(spec) | tuple(spec), *body_exps]:
                if len(spec) < 2:
                    raise SyntaxError("dotimes requires [var count]")
                var_sym = spec[0]
                limit = int(eval_exp(spec[1], env))
                result = spec[2] if len(spec) > 2 else None
                loop_env = Env(outer=env)
                for i in range(limit):
                    loop_env[var_sym] = i
                    for b in body_exps:
                        eval_exp(b, loop_env)
                return eval_exp(result, loop_env) if result is not None else None

            # 13c. (while test body...)
            case ['while', test_exp, *body_exps]:
                result = None
                while eval_exp(test_exp, env):
                    for b in body_exps:
                        result = eval_exp(b, env)
                return result

            # 13d. (try exp (catch err_var handler...)) or (try exp handler)
            case ['try', try_exp, *catch_clauses]:
                try:
                    return eval_exp(try_exp, env)
                except (LispyError, Exception) as err:
                    if not catch_clauses:
                        return None
                    clause = catch_clauses[0]
                    msg = String(str(err))
                    if isinstance(clause, (list, tuple)) and len(clause) >= 3 and clause[0] == 'catch':
                        err_var = clause[1]
                        catch_env = Env([err_var], [msg], env)
                        body = clause[2] if len(clause) == 3 else ['begin'] + list(clause[2:])
                        x = body
                        env = catch_env
                        continue
                    elif isinstance(clause, (list, tuple)) and len(clause) == 2 and clause[0] == 'catch':
                        x = clause[1]
                        continue
                    else:
                        x = clause
                        continue

            # 14. Workspace save and load hooks
            case ['save', filename_exp]:
                filename = eval_exp(filename_exp, env)
                fn_str = filename.value if isinstance(filename, String) else str(filename)
                return save_workspace(fn_str)

            case ['load', filename_exp]:
                filename = eval_exp(filename_exp, env)
                fn_str = filename.value if isinstance(filename, String) else str(filename)
                return load_workspace(fn_str)

            # 15. Property list flavor: (:name user)
            case [str(keyword), target_exp] if keyword.startswith(':'):
                target = eval_exp(target_exp, env)
                if isinstance(target, dict):
                    return target.get(keyword, [])
                raise TypeError(f"Cannot lookup keyword {keyword} on non-dictionary object")

            # 16. Python Method Dispatch flavor: obj/method -> obj.method()
            case [str(method_call), *args_exp] if '/' in method_call and method_call != '/':
                obj_name, method_name = method_call.split('/', 1)
                
                if obj_name == 'str' and method_name == 'join':
                    args = [eval_exp(arg, env) for arg in args_exp]
                    if len(args) == 1:
                        seq = args[0]
                        sep = ""
                    else:
                        sep = _unwrap_str(args[0])
                        seq = args[1]
                    joined = sep.join(_unwrap_str(c) for c in (seq if isinstance(seq, (list, tuple)) else [seq]))
                    return String(joined)

                obj = eval_exp(obj_name, env)
                if isinstance(obj, (String, Char)):
                    obj = obj.value
                args = [eval_exp(arg, env) for arg in args_exp]
                native_args = [a.value if isinstance(a, (String, Char)) else a for a in args]
                
                method = getattr(obj, method_name)
                result = method(*native_args)
                
                if isinstance(result, str):
                    return String(result)
                return result

            case _:
                raise SyntaxError(f"Unknown syntax: {x}")

# --- Parsing (Tokenizing and AST Building) ---
def parse(program: str) -> Exp:
    """Read and macro-expand a Lisp expression from a string program."""
    tokens = tokenize(program)
    ast = read_from_tokens(tokens)
    return expand(ast, toplevel=True)

# String literals: """raw text""" (may hold " and newlines, no escapes) or "text" with escapes
STRING_PATTERN = r'"""[\s\S]*?"""|"(?:\\.|[^"\\])*"'
CHAR_PATTERN = r'#\\[a-zA-Z0-9]+;?|#\\.'      # named/hex chars (#\newline, #\x41;) and any single char
TOKEN_RE = re.compile(
    CHAR_PATTERN
    + '|' + STRING_PATTERN
    + r'|;[^\n]*'                         # comment
    + r'|,@'                              # unquote-splicing
    + r"|['`,]"                           # quote, quasiquote, unquote
    + r'|[\[\](){}]'                      # brackets
    + r'|[^\s()\[\]{}"\'`,;]+'            # symbols and numbers
)

def tokenize(chars: str) -> list[str]:
    """Convert a string into a list of tokens, handling comments, quotes, quasiquotes, and strings."""
    return [t for t in TOKEN_RE.findall(chars) if not t.startswith(';')]

def read_from_tokens(tokens: list[str]) -> Exp:
    """Read an expression from a sequence of tokens with automatic closing parentheses."""
    if not tokens:
        raise SyntaxError("Unexpected EOF while reading")
        
    token = tokens.pop(0)
    
    if token == '(':
        L = []
        while tokens and tokens[0] != ')':
            if tokens[0] in (']', '}'): 
                break 
            L.append(read_from_tokens(tokens))
        if tokens and tokens[0] == ')':
            tokens.pop(0)
        return L
        
    elif token == '[':
        L = []
        while tokens and tokens[0] != ']':
            if tokens[0] in (')', '}'): 
                break
            L.append(read_from_tokens(tokens))
        if tokens and tokens[0] == ']':
            tokens.pop(0)
        return tuple(L)
        
    elif token == '{':
        D = {}
        while tokens and tokens[0] != '}':
            if tokens[0] in (')', ']'): 
                break
            key = read_from_tokens(tokens)
            if not tokens or tokens[0] == '}':
                break
            val = read_from_tokens(tokens)
            D[tuple(key) if isinstance(key, list) else key] = val
            
        if tokens and tokens[0] == '}':
            tokens.pop(0)
        return D
        
    elif token in (')', ']', '}'):
        raise SyntaxError(f"Unexpected closing bracket: {token}")
    elif token == "'":
        return ['quote', read_from_tokens(tokens)]
    elif token == '`':
        return ['quasiquote', read_from_tokens(tokens)]
    elif token == ',':
        return ['unquote', read_from_tokens(tokens)]
    elif token == ',@':
        return ['unquote-splicing', read_from_tokens(tokens)]
    else:
        return atom(token)

def _unescape_string(raw: str) -> str:
    """Process standard, hex (\\x41; or \\x41), and unicode (\\u00e4) escapes in string literals."""
    def replace_match(m: re.Match) -> str:
        seq = m.group(0)
        simple = {'\\n': '\n', '\\t': '\t', '\\r': '\r', '\\"': '"', '\\\\': '\\', '\\0': '\0'}
        if seq in simple:
            return simple[seq]
        if seq.startswith('\\x'):
            hex_digits = seq[2:].rstrip(';')
            return chr(int(hex_digits, 16))
        if seq.startswith('\\u'):
            return chr(int(seq[2:], 16))
        if seq.startswith('\\U'):
            return chr(int(seq[2:], 16))
        return seq[1:]

    return re.sub(r'\\(?:x[0-9a-fA-F]+;?|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|.)', replace_match, raw)

def atom(token: str) -> Atom:
    """Numbers become numbers, "strings" become String, #\\c become Char, others are symbols."""
    if token == '#t':
        return True
    if token == '#f':
        return False
    if len(token) >= 6 and token.startswith('"""') and token.endswith('"""'):
        return String(token[3:-3])
    if len(token) >= 2 and token.startswith('"') and token.endswith('"'):
        return String(_unescape_string(token[1:-1]))
    if token.startswith('#\\'):
        char_map = {
            '#\\newline': '\n',
            '#\\space': ' ',
            '#\\tab': '\t',
            '#\\return': '\r',
            '#\\nul': '\0',
            '#\\null': '\0',
        }
        lower_tok = token.lower()
        if lower_tok in char_map:
            return Char(char_map[lower_tok])
        if lower_tok.startswith('#\\x') and len(token) > 3:
            try:
                return Char(chr(int(token[3:].rstrip(';'), 16)))
            except ValueError:
                pass
        if lower_tok.startswith('#\\u') and len(token) > 3:
            try:
                return Char(chr(int(token[3:].rstrip(';'), 16)))
            except ValueError:
                pass
        return Char(token[2:])
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return Symbol(token)

# --- ANSI Color Codes for Terminal Clarity ---
COLOR_RESET = "\033[0m"
COLOR_PROMPT = "\033[94m"   # Bright Blue for 'lis.py>'
COLOR_RESULT = "\033[92m"   # Bright Green for successful output
COLOR_ERROR = "\033[91m"    # Bright Red for errors
COLOR_INFO = "\033[96m"     # Cyan for greeting/status text

RECURSION_HINT = ("recursion too deep (a few hundred nested calls is the limit; tail calls are free). "
                  "Use while, map or filter for long lists and big counts.")

def count_balance(text: str) -> int:
    """Return the balance of opening vs closing brackets, ignoring strings and comments.

    An unfinished string counts as one open bracket, so the REPL keeps reading
    the lines of a multi-line string.
    """
    cleaned = re.sub(CHAR_PATTERN + '|' + STRING_PATTERN + r'|;[^\n]*', '', text)
    if '"' in cleaned:
        return 1
    opens = cleaned.count('(') + cleaned.count('[') + cleaned.count('{')
    closes = cleaned.count(')') + cleaned.count(']') + cleaned.count('}')
    return max(0, opens - closes)

_CLOSER = {'(': ')', '[': ']', '{': '}'}
_OPENER = {')': '(', ']': '[', '}': '{'}

def missing_closers(text: str) -> str:
    """Return the closing brackets the reader adds by itself at the end of `text`.

    "(+ 1 [2 (* 3 4" gives ")])". Strings, characters and comments are skipped.
    """
    stack = []
    for token in TOKEN_RE.findall(text):
        if token in _CLOSER:
            stack.append(token)
        elif token in _OPENER:
            # A wrong closer also ends the inner brackets, as read_from_tokens does
            while stack and stack[-1] != _OPENER[token]:
                stack.pop()
            if stack:
                stack.pop()
    return ''.join(_CLOSER[c] for c in reversed(stack))

def close_position(text: str) -> int:
    """Offset just after the last code token, where missing closers go (before a trailing ; comment)."""
    end = 0
    for m in TOKEN_RE.finditer(text):
        if not m.group().startswith(';'):
            end = m.end()
    return end

def auto_close(text: str) -> tuple[str, str]:
    """Return (text with the missing closers written in, the closers added)."""
    closers = missing_closers(text)
    if not closers:
        return text, ''
    pos = close_position(text)
    return text[:pos] + closers + text[pos:], closers

# --- Interaction and REPL Printing ---
def lisp_str(exp: Any) -> str:
    """Convert a Python object back into a Lisp-readable string format, handling custom types safely."""
    type_name = type(exp).__name__
    
    if exp is True:
        return "#t"
    if exp is False:
        return "#f"
    if type_name == 'Procedure':
        if exp.native_fn is not None:
            return exp.name if exp.name else "<native-function>"
        parms_repr = lisp_str(tuple(exp.parms)) if isinstance(exp.parms, list) else str(exp.parms)
        return f"(lambda {parms_repr} {lisp_str(exp.body)})"
    elif type_name == 'String':
        escaped = exp.value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        return f'"{escaped}"'
    elif type_name == 'Char':
        reverse_char_map = {'\n': '#\\newline', ' ': '#\\space', '\t': '#\\tab', '\r': '#\\return', '\0': '#\\nul'}
        if exp.value in reverse_char_map:
            return reverse_char_map[exp.value]
        return f"#\\{exp.value}"
    elif isinstance(exp, list):
        return '(' + ' '.join(map(lisp_str, exp)) + ')'
    elif isinstance(exp, tuple):
        return '[' + ' '.join(map(lisp_str, exp)) + ']'
    elif isinstance(exp, dict):
        pairs = [f"{lisp_str(k)} {lisp_str(v)}" for k, v in exp.items()]
        return '{' + ' '.join(pairs) + '}'
    return str(exp)

RUNTIME_ERRORS = (SyntaxError, NameError, TypeError, ZeroDivisionError, FileNotFoundError,
                  LispyError, ValueError, IndexError, KeyError, AttributeError)

# --- Tab completion ---
# Characters that end a name when completing: brackets, quotes, spaces and comments.
COMPLETION_DELIMS = " \t\n()[]{}'\"`,;@"

def completion_candidates(env: 'Env' = global_env) -> set[str]:
    """Every name worth completing: special forms, global names and the :keywords used in global maps."""
    names = set(SPECIAL_FORMS) | {'exit'}
    names.update(k for k in env if not k.startswith('_'))
    for value in list(env.values()):
        if isinstance(value, dict):
            names.update(k for k in value if isinstance(k, str) and k.startswith(':'))
    return names

def complete_names(prefix: str, env: 'Env' = global_env) -> list[str]:
    """The sorted names that start with `prefix`, e.g. "str" gives ["str", "string->symbol", ...]."""
    return sorted(n for n in completion_candidates(env) if n.startswith(prefix))

def setup_completion() -> bool:
    """Turn on Tab completion and line history in the REPL. Returns False when readline is missing.

    readline comes with Python on Linux and macOS; on Windows install it with
    `pip install pyreadline3`.
    """
    try:
        import readline
    except ImportError:
        return False
    matches: list[str] = []

    def completer(text: str, state: int) -> str | None:
        nonlocal matches
        if state == 0:
            matches = complete_names(text)
        return matches[state] if state < len(matches) else None

    readline.set_completer(completer)
    readline.set_completer_delims(COMPLETION_DELIMS)
    if 'libedit' in (getattr(readline, '__doc__', '') or ''):
        readline.parse_and_bind("bind ^I rl_complete")   # macOS
    else:
        readline.parse_and_bind("tab: complete")
    return True

def repl_str(val: Any, width: int | None = None) -> str:
    """A REPL result: on one line when it fits the terminal, otherwise pretty-printed."""
    if width is None:
        width = shutil.get_terminal_size().columns - 1
    flat = lisp_str(val)
    return flat if len(flat) <= width else pretty_print(val, width=width)

def repl(prompt: str = "lispy3> ") -> None:
    """An interactive Read-Eval-Print Loop showing open bracket count."""
    completion = setup_completion()
    print(f"{COLOR_INFO}Modern Python 3 Lispy Interpreter Started.{COLOR_RESET}")
    print(f"{COLOR_INFO}Type (help) for the built-ins, 'exit' to quit. Unclosed paren depth is shown in prompt.{COLOR_RESET}")
    if completion:
        print(f"{COLOR_INFO}Tab completes a name or :keyword.{COLOR_RESET}\n")
    else:
        print(f"{COLOR_INFO}For Tab completion: pip install pyreadline3{COLOR_RESET}\n")
    
    env = global_env
    # readline must be told the colour codes take no room, or long lines wrap wrongly
    hide = ("\001", "\002") if completion and sys.platform != "win32" else ("", "")
    color_prompt, color_reset = f"{hide[0]}{COLOR_PROMPT}{hide[1]}", f"{hide[0]}{COLOR_RESET}{hide[1]}"
    colored_prompt = f"{color_prompt}{prompt}{color_reset}"
    
    buffer = ""
    
    while True:
        try:
            depth = count_balance(buffer) if buffer else 0
            
            if depth > 0:
                current_prompt = f"{color_prompt}... ({depth})> {color_reset}"
            else:
                current_prompt = colored_prompt

            line = input(current_prompt)
            
            if not buffer and not line.strip():
                continue
                
            if not buffer and line.strip().lower() == 'exit':
                print(f"{COLOR_INFO}Goodbye!{COLOR_RESET}")
                break
                
            buffer = f"{buffer}\n{line}" if buffer else line
            
            if count_balance(buffer) > 0:
                continue
                
            ast = parse(buffer)
            buffer = ""
            val = eval_exp(ast, env)
            
            if val is not None:
                print(f"{COLOR_RESULT}{repl_str(val)}{COLOR_RESET}")
        except turtle.Terminator:
            buffer = ""
            print(f"{COLOR_ERROR}Error: Turtle window was closed. Call (reinit-turtle) to reopen.{COLOR_RESET}")
        except RUNTIME_ERRORS as e:
            buffer = ""
            print(f"{COLOR_ERROR}Error: {e}{COLOR_RESET}")
        except RecursionError:
            buffer = ""
            print(f"{COLOR_ERROR}Error: {RECURSION_HINT}{COLOR_RESET}")
        except (KeyboardInterrupt, EOFError):
            print(f"\n{COLOR_INFO}Goodbye!{COLOR_RESET}")
            break

def run_file(filename: str) -> bool:
    """Run a Lisp program file like a script. Returns True if it finished without error."""
    try:
        load_workspace(filename)
        return True
    except turtle.Terminator:
        print(f"{COLOR_ERROR}Error: Turtle window was closed.{COLOR_RESET}", file=sys.stderr)
    except RUNTIME_ERRORS as e:
        print(f"{COLOR_ERROR}Error: {e}{COLOR_RESET}", file=sys.stderr)
    except RecursionError:
        print(f"{COLOR_ERROR}Error: {RECURSION_HINT}{COLOR_RESET}", file=sys.stderr)
    return False

def hold_turtle_window() -> None:
    """If the program drew with turtle, keep the window open until the user closes it."""
    if turtle.Turtle._screen is not None:
        try:
            turtle.mainloop()
        except turtle.Terminator:
            pass

if __name__ == "__main__":
    # python lispy3.py            -> REPL
    # python lispy3.py prog.lisp  -> run prog.lisp, keep a turtle window open, then exit
    # python lispy3.py -i prog.lisp -> run prog.lisp, then stay in the REPL
    #                                  (-i may also come after the file name)
    args = sys.argv[1:]
    interactive = '-i' in args
    args = [a for a in args if a != '-i']
    if args:
        ok = run_file(args[0])
        if interactive:
            repl()
        elif ok:
            hold_turtle_window()
        else:
            sys.exit(1)
    else:
        repl()
