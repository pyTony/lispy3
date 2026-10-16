
from typing import Any, TypeAlias, Callable, Union
from dataclasses import dataclass
import math
import operator as op
import re
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
    
class Procedure:
    """A user-defined or wrapped native Lisp/Scheme procedure that knows how to serialize itself."""
    def __init__(self, parms: list[Symbol], body: Any, env: 'Env', native_fn: Callable = None, name: str = None):
        self.parms = parms
        self.body = body
        self.env = env
        self.native_fn = native_fn  # Säilytetään alkuperäinen Python-funktio, jos kyseessä on natiivifunktio
        self.name = name            # Natiivifunktion nimi (esim. 'log' tai '+')

    def __call__(self, *args: Any) -> Any:
        # Jos kyseessä on kääritty natiivifunktio, ajetaan se suoraan Pythonissa
        if self.native_fn:
            return self.native_fn(*args)
        # Muuten ajetaan Lisp-funktio luomalla sille oma paikallinen skooppi
        return eval_exp(self.body, Env(self.parms, list(args), self.env))
    
class Env(dict):
    """An environment for lexical scoping, inheriting from dict."""
    def __init__(self, parms: list[Symbol] = None, args: list[Any] = None, outer: 'Env' = None):
        super().__init__()
        self.outer = outer
        if parms and args:
            self.update(zip(parms, args))

    def find(self, var: Symbol) -> 'Env':
        """Find the innermost environment where var is defined."""
        if var in self:
            return self
        if self.outer is None:
            raise NameError(f"Undefined symbol: {var}")
        return self.outer.find(var)

def string_literal(text: str) -> str:
    """Write text as a Lispy string literal that reads back as the same text."""
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'

