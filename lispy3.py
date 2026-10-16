from typing import Any, TypeAlias, Callable, Union
from dataclasses import dataclass
import functools
import itertools
import math
import operator as op
import re
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

# --- Help Topics ---
HELP_TOPICS: dict[str, str] = {
    'make-vector': "(make-vector n fill) - n items, all fill (0 if left out), numbered from 0",
    'vector-ref': "(vector-ref v i) - item i of v",
    'vector-set!': "(vector-set! v i x) - put x into item i of v",
    'clock': "(clock) - seconds as a decimal number, for timing",
    'cond': "(cond (test1 exp1...) (test2 exp2...) (else expN...))",
    'and': "(and exp1 exp2 ...) - Short-circuit logical AND.",
    'or': "(or exp1 exp2 ...) - Short-circuit logical OR.",
    'define-macro': "(define-macro (name parms...) body) or (define-macro name (lambda ...))",
    'quasiquote': "`(a ,b ,@c) - Quasiquote template with unquote (,) and unquote-splicing (,@).",
    'try': "(try expr (catch e handler_expr)) - Catch runtime errors.",
    'error': "(error msg) - Raise a recoverable runtime error.",
    'dotimes': "(dotimes [i count] body...) - Loop i from 0 to count-1.",
    'for-each': "(for-each proc list1 ...) - Apply proc to each element for side-effects.",
    'numbers': "Variadic +, -, *, /, <, <=, =, >=, >, modulo, quotient, expt.",
    'lists': "reverse, nth, last, range, reduce, fold, apply, sort, member, append, list?, procedure?, eq?, equal?.",
    'strings': "substring, string-ref, upcase, downcase, split, list->string, string->number, format, str.",
    'maps': "assoc, dissoc, keys, vals, contains?.",
}

# --- Pretty Printer ---
def pretty_print(exp: Any, indent: int = 0, width: int = 40) -> str:
    """Format an AST or value into an indented string fitting within `width` columns."""
    pad = "  " * indent
    type_name = type(exp).__name__

    if type_name == 'Procedure':
        if exp.native_fn is not None:
            return exp.name if exp.name else "<native-function>"
        parms = '[' + ' '.join(exp.parms) + ']' if isinstance(exp.parms, (list, tuple)) else str(exp.parms)
        body_s = pretty_print(exp.body, indent + 1, width).lstrip()
        if getattr(exp, 'name', None):
            return f"(define {exp.name}\n{pad}  (lambda {parms}\n{pad}    {body_s}))"
        return f"(lambda {parms}\n{pad}  {body_s})"

    if type_name == 'String':
        return f'"{exp.value}"'
    if type_name == 'Char':
        reverse_char_map = {'\n': '#\\newline', ' ': '#\\space', '\t': '#\\tab', '\r': '#\\return', '\0': '#\\nul'}
        return reverse_char_map.get(exp.value, f"#\\{exp.value}")

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

    return str(exp)

# --- Helper Functions for Workspace Save and Load ---
def save_workspace(filename: str) -> str:
    """Saves only user-defined variables and Lisp Procedures to a file, ignoring Python built-ins."""
    real_filename = filename if filename.endswith('.lisp') else f"{filename}.lisp"
    std = standard_env()
    
    with open(real_filename, 'w', encoding='utf-8') as f:
        for key, value in global_env.items():
            if key in std or key == 'nan':
                continue
            if callable(value) and type(value).__name__ != 'Procedure':
                continue
            f.write(f"(define {key} {lisp_str(value)})\n")
            
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

def push_pose() -> list:
    """Save the turtle's current (x, y, heading) onto the pose stack."""
    _turtle_pose_stack.append((turtle.xcor(), turtle.ycor(), turtle.heading()))
    return []

def pop_pose() -> list:
    """Restore the turtle's last saved (x, y, heading) without drawing a line."""
    if _turtle_pose_stack:
        x, y, h = _turtle_pose_stack.pop()
        was_down = turtle.isdown()
        turtle.penup()
        turtle.goto(x, y)
        turtle.setheading(h)
        if was_down:
            turtle.pendown()
    return []

