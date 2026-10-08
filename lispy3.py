
from typing import Any, TypeAlias, Callable, Union
from dataclasses import dataclass
import math
import operator as op
import re
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
        self.native_fn = native_fn  # Store the original Python function if it's a native function
        self.name = name            # Name of the native function (e.g., 'log' or '+')

    def __call__(self, *args: Any) -> Any:
        # If it is a wrapped native function, run it directly in Python
        if self.native_fn:
            return self.native_fn(*args)
        # Otherwise, run the Lisp function by creating its own local scope
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
        return f'"{exp.value}"'
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

    # 8. Atoms (Symbols, Numbers)
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
                
            # If it's a Python built-in function (e.g., log), do not save it
            if callable(value) and type(value).__name__ != 'Procedure':
                continue
                
            # Write pure Lisp code to the file
            f.write(f"(define {key} {lisp_str(value)})\n")
            
    return f"Workspace saved to {real_filename}"

def load_workspace(filename: str) -> str:
    """Loads and evaluates all Lisp definitions from a file safely, preventing REPL leaks."""
    real_filename = filename if filename.endswith('.lisp') else f"{filename}.lisp"
    
    with open(real_filename, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    # Wrap the file into a single begin block
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
    return "Turtle window reopened."

# --- Standard Environment Definitions ---
def standard_env() -> Env:
    """Create a global environment where ALL operations are wrapped inside Procedure objects."""
    env = Env()
    
    # 1. Wrap math library functions (like log, sin, cos, pow, pi)
    for key, value in vars(math).items():
        if callable(value):
            # Create a Procedure that knows its own name
            env[key] = Procedure(parms=['x'], body=None, env=env, native_fn=value, name=key)
        else:
            env[key] = value # pi and e remain as numbers
            
    # 2. Create basic operators already wrapped
    primitives = {
        '+': op.add, 'plus': op.add,
        '-': op.sub, '*': op.mul, '/': op.truediv,
        '>': op.gt, '<': op.lt, '>=': op.ge, '<=': op.le, '=': op.eq,
        'append': op.add,
        'car': lambda x: x if x else [],
        'cdr': lambda x: x[1:],
        'cons': lambda x, y: [x] + y,
        'length': len,
        'list': lambda *x: list(x),
        'null?': lambda x: x == [],
        'number?': lambda x: isinstance(x, (int, float)),
        'symbol?': lambda x: isinstance(x, str),
        'seq': lambda x: [Char(c) for c in x.value] if isinstance(x, String) else ([Char(c) for c in x] if isinstance(x, str) else list(x)),
        'str': str,
        'map': lambda proc, items: list(map(proc, items)),
        'filter': lambda proc, items: list(filter(proc, items)),
        'first': lambda x: x if x else [],
        'rest': lambda x: x[1:],
        'empty?': lambda x: x == [],
        'get': lambda collection, key: collection.get(key, []) if isinstance(collection, dict) else [],
        'pretty-print': lambda exp: print(pretty_print(exp, width=40)),
        'pprint': lambda exp: print(pretty_print(exp, width=40)),
        'reinit-turtle': reinit_turtle,
        'reset': reinit_turtle,
    }
    
    for key, value in primitives.items():
        # All basic functions are cleanly wrapped into Procedure objects!
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
                eval_k = k if isinstance(k, str) else eval_exp(k, env)
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
            return Procedure(actual_parms, body, env) # Now returns a Procedure object!

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
            args = [eval_exp(arg, env) for arg in args_exp]
            return proc(*args)
            
        case _:
            raise SyntaxError(f"Unknown syntax: {x}")

# --- Parsing (Tokenizing and AST Building) ---
def parse(program: str) -> Exp:
    """Read a Lisp expression from a string program."""
    return read_from_tokens(tokenize(program))
def tokenize(chars: str) -> list[str]:
    """Convert a string into a list of tokens, stripping comments and splitting brackets."""
    # 1. Strip comments (anything from ';' until end of the line)
    chars = re.sub(r';.*', '', chars)

    # 2. Ensure spaces around brackets for easy text processing
    for bracket in "()[]{}":
        chars = chars.replace(bracket, f" {bracket} ")
    chars = chars.replace("'", " ' ")
    
    # 3. Advanced regex tokenizer to keep string literals intact and catch tokens
    return re.findall(r'\[|\]|\(|\)|\{|\}|\'|"[^"]*"|#\\[^\s()\[\]{}]+|[^\s()\[\]{}]+', chars)

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
            D[key] = val
            
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
    """Numbers become numbers, "strings" become String, #\c become Char, others are symbols."""
    if token.startswith('"') and token.endswith('"'):
        return String(token[1:-1])
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
def count_balance(text: str) -> int:
    """Return the balance of opening vs closing brackets, ignoring strings and comments."""
    # Strip comments first
    cleaned = re.sub(r';.*', '', text)
    # Strip string literals
    cleaned = re.sub(r'"[^"]*"', '', cleaned)
    opens = cleaned.count('(') + cleaned.count('[') + cleaned.count('{')
    closes = cleaned.count(')') + cleaned.count(']') + cleaned.count('}')
    return max(0, opens - closes)

# --- Interaction and REPL Printing ---
def lisp_str(exp: Any) -> str:
    """Convert a Python object back into a Lisp-readable string format, handling custom types safely."""
    # CORE FIX: Check types by name so that dataclasses and objects are reliably identified!
    type_name = type(exp).__name__
    
    if type_name == 'Procedure':
        # If it is a native function (body is None or native_fn exists)
        if exp.native_fn is not None:
            # If the object has a name (like log or +), print it.
            # If there is no name, use a recognizable name.
            return exp.name if exp.name else "<native-function>"
        
        # If it is a true user-defined Lisp lambda function
        return f"(lambda {lisp_str(tuple(exp.parms))} {lisp_str(exp.body)})"

    elif type_name == 'String':
        return f'"{exp.value}"'
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
    print(f"{COLOR_INFO}Type 'exit' to quit. Unclosed paren depth is shown in prompt.{COLOR_RESET}\n")
    
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
        except (SyntaxError, NameError, TypeError, ZeroDivisionError, FileNotFoundError) as e:
            buffer = ""
            print(f"{COLOR_ERROR}Error: {e}{COLOR_RESET}")
        except (KeyboardInterrupt, EOFError):
            print(f"\n{COLOR_INFO}Goodbye!{COLOR_RESET}")
            break

if __name__ == "__main__":
    repl()