def pretty_print(exp: Any, indent: int = 0, width: int = 40) -> str:
    """Format an AST or value into an indented string fitting within `width` columns."""
    pad = "  " * indent
    type_name = type(exp).__name__

    # 1. Native / User Procedures (Named or Lambdas)
    if type_name == 'Procedure':
        if exp.native_fn is not None:
            return exp.name if exp.name else "<native-function>"
        parms = '[' + ' '.join(exp.parms) + ']'
        body_s = pretty_print(exp.body, indent + 1, width).lstrip()
        # If the procedure was defined with a name, format as (define name (lambda ...))
        if getattr(exp, 'name', None):
            return f"(define {exp.name}\n{pad}  (lambda {parms}\n{pad}    {body_s}))"
        return f"(lambda {parms}\n{pad}  {body_s})"

    # 2. String and Character Literals
    if type_name == 'String':
        return string_literal(exp.value)
    if type_name == 'Char':
        reverse_char_map = {'\n': '#\\newline', ' ': '#\\space', '\t': '#\\tab'}
        return reverse_char_map.get(exp.value, f"#\\{exp.value}")

    # 3. Guard against cyclic inspection of lexical Environments
    if isinstance(exp, Env):
        return "<env>"

    # 4. Check flat string length first (avoids line breaks if short enough)
    flat_str = lisp_str(exp)
    if '\n' not in flat_str and (len(flat_str) + len(pad) <= width):
        return flat_str

    # 5. Vectors [...]
    if isinstance(exp, tuple):
        if not exp:
            return "[]"
        items = "\n".join(f"{pad}  {pretty_print(x, indent + 1, width).lstrip()}" for x in exp)
        return f"[\n{items}\n{pad}]"

    # 6. Maps {...}
    if isinstance(exp, dict):
        if not exp:
            return "{}"
        pairs = "\n".join(
            f"{pad}  {lisp_str(k)} {pretty_print(v, indent + 1, width).lstrip()}"
            for k, v in exp.items()
        )
        return f"{{\n{pairs}\n{pad}}}"

    # 7. Lists (...) including special forms
    if isinstance(exp, list):
        if not exp:
            return "()"

        head = exp[0]

        # Data lists: fill atoms into rows instead of one item per line
        if all(not isinstance(e, (list, tuple, dict)) and type(e).__name__ != 'Procedure' for e in exp) \
                and not (isinstance(head, str) and head in ('define', 'lambda', 'if', 'let', 'begin')):
            room = max(width - len(pad) - 2, 10)
            rows, cur = [], ""
            for e in exp:
                item = pretty_print(e, 0, width)
                if cur and len(cur) + 1 + len(item) > room:
                    rows.append(cur)
                    cur = item
                else:
                    cur = f"{cur} {item}" if cur else item
            rows.append(cur)
            body = "\n".join(f"{pad}  {r}" for r in rows)
            return f"(\n{body}\n{pad})"

        # Data list whose first item is not a symbol: one item per line
        if not isinstance(head, str):
            items = "\n".join(f"{pad}  {pretty_print(x, indent + 1, width).lstrip()}" for x in exp)
            return f"(\n{items}\n{pad})"

        # Explicit define handling: (define var val)
        if head == 'define' and len(exp) == 3:
            var_name = lisp_str(exp[1])
            val_s = pretty_print(exp[2], indent + 1, width).lstrip()
            return f"(define {var_name}\n{pad}  {val_s})"

        # (lambda [params] body)
        if head == 'lambda' and len(exp) >= 3:
            parms_s = lisp_str(exp[1])
            body_s = "\n".join(f"{pad}  {pretty_print(b, indent + 1, width).lstrip()}" for b in exp[2:])
            return f"(lambda {parms_s}\n{body_s})"

        # (if test conseq alt)
        if head == 'if' and len(exp) == 4:
            test_s = pretty_print(exp[1], indent + 1, width).lstrip()
            conseq_s = pretty_print(exp[2], indent + 1, width).lstrip()
            alt_s = pretty_print(exp[3], indent + 1, width).lstrip()
            return f"(if {test_s}\n{pad}  {conseq_s}\n{pad}  {alt_s})"

        # (let [bindings] body)
        if head == 'let' and len(exp) >= 3:
            bindings_s = pretty_print(exp[1], indent + 1, width).lstrip()
            body_s = "\n".join(f"{pad}  {pretty_print(b, indent + 1, width).lstrip()}" for b in exp[2:])
            return f"(let {bindings_s}\n{body_s})"

        # (begin ...)
        if head == 'begin':
            body_s = "\n".join(f"{pad}  {pretty_print(e, indent + 1, width).lstrip()}" for e in exp[1:])
            return f"(begin\n{body_s})"

        # Generic function application / compound lists
        head_s = pretty_print(exp[0], 0, width)
        rest_s = "\n".join(f"{pad}  {pretty_print(e, indent + 1, width).lstrip()}" for e in exp[1:])
        return f"({head_s}\n{rest_s})"

    # 8. Atoms (Symbols, Numbers, #t and #f)
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
                
            # Jos kyseessä on jokin Pythonin oma funktio (esim. log), jätetään se tallentamatta
            if callable(value) and type(value).__name__ != 'Procedure':
                continue
                
            # Kirjoitetaan puhdasta Lisp-koodia tiedostoon
            f.write(f"(define {key} {lisp_str(value)})\n")
            
    return f"Workspace saved to {real_filename}"