def clear_poses() -> list:
    """Empty the saved turtle pose stack."""
    _turtle_pose_stack.clear()
    return []

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
    return int(math.trunc(a / b))

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
        'modulo': _modulo,
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
        'empty?': lambda x: len(x) == 0 if isinstance(x, (list, tuple, dict, str, String)) else False,
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
        'append': lambda *lists: [elem for lst in lists for elem in lst],
        'car': lambda x: x[0] if isinstance(x, (list, tuple)) and x else [],
        'cdr': lambda x: list(x[1:]) if isinstance(x, (list, tuple)) else [],
        'cons': lambda x, y: [x] + (list(y) if isinstance(y, tuple) else (y if isinstance(y, list) else [y])),
        'length': lambda x: len(x.value) if isinstance(x, String) else len(x),
        'list': lambda *x: list(x),
        'first': lambda x: x[0] if isinstance(x, (list, tuple)) and x else (x if x else []),
        'rest': lambda x: list(x[1:]) if isinstance(x, (list, tuple)) else [],
        'last': lambda x: x[-1] if isinstance(x, (list, tuple)) and x else [],
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
        'number->string': lambda n: String(str(n)),
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
        'display': lambda *x: print(*(_unwrap_str(a) if isinstance(a, (String, Char)) else lisp_str(a) for a in x), sep='', end=''),
        # Mutable vectors (Python lists) and a timer
        'make-vector': lambda n, fill=0: [fill] * int(n),
        'vector-ref': lambda v, i: v[i],
        'vector-set!': lambda v, i, x: v.__setitem__(i, x),
        'clock': time.perf_counter,
        'newline': lambda: print(),
        'pretty-print': lambda exp: print(pretty_print(exp, width=40)),
        'pprint': lambda exp: print(pretty_print(exp, width=40)),
        'help': lambda *topic: HELP_TOPICS.get(_unwrap_str(topic[0]), f"Topics: {', '.join(HELP_TOPICS.keys())}") if topic else f"Topics: {', '.join(HELP_TOPICS.keys())}",
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

# --- Evaluation Engine with Proper Tail Call Optimization (TCO) ---
def eval_exp(x: Exp, env: 'Env' = global_env) -> Any:
    """Evaluate an expression in an environment with TCO loop and Structural Pattern Matching."""
    while True:
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
                    if not val and val is not None and val != 0 or val is False or val == []:
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
                args = [eval_exp(arg, env) for arg in args_exp]
                native_args = [a.value if isinstance(a, (String, Char)) else a for a in args]
                
                method = getattr(obj, method_name)
                result = method(*native_args)
                
                if isinstance(result, str):
                    return String(result)
                return result

            # 17. (proc args...) -> Macro check + Standard function application with TCO
            case [proc_exp, *args_exp]:
                if isinstance(proc_exp, str) and proc_exp in macro_table:
                    x = macro_table[proc_exp](*args_exp)
                    continue

                proc = eval_exp(proc_exp, env)
                args = [eval_exp(arg, env) for arg in args_exp]
                
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
                    # TCO: Update x and env in-place instead of growing the Python call stack!
                    x = proc.body
                    env = proc.bind_env(args)
                    continue
                elif callable(proc):
                    return proc(*args)
                raise TypeError(f"{lisp_str(proc)} is not callable")
                
            case _:
                raise SyntaxError(f"Unknown syntax: {x}")

# --- Parsing (Tokenizing and AST Building) ---
def parse(program: str) -> Exp:
    """Read and macro-expand a Lisp expression from a string program."""
    tokens = tokenize(program)
    if not tokens:
        return None
    ast = read_from_tokens(tokens)
    return expand(ast, toplevel=True)

