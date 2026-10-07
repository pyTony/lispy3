from typing import Any, TypeAlias, Callable
from dataclasses import dataclass
import math
import operator as op
import re

# --- Types and Data Structures ---
Symbol: TypeAlias = str
Number: TypeAlias = int | float
Atom: TypeAlias = Symbol | Number | 'String'
List: TypeAlias = list['Exp']
Exp: TypeAlias = Atom | List | tuple['Exp', ...] | dict['Exp', 'Exp']

@dataclass(frozen=True)
class String:
    """A wrapper to distinguish pure string literals from Lisp symbols."""
    value: str

    def __repr__(self) -> str:
        return self.value

class Procedure:
    """A user-defined Lisp/Scheme procedure that remembers its source code for saving."""
    def __init__(self, parms: list[Symbol], body: Exp, env: Env):
        self.parms = parms
        self.body = body
        self.env = env

    def __call__(self, *args: Any) -> Any:
        # Suoritetaan funktio luomalla sille oma paikallinen skooppi
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

# --- Helper Functions for Workspace Save and Load (FINAL REPL FIX) ---
def save_workspace(filename: str) -> str:
    """Saves all user-defined definitions from the global environment to a file as Lisp code."""
    real_filename = filename if filename.endswith('.lisp') else f"{filename}.lisp"
    
    # Luodaan puhdas standardiympäristö pelkkää nimitarkistusta varten
    std = standard_env()
    
    with open(real_filename, 'w', encoding='utf-8') as f:
        # Käydään suoraan läpi yhteistä globaalia ympäristöä
        for key, value in global_env.items():
            # Tallennetaan vain ne, joita ei ole standardiympäristössä ja jätetään 'nan' pois
            if key not in std and key != 'nan':
                f.write(f"(define {key} {lisp_str(value)})\n")
    return f"Workspace saved to {real_filename}"

def load_workspace(filename: str) -> str:
    """Loads and evaluates Lisp definitions from a file into the global environment."""
    real_filename = filename if filename.endswith('.lisp') else f"{filename}.lisp"
    
    with open(real_filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    for line in lines:
        ast = parse(line)
        eval_exp(ast, global_env) # Ajetaan koodi suoraan yhteisessä globaalissa ympäristössä
        
    return f"Workspace loaded from {real_filename}"

# --- Standard Environment Definitions ---
def standard_env() -> Env:
    """Create a global environment with standard Lisp/Scheme operations."""
    env = Env()
    env.update(vars(math)) # Includes pow, sin, cos, pi, e, etc.
    env.update({
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
        
        # Functional programming tools
        'map': lambda proc, items: list(map(proc, items)),
        'filter': lambda proc, items: list(filter(proc, items)),
        
        # Clojure-style aliases
        'first': lambda x: x if x else [],
        'rest': lambda x: x[1:],
        'empty?': lambda x: x == [],
        
        # Dictionary lookup tool
        'get': lambda collection, key: collection.get(key, []) if isinstance(collection, dict) else [],
    })
    return env

global_env = standard_env()

# --- Evaluation Engine ---
def eval_exp(x: Exp, env: Env = global_env) -> Any:
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
            
        # 4. Pure string literals (dataclass String)
        case String(s):
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
            env[var] = eval_exp(exp, env)
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
            
        # 14. Workspace save and load hooks (Päivitetty)
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
    """Convert a string into a list of tokens, splitting brackets and handling strings properly."""
    # Ensure spaces around brackets for easy text processing
    for bracket in "()[]{}":
        chars = chars.replace(bracket, f" {bracket} ")
    chars = chars.replace("'", " ' ")
    
    # Advanced regex tokenizer to keep string literals intact and catch tokens
    return re.findall(r'\[|\]|\(|\)|\{|\}|\'|"[^"]*"|[^\s()\[\]{}]+', chars)

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
    """Numbers become numbers, "strings" lose quotes and become String objects, others are symbols."""
    if token.startswith('"') and token.endswith('"'):
        return String(token[1:-1]) # Wrap pure string text in String dataclass
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return Symbol(token)

# --- Interaction and REPL Printing ---
def lisp_str(exp: Any) -> str:
    """Convert a Python object back into a Lisp-readable string format."""
    if isinstance(exp, list):
        return '(' + ' '.join(map(lisp_str, exp)) + ')'
    elif isinstance(exp, tuple):
        return '[' + ' '.join(map(lisp_str, exp)) + ']'
    elif isinstance(exp, dict):
        pairs = [f"{lisp_str(k)} {lisp_str(v)}" for k, v in exp.items()]
        return '{' + ' '.join(pairs) + '}'
    elif isinstance(exp, String):
        return f'"{exp.value}"'
    elif isinstance(exp, Procedure):
        # Muutetaan funktio takaisin muotoon: (lambda [argumentit] body)
        return f"(lambda {lisp_str(tuple(exp.parms))} {lisp_str(exp.body)})"

    return str(exp)

def repl(prompt: str = "lispy3> ") -> None:
    """An interactive Read-Eval-Print Loop for the modern Lispy interpreter."""
    print("Modern Python 3 Lispy Interpreter Started.")
    print("Features: Unclosed brackets are fixed, Clojure map/vector types supported.")
    print("Workspace functions: (save \"name\") and (load \"name\") are active.")
    print("Type 'exit' to quit.\n")
    
    # KORJAUKSEN YDIN: Käytetään samaa globaalia ympäristöä kuin save ja load!
    env = global_env 
       
    while True:
        try:
            line = input(prompt).strip()
            if not line:
                continue
            if line.lower() == 'exit':
                print("Goodbye!")
                break
                
            ast = parse(line)
            val = eval_exp(ast, env)
            
            if val is not None:
                print(lisp_str(val))
                
        except (SyntaxError, NameError, TypeError, ZeroDivisionError, FileNotFoundError) as e:
            print(f"Error: {e}")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    repl()