def load_workspace(filename: str) -> str:
    """Loads and evaluates all Lisp definitions from a file safely, preventing REPL leaks."""
    real_filename = filename if filename.endswith('.lisp') else f"{filename}.lisp"
    
    with open(real_filename, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    # Kääritään tiedosto yhteen begin-lohkoon
    full_program = f"(begin {content})"
    
    ast = parse(full_program)
    
    # Extract defined symbols
    defined_symbols = []
    if isinstance(ast, list) and ast and ast[0] == 'begin':
        for exp in ast[1:]:
            if isinstance(exp, list) and len(exp) >= 2 and exp[0] == 'define':
                defined_symbols.append(exp[1])

    # Ajetaan koodi globaalissa ympäristössä.
    # Kaapataan tulos muuttujaan, jotta se ei vuoda REPLin suoraan syötteeseen!
    _ = eval_exp(ast, global_env)

    if defined_symbols:
        return f"Workspace loaded from {real_filename}. Defined: {', '.join(defined_symbols)}"
    return f"Workspace loaded from {real_filename}"

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
    turtle.resetscreen()
    # bye() above leaves turtle's "running" flag False, which would make the very
    # next drawing call raise Terminator again. The new window is alive, so say so.
    turtle.TurtleScreen._RUNNING = True
    return "Turtle window reopened."

# --- Turtle poses, for the [ and ] of branching L-systems ---
_pose_stack: list = []

def push_pose() -> None:
    """Remember the turtle's position, heading and pen state."""
    _pose_stack.append((turtle.position(), turtle.heading(), turtle.isdown()))

def pop_pose() -> None:
    """Move the turtle back to the last remembered pose without drawing."""
    if not _pose_stack:
        raise IndexError("pop-pose: no pose to return to")
    position, heading, pen_down = _pose_stack.pop()
    turtle.penup()
    turtle.setposition(position)
    turtle.setheading(heading)
    if pen_down:
        turtle.pendown()

def clear_poses() -> None:
    """Forget all remembered poses."""
    _pose_stack.clear()

# --- Built-in help: (help) lists everything, (help 'name) explains one name ---
HELP_TOPICS: dict[str, list[tuple[str, str]]] = {
    "Special forms (write them as code, quote the name to ask about one: (help 'if))": [
        ("define", "(define name value) - give a name to a value or a lambda"),
        ("set!", "(set! name value) - change an existing variable"),
        ("lambda", "(lambda [a b] body) - a function; body is ONE expression, use begin for more"),
        ("if", "(if test then else) - the else part is required"),
        ("begin", "(begin e1 e2 ...) - run each, return the last value"),
        ("let", "(let [a 1 b 2] body) - local names for one body"),
        ("while", "(while test body...) - loop while test is true, no recursion depth used"),
        ("quote", "(quote x) or 'x - x itself, not evaluated"),
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
        ("empty?", "(empty? lst) - true for the empty list"),
        ("append", "(append a b) - join two lists or two strings"),
        ("seq", "(seq \"abc\") - a string as a list of characters (#\\a #\\b #\\c)"),
        ("map", "(map f lst) - a list of (f item) for each item"),
        ("filter", "(filter f lst) - the items for which (f item) is true"),
        ("get", "(get map key) - look up a key in a {map}; also (:key map)"),
    ],
    "Numbers and comparison": [
        ("+", "(+ a b) - add; numbers only, exactly two arguments (also plus)"),
        ("-", "(- a b) - subtract, two arguments"),
        ("*", "(* a b) - multiply, two arguments"),
        ("/", "(/ a b) - divide, two arguments, gives a decimal"),
        ("=", "(= a b) - equal; works on numbers, symbols, strings and characters"),
        ("<", "(< a b), also > <= >= - compare two values"),
        ("not", "(not x) - #t if x is #f, 0 or empty, else #f"),
        ("abs", "(abs x) - absolute value"),
        ("min", "(min a b ...) - smallest"),
        ("max", "(max a b ...) - largest"),
        ("round", "(round x) - nearest whole number"),
        ("number?", "(number? x) - true for a number"),
        ("symbol?", "(symbol? x) - true for a symbol (and for the text from str)"),
        ("string?", "(string? x) - true for a string"),
        ("str", "(str x) - x as text"),
        ("math", "every name in Python's math module: sqrt floor fmod log sin cos pi e ... try (help 'sqrt)"),
    ],
    "Vectors, time and output": [
        ("make-vector", "(make-vector n fill) - n items, all fill (0 if left out), numbered from 0"),
        ("vector-ref", "(vector-ref v i) - item i of v"),
        ("vector-set!", "(vector-set! v i x) - put x into item i of v"),
        ("clock", "(clock) - seconds as a decimal number, for timing"),
        ("display", "(display a b ...) - print the values with nothing between them"),
        ("pretty-print", "(pretty-print x) - print x indented; also pprint"),
        ("help", "(help) - this list; (help 'name) or (help name) - explain one name"),
        ("eval", "(eval code) - run code held as data, e.g. (eval '(+ 1 2)) gives 3; runs in the global environment"),
        ("read", "(read \"(+ 1 2)\") - turn text into code (data) for eval"),
        ("string->symbol", "(string->symbol \"car\") - the symbol car"),
        ("symbol->string", "(symbol->string 'car) - the string \"car\""),
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
_HELP_INDEX.update({'#f': _HELP_INDEX['#t'], 'plus': _HELP_INDEX['+'], 'pprint': _HELP_INDEX['pretty-print'],
                    'reset': _HELP_INDEX['reinit-turtle'], '>': _HELP_INDEX['<'], '<=': _HELP_INDEX['<'],
                    '>=': _HELP_INDEX['<']})

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

# --- Standard Environment Definitions ---
def standard_env() -> Env:
    """Create a global environment where ALL operations are wrapped inside Procedure objects."""
    env = Env()
    
    # 1. Kääritään math-kirjaston funktiot (kuten log, sin, cos, pow, pi)
    for key, value in vars(math).items():
        if callable(value):
            # Luodaan Procedure, joka tietää oman nimensä
            env[key] = Procedure(parms=['x'], body=None, env=env, native_fn=value, name=key)
        else:
            env[key] = value # pi ja e säilyvät numeroina
            
    # 2. Luodaan perusoperaattorit valmiiksi käärittyinä
    primitives = {
        '+': op.add, 'plus': op.add,
        '-': op.sub, '*': op.mul, '/': op.truediv,
        '>': op.gt, '<': op.lt, '>=': op.ge, '<=': op.le, '=': op.eq,
        # Python builtins that don't live in `math`
        'abs':   abs,
        'min':   min,
        'max':   max,
        'round': round,
        'append': lambda x, y: String((x.value if isinstance(x, String) else x) + (y.value if isinstance(y, String) else y)) if isinstance(x, (str, String)) and isinstance(y, (str, String)) else op.add(x, y),
        'car': lambda x: x[0] if x else [],
        'cdr': lambda x: x[1:],
        'cons': lambda x, y: [x] + y,
        'length': lambda x: len(x.value) if isinstance(x, String) else len(x),
        'list': lambda *x: list(x),
        'null?': lambda x: x == [],
        'not': lambda x: not x,
        'number?': lambda x: isinstance(x, (int, float)),
        'symbol?': lambda x: isinstance(x, str),
        'seq': lambda x: [Char(c) for c in x.value] if isinstance(x, String) else ([Char(c) for c in x] if isinstance(x, str) else list(x)),
        'str': str,
        'map': lambda proc, items: list(map(proc, items)),
        'filter': lambda proc, items: list(filter(proc, items)),
        'first': lambda x: x[0] if x else [],
        'rest': lambda x: x[1:],
        'empty?': lambda x: x == [],
        'get': lambda collection, key: collection.get(key, []) if isinstance(collection, dict) else [],
        'pretty-print': lambda exp: print(pretty_print(exp, width=40)),
        'pprint': lambda exp: print(pretty_print(exp, width=40)),
        'reinit-turtle': reinit_turtle,
        'reset': reinit_turtle,
        # Mutable vectors (Python lists), a timer and plain output
        'make-vector': lambda n, fill=0: [fill] * int(n),
        'vector-ref': lambda v, i: v[i],
        'vector-set!': lambda v, i, x: v.__setitem__(i, x),
        'clock': time.perf_counter,          # seconds as a float
        'display': lambda *x: print(*(a if isinstance(a, (str, String, Char)) else lisp_str(a) for a in x), sep=''),
        'push-pose': push_pose,
        'pop-pose': pop_pose,
        'clear-poses': clear_poses,
        'help': lisp_help,
        'eval': lambda exp: eval_exp(exp, global_env),
        'read': lambda text: parse(text.value if isinstance(text, String) else str(text)),
        'string->symbol': lambda text: Symbol(text.value if isinstance(text, String) else text),
        'symbol->string': lambda sym: String(str(sym)),
        'string?': lambda x: isinstance(x, String),
    }
    
    for key, value in primitives.items():
        # Kaikki perusfunktiot kääritään siististi Procedure-olioiksi!
        env[key] = Procedure(parms=['*args'], body=None, env=env, native_fn=value, name=key)

    # 3. Add turtle graphics support dynamically
    for key in turtle.__all__:
        value = getattr(turtle, key)
        if callable(value):
            env[key] = Procedure(
                parms=['*args'],
                body=None,
                env=env,
                native_fn=lambda *args, k=key: getattr(turtle, k)(*args),
                name=key
            )
        else:
            env[key] = value

    return env

global_env = standard_env()

# --- Evaluation Engine ---
def eval_exp(x: Exp, env: 'Env' = global_env) -> Any:
    """Evaluate an expression in an environment using Structural Pattern Matching."""
    match x:
        # 1. Clojure-style Keywords: keywords starting with ':' evaluate to themselves
        case str(symbol) if symbol.startswith(':'):
            return x

        # 2. Variable reference
        case str(symbol):
            return env.find(symbol)[symbol]
            
        # 3. Constant numeric literal
        case int() | float():
            return x
            
        # 4. Pure string literals and Characters
        case String(s) | Char(s):
            return x
                    
        # 5. Clojure-style data Vector [1 2 3] (tuple in Python) -> evaluates its contents
        case tuple(elements):
            return [eval_exp(e, env) for e in elements]
            
        # 6. Clojure-style Map {key val} (dict in Python) -> evaluates values, keeps string keys raw
        case dict(d):
            evaluated_dict = {}
            for k, v in d.items():
                eval_k = k.value if isinstance(k, String) else k if isinstance(k, str) else eval_exp(k, env); eval_k = tuple(eval_k) if isinstance(eval_k, list) else eval_k.value if isinstance(eval_k, String) else eval_k
                eval_v = eval_exp(v, env)
                evaluated_dict[eval_k] = eval_v
            return evaluated_dict

        # 7. (quote exp)
        case ['quote', exp]:
            return exp
            
        # 8. (if test conseq alt)
        case ['if', test, conseq, alt]:
            exp = conseq if eval_exp(test, env) else alt
            return eval_exp(exp, env)
            
        # 9. (define var exp)
        case ['define', str(var), exp]:
            val = eval_exp(exp, env)
            if isinstance(val, Procedure) and val.name is None:
                val.name = var
            env[var] = val
            return None
                    
        # 10. (set! var exp)
        case ['set!', str(var), exp]:
            env.find(var)[var] = eval_exp(exp, env)
            return None
            
        # 11. (lambda (parms...) body) or (lambda [parms...] body)
        case ['lambda', list(parms) | tuple(parms), body]:
            actual_parms = list(parms) if isinstance(parms, tuple) else parms
            return Procedure(actual_parms, body, env) # Palauttaa nyt Procedure-olion!

        # 12. (begin exp1 exp2 ... expN)
        case ['begin', *exps]:
            result = None
            for exp in exps:
                result = eval_exp(exp, env)
            return result

        # 13. (let [var1 val1...] body) or (let (var1 val1...) body)
        case ['let', list(bindings) | tuple(bindings), body]:
            if len(bindings) % 2 != 0:
                raise SyntaxError("Let bindings must have an even number of elements")
            
            vars_local = [bindings[i] for i in range(0, len(bindings), 2)]
            vals_local = [eval_exp(bindings[i+1], env) for i in range(0, len(bindings), 2)]
            
            local_env = Env(vars_local, vals_local, env)
            return eval_exp(body, local_env)
            
        # (while test body...) -> iterative loop, so it needs no recursion depth
        case ['while', test, *body]:
            while eval_exp(test, env):
                for exp in body:
                    eval_exp(exp, env)
            return None

        # 14. Workspace save and load hooks (Updated)
        case ['save', filename_exp]:
            filename = eval_exp(filename_exp, env)
            fn_str = filename.value if isinstance(filename, String) else str(filename)
            return save_workspace(fn_str)

        case ['load', filename_exp]:
            filename = eval_exp(filename_exp, env)
            fn_str = filename.value if isinstance(filename, String) else str(filename)
            return load_workspace(fn_str)

        # 15. Property list flavor: if a Clojure keyword is used as a function call,
        # e.g., (:name user), let it perform a dictionary lookup directly!
        case [str(keyword), target_exp] if keyword.startswith(':'):
            target = eval_exp(target_exp, env)
            if isinstance(target, dict):
                return target.get(keyword, [])
            raise TypeError(f"Cannot lookup keyword {keyword} on non-dictionary object")

        # 16. (proc args...) -> Standard function application
        case [proc_exp, *args_exp]:
            proc = eval_exp(proc_exp, env)
            if not callable(proc):
                hint = " (a string is data; use (string->symbol ...) to make a name)" if isinstance(proc, String) else ""
                raise TypeError(f"{lisp_str(proc)} is not a function{hint}")
            args = [eval_exp(arg, env) for arg in args_exp]
            return proc(*args)
            
        case _:
            raise SyntaxError(f"Unknown syntax: {x}")

# --- Parsing (Tokenizing and AST Building) ---
def parse(program: str) -> Exp:
    """Read a Lisp expression from a string program."""
    return read_from_tokens(tokenize(program))
# String literals: """raw text""" (may hold " and newlines, no escapes) or "text" with escapes
STRING_PATTERN = r'"""[\s\S]*?"""|"(?:[^"\\]|\\.)*"'
CHAR_PATTERN = r'#\\[()\[\]{}]|#\\[^\s()\[\]{}]+'
TOKEN_RE = re.compile(CHAR_PATTERN + '|' + STRING_PATTERN +
                      r'|;[^\n]*|\[|\]|\(|\)|\{|\}|\'|[^\s()\[\]{}";\']+')
STRING_ESCAPES = {'n': '\n', 't': '\t', '"': '"', '\\': '\\'}

def tokenize(chars: str) -> list[str]:
    """Convert a string into a list of tokens, dropping ; comments.

    Strings and characters are matched first, so a ; or ' inside "text",
    or the characters #\\; and #\\', are kept as they are.
    """
    return [t for t in TOKEN_RE.findall(chars) if not t.startswith(';')]

def read_from_tokens(tokens: list[str]) -> Exp:
    """Read an expression from a sequence of tokens with automatic closing parentheses."""
    if not tokens:
        raise SyntaxError("Unexpected EOF while reading")
        
    token = tokens.pop(0)
    
    if token == '(':
        L = []
        while tokens and tokens[0] != ')':
            # Safe boundary check: if user closes with a wrong bracket type, intercept it
            if tokens[0] in (']', '}'): 
                break 
            L.append(read_from_tokens(tokens))
        if tokens and tokens[0] == ')':
            tokens.pop(0) # Remove ')'
        return L
        
    elif token == '[':
        L = []
        while tokens and tokens[0] != ']':
            if tokens[0] in (')', '}'): 
                break
            L.append(read_from_tokens(tokens))
        if tokens and tokens[0] == ']':
            tokens.pop(0) # Remove ']'
        return tuple(L) # Returns as tuple to be recognized as data vector
        
    elif token == '{':
        D = {}
        while tokens and tokens[0] != '}':
            if tokens[0] in (')', ']'): 
                break
            key = read_from_tokens(tokens)
            
            # If the user closed the map abruptly, break out safely
            if not tokens or tokens[0] == '}':
                break
            val = read_from_tokens(tokens)
            D[key.value if isinstance(key, String) else tuple(key) if isinstance(key, list) else tuple(key) if type(key).__name__ == 'list' else key] = val
            
        if tokens and tokens[0] == '}':
            tokens.pop(0) # Remove '}'
        return D # Returns as standard dict for map structures
        
    elif token in (')', ']', '}'):
        raise SyntaxError(f"Unexpected closing bracket: {token}")
    elif token == "'":
        return ['quote', read_from_tokens(tokens)]
    else:
        return atom(token)

def atom(token: str) -> Atom:
    r"""Numbers become numbers, #t and #f booleans, "strings" String, #\c Char, others symbols."""
    if token == '#t':
        return True
    if token == '#f':
        return False
    if len(token) >= 6 and token.startswith('"""') and token.endswith('"""'):
        return String(token[3:-3])
    if len(token) >= 2 and token.startswith('"') and token.endswith('"'):
        return String(re.sub(r'\\(.)', lambda m: STRING_ESCAPES.get(m.group(1), m.group(0)), token[1:-1]))
    if token.startswith('#\\'):
        char_map = {'#\\newline': '\n', '#\\space': ' ', '#\\tab': '\t'}
        if token in char_map:
            return Char(char_map[token])
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
RECURSION_HINT = ("recursion too deep (a few hundred calls is the limit). "
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

# --- Interaction and REPL Printing ---
def lisp_str(exp: Any) -> str:
    """Convert a Python object back into a Lisp-readable string format, handling custom types safely."""
    # KORJAUKSEN YDIN: Tarkistetaan tyypit nimen perusteella, jotta dataclassit ja oliot tunnistetaan satavarmasti!
    type_name = type(exp).__name__

    if isinstance(exp, bool):
        return '#t' if exp else '#f'
    if type_name == 'Procedure':
        # Jos kyseessä on natiivifunktio (body on None tai native_fn on olemassa)
        if exp.native_fn is not None:
            # Jos oliolla on nimi (kuten log tai +), tulostetaan se.
            # Jos nimeä ei ole, käytetään tunnistettavaa nimeä.
            return exp.name if exp.name else "<native-function>"
        
        # Jos se on käyttäjän aito Lisp-lambda-funktio
        return f"(lambda {lisp_str(tuple(exp.parms))} {lisp_str(exp.body)})"

    elif type_name == 'String':
        return string_literal(exp.value)
    elif type_name == 'Char':
        reverse_char_map = {'\n': '#\\newline', ' ': '#\\space', '\t': '#\\tab'}
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
def repl(prompt: str = "lispy3> ") -> None:
    """An interactive Read-Eval-Print Loop showing open bracket count."""
    print(f"{COLOR_INFO}Modern Python 3 Lispy Interpreter Started.{COLOR_RESET}")
    print(f"{COLOR_INFO}Type (help) for the built-ins, 'exit' to quit. Unclosed paren depth is shown in prompt.{COLOR_RESET}\n")
    
    env = global_env
    colored_prompt = f"{COLOR_PROMPT}{prompt}{COLOR_RESET}"
    
    buffer = ""
    
    while True:
        try:
            depth = count_balance(buffer) if buffer else 0
            
            # Show depth indicator when lines remain unclosed, e.g. "... (2)> "
            if depth > 0:
                current_prompt = f"{COLOR_PROMPT}... ({depth})> {COLOR_RESET}"
            else:
                current_prompt = colored_prompt

            line = input(current_prompt)
            
            if not buffer and not line.strip():
                continue
                
            if not buffer and line.strip().lower() == 'exit':
                print(f"{COLOR_INFO}Goodbye!{COLOR_RESET}")
                break
                
            buffer = f"{buffer}\n{line}" if buffer else line
            
            # Keep prompting if parens are still open
            if count_balance(buffer) > 0:
                continue
                
            ast = parse(buffer)
            buffer = ""
            val = eval_exp(ast, env)
            
            if val is not None:
                print(f"{COLOR_RESULT}{lisp_str(val)}{COLOR_RESET}")
        except turtle.Terminator:
            buffer = ""
            print(f"{COLOR_ERROR}Error: Turtle window was closed. Call (reinit-turtle) to reopen.{COLOR_RESET}")
        except (SyntaxError, NameError, TypeError, ZeroDivisionError, FileNotFoundError,
                IndexError, KeyError) as e:
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
    except (SyntaxError, NameError, TypeError, ZeroDivisionError,
            FileNotFoundError, IndexError, KeyError) as e:
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