def tokenize(chars: str) -> list[str]:
    """Convert a string into a list of tokens, handling comments, quotes, quasiquotes, and strings."""
    token_pattern = re.compile(
        r'"(?:\\.|[^"\\])*"'                  # String literal with escapes
        r'|;[^\n]*'                           # Comment
        r'|,@'                                # Unquote-splicing
        r"|['`,]"                             # Quote, quasiquote, unquote
        r'|#\\[a-zA-Z0-9]+;?'                 # Named/hex char literal (#\newline, #\x41)
        r'|#\\.'                              # Any single-char literal (#\[, #\], #\F, etc.)
        r'|[\[\](){}]'                        # Brackets
        r'|[^\s()\[\]{}"\'`,;]+'              # Symbols / numbers
    )
    raw_tokens = token_pattern.findall(chars)
    return [t for t in raw_tokens if not t.startswith(';')]

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
            D[key] = val
            
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

def _strip_non_code(text: str) -> str:
    """Replace strings, comments, and #\\x char literals with spaces of the same length."""
    pattern = re.compile(r'"(?:\\.|[^"\\])*"|;[^\n]*|#\\[a-zA-Z0-9]+;?|#\\.')
    return pattern.sub(lambda m: " " * len(m.group(0)), text)

def atom(token: str) -> Atom:
    """Numbers become numbers, "strings" become String, #\\c become Char, others are symbols."""
    if token.startswith('"') and token.endswith('"'):
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

def _strip_non_code(text: str) -> str:
    """Mask strings, comments, and #\\x char literals with spaces of identical length."""
    pattern = re.compile(r'"(?:\\.|[^"\\])*"|;[^\n]*|#\\[a-zA-Z0-9]+;?|#\\.')
    return pattern.sub(lambda m: " " * len(m.group(0)), text)

def count_balance(text: str) -> int:
    """Return the balance of opening vs closing brackets, ignoring strings, chars, and comments."""
    cleaned = _strip_non_code(text)
    opens = cleaned.count('(') + cleaned.count('[') + cleaned.count('{')
    closes = cleaned.count(')') + cleaned.count(']') + cleaned.count('}')
    return max(0, opens - closes)

def missing_closers(text: str) -> str:
    """Return the string of closing brackets needed to balance `text`."""
    cleaned = _strip_non_code(text)
    stack: list[str] = []
    pairs = {'(': ')', '[': ']', '{': '}'}
    for c in cleaned:
        if c in pairs:
            stack.append(pairs[c])
        elif c in (')', ']', '}'):
            if stack:
                stack.pop()
    return "".join(reversed(stack))

def close_position(text: str) -> int:
    """Return the character offset right after the last non-comment, non-whitespace token."""
    no_comments = re.sub(r';[^\n]*', lambda m: " " * len(m.group(0)), text)
    stripped = no_comments.rstrip()
    return len(stripped)

def auto_close(text: str) -> tuple[str, str]:
    """Return `(closed_text, closers)` with missing closing brackets inserted at `close_position`."""
    closers = missing_closers(text)
    if not closers:
        return text, ""
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

def repl(prompt: str = "lispy3> ") -> None:
    """An interactive Read-Eval-Print Loop showing open bracket count."""
    print(f"{COLOR_INFO}Modern Python 3 Lispy Interpreter Started.{COLOR_RESET}")
    print(f"{COLOR_INFO}Type 'exit' to quit. Unclosed paren depth is shown in prompt.{COLOR_RESET}\n")
    
    env = global_env
    colored_prompt = f"{COLOR_PROMPT}{prompt}{COLOR_RESET}"
    
    buffer = ""
    
    while True:
        try:
            depth = count_balance(buffer) if buffer else 0
            
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
        except (SyntaxError, NameError, TypeError, ZeroDivisionError, FileNotFoundError, LispyError, ValueError, IndexError) as e:
            buffer = ""
            print(f"{COLOR_ERROR}Error: {e}{COLOR_RESET}")
        except (KeyboardInterrupt, EOFError):
            print(f"\n{COLOR_INFO}Goodbye!{COLOR_RESET}")
            break

if __name__ == "__main__":
    repl()
