"""Explicit library environments and selective imports for lispy3.

Library macros use definition-site bindings for introduced references and retain
use-site symbols in their arguments. This is not a syntax-rules implementation.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LibraryReference:
    env: object
    name: str

    def value(self):
        return self.env[self.name]


class UseSiteSymbol(str):
    def __new__(cls, name, scope):
        result = super().__new__(cls, name)
        result.scope = scope
        return result


@dataclass
class Library:
    name: str
    env: object
    macros: dict
    directory: Path
    exports: dict


class ImportedMacro:
    def __init__(self, system, library, proc):
        self.system, self.library, self.proc = system, library, proc

    def __call__(self, *args):
        system = self.system
        caller = system.current.get()
        args = [system.tag(arg, caller) for arg in args]
        with system.scope(self.library):
            code = system.runtime.expand(self.proc(*args), toplevel=True)
        return system.bind(code, self.library.env)


class LibrarySystem:
    def __init__(self, runtime):
        self.runtime = runtime
        self.registry = {}
        self.files = {}
        self.loading = set()
        self.current = ContextVar('lispy_library', default=None)
        self.directory = ContextVar('lispy_library_directory', default=None)

    def has_imports(self):
        return (any(isinstance(value, LibraryReference) for value in self.runtime.global_env.values()) or
                any(isinstance(value, ImportedMacro) for value in self.runtime.macro_table.values()))

    def reset(self):
        self.registry.clear()
        self.files.clear()
        self.loading.clear()
        table = self.runtime.macro_table
        for name in list(table):
            if isinstance(table[name], ImportedMacro):
                del table[name]

    @contextmanager
    def scope(self, library, directory=None):
        token = self.current.set(library)
        path_token = self.directory.set(directory or library.directory)
        try:
            yield
        finally:
            self.directory.reset(path_token)
            self.current.reset(token)

    def macros(self, head=None):
        lib = head.scope if isinstance(head, UseSiteSymbol) else self.current.get()
        return lib.macros if lib else self.runtime.macro_table

    def env(self):
        lib = self.current.get()
        return lib.env if lib else self.runtime.global_env

    @staticmethod
    def owner(env):
        return getattr(env, 'library', None)

    def check_definition(self, env, name):
        library = self.owner(env)
        macros = library.macros if library else self.runtime.macro_table
        if isinstance(dict.get(env, name), LibraryReference) or isinstance(macros.get(name), ImportedMacro):
            raise self.runtime.LispyError(f'import binding is read-only: {name}')

    def expand_in(self, code, env, toplevel=False):
        library = self.owner(env)
        if library:
            with self.scope(library):
                return self.runtime.expand(code, toplevel)
        return self.runtime.expand(code, toplevel)

    def runtime_macro(self, head, env):
        lib = self.owner(env)
        return (lib.macros if lib else self.runtime.macro_table).get(head)

    @staticmethod
    def tag(code, scope):
        if type(code) is str:
            return UseSiteSymbol(code, scope)
        if isinstance(code, UseSiteSymbol):
            return code
        if type(code) is list:
            return [LibrarySystem.tag(e, scope) for e in code]
        if type(code) is tuple:
            return tuple(LibrarySystem.tag(e, scope) for e in code)
        if type(code) is dict:
            return {k: LibrarySystem.tag(v, scope) for k, v in code.items()}
        return code

    @staticmethod
    def plain(code):
        if isinstance(code, UseSiteSymbol):
            return str(code)
        if isinstance(code, list):
            return [LibrarySystem.plain(e) for e in code]
        if isinstance(code, tuple):
            return tuple(LibrarySystem.plain(e) for e in code)
        return code

    def bind(self, code, env, bound=frozenset()):
        """Capture introduced free references, leaving binders/data/caller syntax alone."""
        if isinstance(code, UseSiteSymbol):
            return code
        if type(code) is str:
            if code in bound or code in self.runtime.SPECIAL_FORMS or code.startswith(':'):
                return code
            try:
                return LibraryReference(env.find(code), code)
            except NameError:
                return code
        if isinstance(code, tuple):
            return tuple(self.bind(e, env, bound) for e in code)
        if isinstance(code, dict):
            return {k: self.bind(v, env, bound) for k, v in code.items()}
        if type(code) is not list or not code:
            return code
        head = code[0]
        if type(head) is str and '/' in head and head != '/' and head != 'str/join':
            obj, method = head.split('/', 1)
            if obj not in bound:
                try:
                    owner = env.find(obj)
                except NameError:
                    pass
                else:
                    temp = self.runtime.gensym('library_obj')
                    body = [f'{temp}/{method}'] + [self.bind(e, env, bound) for e in code[1:]]
                    return [['lambda', [temp], body], LibraryReference(owner, obj)]
        if head == 'quote':
            return self.plain(code)
        if head == 'lambda':
            parms = self.plain(code[1])
            names = {parms} if isinstance(parms, str) else set(parms)
            return ['lambda', parms, self.bind(code[2], env, bound | names)]
        if head == 'begin':
            # Definitions in a generated program belong to the caller's lexical scope.
            names = {str(e[1]) for e in code[1:] if type(e) is list and len(e) > 1 and e[0] == 'define'}
            return ['begin'] + [self.bind(e, env, bound | names) for e in code[1:]]
        if head == 'define':
            return ['define', self.plain(code[1]), self.bind(code[2], env, bound | {str(code[1])})]
        if head == 'let':
            named = isinstance(code[1], str)
            bindings = code[2] if named else code[1]
            nested = self.runtime._scheme_bindings(bindings)
            names = {str(b[0]) for b in bindings} if nested else {str(n) for n in bindings[::2]}
            local = bound | names | ({str(code[1])} if named else set())
            if nested:
                bindings = [[self.plain(b[0]), self.bind(b[1], env, bound)] for b in bindings]
            else:
                result, seen = [], bound
                for name, value in zip(bindings[::2], bindings[1::2]):
                    result.extend([self.plain(name), self.bind(value, env, seen)])
                    seen = seen | {str(name)}
                bindings = result
            return ['let'] + ([str(code[1])] if named else []) + [bindings, self.bind(code[-1], env, local)]
        if head == 'dotimes':
            spec = code[1]
            return ['dotimes', [self.plain(spec[0]), self.bind(spec[1], env, bound)] +
                    [self.bind(e, env, bound | {str(spec[0])}) for e in spec[2:]]] + [
                    self.bind(e, env, bound | {str(spec[0])}) for e in code[2:]]
        if head == 'catch' and len(code) >= 3:
            return ['catch', self.plain(code[1])] + [self.bind(e, env, bound | {str(code[1])}) for e in code[2:]]
        return [self.bind(e, env, bound) for e in code]

    @staticmethod
    def name(value):
        if type(value) is str:
            return value
        if type(value) is list and value and all(type(e) is str for e in value):
            return '/'.join(value)
        raise SyntaxError('library: expected a name or a list of name components')

    def define(self, form):
        r = self.runtime
        if len(form) < 3:
            raise SyntaxError('define-library needs a name and declarations')
        name = self.name(form[1])
        if name in self.registry:
            raise r.LispyError(f'library already defined: {name}')
        library = Library(name, r.Env(outer=r.standard_env()), {}, self.directory.get() or Path.cwd(), {})
        library.env.library = library
        library.env['eval'] = lambda code: self.evaluate(code, library)
        library.env['read'] = lambda text: self.read(text, library)
        exports = []
        with self.scope(library):
            for declaration in form[2:]:
                if not isinstance(declaration, list) or not declaration:
                    raise SyntaxError('define-library: expected export, import, begin or include declaration')
                kind, *body = declaration
                if kind == 'export':
                    exports.extend(body)
                elif kind == 'import':
                    self.import_sets(body)
                elif kind == 'begin':
                    for exp in body:
                        r.eval_exp(r.expand(exp, True), library.env)
                elif kind == 'include':
                    for filename in body:
                        if not isinstance(filename, r.String):
                            raise SyntaxError('include: expected a filename string')
                        self.load_source(filename.value, library)
                else:
                    raise SyntaxError(f'define-library: unsupported declaration {kind}')
        for export in exports:
            if type(export) is str:
                internal = external = export
            elif type(export) is list and len(export) == 3 and export[0] == 'rename':
                _, internal, external = export
                if type(internal) is not str or type(external) is not str:
                    raise SyntaxError('export rename needs two names')
            else:
                raise SyntaxError('export: expected name or (rename internal external)')
            if external in library.exports:
                raise r.LispyError(f'duplicate export: {external}')
            if internal in library.macros:
                proc = library.macros[internal]
                library.exports[external] = proc if isinstance(proc, ImportedMacro) else ImportedMacro(self, library, proc)
            elif internal in library.env:
                library.exports[external] = LibraryReference(library.env, internal)
            else:
                raise r.LispyError(f'export missing definition: {internal}')
        self.registry[name] = library

    def read(self, text, library):
        with self.scope(library):
            return self.runtime.parse(self.runtime._unwrap_str(text))

    def evaluate(self, code, library):
        # Legacy procedural macros may explicitly evaluate an input argument.
        # Such syntax belongs to its caller, not the macro's private library.
        def use_site(exp):
            if isinstance(exp, UseSiteSymbol):
                return exp
            if isinstance(exp, (list, tuple)):
                for item in exp:
                    found = use_site(item)
                    if found is not None:
                        return found
            return None
        marker = use_site(code)
        if marker is not None:
            caller = marker.scope
            target = caller.env if caller else self.runtime.global_env
            if caller:
                with self.scope(caller):
                    return self.runtime.eval_exp(self.runtime.expand(self.plain(code), True), target)
            token = self.current.set(None)
            try:
                return self.runtime.eval_exp(self.runtime.expand(self.plain(code), True), target)
            finally:
                self.current.reset(token)
        return self.runtime.eval_exp(self.expand_in(code, library.env, True), library.env)

    def load_source(self, filename, library):
        r = self.runtime
        path = Path(filename)
        if not path.suffix:
            path = path.with_suffix('.lisp')
        if not path.is_absolute():
            path = (self.directory.get() or library.directory) / path
        with self.scope(library, path.parent):
            # Read/expand/evaluate sequentially so definitions exist for later macros.
            tokens = r.tokenize(path.read_text(encoding='utf-8'))
            while tokens:
                r.eval_exp(r.expand(r.read_from_tokens(tokens), True), library.env)
        return f'Library source loaded from {path}'

    def resolve(self, spec):
        r = self.runtime
        if isinstance(spec, r.String):
            path = Path(spec.value)
            if not path.is_absolute():
                path = (self.directory.get() or Path.cwd()) / path
            path = path.resolve()
            name = None
        else:
            name = self.name(spec)
            if name in self.registry:
                return self.registry[name].exports
            path = Path(r.LISP_DIR) / (name + '.sld')
        key = str(path)
        if key in self.files:
            return self.registry[self.files[key]].exports
        if key in self.loading:
            raise r.LispyError(f'cyclic library import: {name or path}')
        if not path.is_file():
            raise r.LispyError(f'library not found: {name or path}')
        self.loading.add(key)
        before = set(self.registry)
        try:
            token = self.directory.set(path.parent)
            try:
                tokens = r.tokenize(path.read_text(encoding='utf-8'))
                if not tokens:
                    raise SyntaxError('library file is empty')
                form = r.read_from_tokens(tokens)
                if tokens or not isinstance(form, list) or not form or form[0] != 'define-library':
                    raise SyntaxError('library file must contain one define-library form')
                declared = self.name(form[1])
                if name is not None and declared != name:
                    raise r.LispyError(f'library name mismatch: expected {name}, got {declared}')
                self.define(form)
                self.files[key] = declared
                return self.registry[declared].exports
            finally:
                self.directory.reset(token)
        except BaseException:
            for added in set(self.registry) - before:
                del self.registry[added]
            self.files = {path: name for path, name in self.files.items() if name in self.registry}
            raise
        finally:
            self.loading.remove(key)

    def selection(self, spec):
        r = self.runtime
        if isinstance(spec, list) and spec and spec[0] in ('only', 'prefix', 'rename'):
            kind = spec[0]
            if len(spec) < 2:
                raise SyntaxError(f'import {kind}: missing import set')
            exports = self.selection(spec[1])
            if kind == 'only':
                names = spec[2:]
                if any(type(n) is not str for n in names) or len(names) != len(set(names)):
                    raise SyntaxError('import only: expected distinct names')
                for name in names:
                    if name not in exports:
                        raise r.LispyError(f'import: missing export {name}')
                return {name: exports[name] for name in names}
            if kind == 'prefix':
                if len(spec) != 3 or type(spec[2]) is not str:
                    raise SyntaxError('import prefix: expected one prefix symbol')
                return {spec[2] + name: value for name, value in exports.items()}
            renamed = dict(exports)
            pairs = spec[2:]
            if any(type(p) is not list or len(p) != 2 or any(type(n) is not str for n in p) for p in pairs):
                raise SyntaxError('import rename: expected (old new) pairs')
            sources = [p[0] for p in pairs]
            if len(set(sources)) != len(sources):
                raise SyntaxError('import rename: duplicate source')
            for old, new in pairs:
                if old not in exports:
                    raise r.LispyError(f'import: missing export {old}')
                del renamed[old]
            for old, new in pairs:
                if new in renamed:
                    raise r.LispyError(f'import name collision: {new}')
                renamed[new] = exports[old]
            return renamed
        return self.resolve(spec)

    def import_sets(self, sets):
        r = self.runtime
        env, macros = self.env(), self.macros()
        selected = {}
        for spec in sets:
            for name, value in self.selection(spec).items():
                if name in r.SPECIAL_FORMS or name in ('define-library', 'import'):
                    raise r.LispyError(f'import reserved name: {name}')
                if name in selected and selected[name] is not value:
                    raise r.LispyError(f'import name collision: {name}')
                selected[name] = value
        for name, value in selected.items():
            existing = macros.get(name) if isinstance(value, ImportedMacro) else dict.get(env, name)
            if (name in macros or name in env) and existing is not value:
                raise r.LispyError(f'import name collision: {name}')
        for name, value in selected.items():
            if isinstance(value, ImportedMacro):
                macros[name] = value
            else:
                env[name] = value
