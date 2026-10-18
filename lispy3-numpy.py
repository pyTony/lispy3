import sys
from fractions import Fraction
from typing import Any
import lispy3 as lp

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False


# --- 1. Optional NumPy Wrapper & Slice Helpers ---
class NDOpArray:
    """Wrapper around np.ndarray for Lispy interop."""
    __slots__ = ("data",)

    def __init__(self, data: Any, dtype=None):
        if not HAS_NUMPY:
            raise RuntimeError("NumPy is not installed.")
        if isinstance(data, NDOpArray):
            self.data = data.data.copy() if dtype is None else data.data.astype(dtype)
        elif isinstance(data, np.ndarray):
            self.data = data if dtype is None else data.astype(dtype)
        else:
            cleaned = _clean_for_numpy(data)
            self.data = np.array(cleaned, dtype=dtype)

    def __repr__(self) -> str:
        return f"#a{lp.lisp_str(self.data.tolist())}"

    def __getitem__(self, idx):
        if type(idx) is int:
            return self.data.item(idx)
        res = self.data[idx]
        return NDOpArray(res) if isinstance(res, np.ndarray) else res.item()
        
    def __setitem__(self, idx, val):
        self.data[idx] = val.data if isinstance(val, NDOpArray) else _clean_for_numpy(val)

    def __len__(self) -> int:
        return len(self.data)


def _clean_for_numpy(data: Any) -> Any:
    if isinstance(data, Fraction):
        return float(data)
    if isinstance(data, (list, tuple, lp.Vector)):
        return [_clean_for_numpy(x) for x in data]
    if isinstance(data, NDOpArray):
        return data.data
    return data


def _to_raw(x: Any) -> Any:
    if isinstance(x, NDOpArray):
        return x.data
    if isinstance(x, Fraction):
        return float(x)
    return x


def _wrap_result(res: Any) -> Any:
    if HAS_NUMPY:
        if isinstance(res, np.ndarray):
            return NDOpArray(res)
        if isinstance(res, np.generic):
            return res.item()
    return res


def _make_num_vector(n: int, fill: Any = 0) -> Any:
    if HAS_NUMPY:
        return NDOpArray(np.full(int(n), fill, dtype=np.int64))
    return lp.Vector([fill] * int(n))


def _vector_fill(v: Any, val: Any, start: int = 0, stop: int = None) -> None:
    if HAS_NUMPY and isinstance(v, NDOpArray):
        v.data[start:stop] = val
    else:
        end = len(v) if stop is None else stop
        v[start:end] = [val] * (end - start)


def _vector_slice_set(v: Any, start: int, stop: int, step: int, val: Any) -> None:
    if HAS_NUMPY and isinstance(v, NDOpArray):
        v.data[start:stop:step] = val
    else:
        v[start:stop:step] = [val] * len(range(start, stop, step))


def _sum_fn(arr: Any, axis: Any = None) -> Any:
    if HAS_NUMPY and isinstance(arr, NDOpArray):
        return _wrap_result(np.sum(arr.data, axis=axis))
    return sum(arr)


# Patch lisp_str and _length in lispy3
_orig_lisp_str = lp.lisp_str
def _patched_lisp_str(exp: Any) -> str:
    if HAS_NUMPY and isinstance(exp, NDOpArray):
        return f"#a{_orig_lisp_str(exp.data.tolist())}"
    return _orig_lisp_str(exp)

lp.lisp_str = _patched_lisp_str

_orig_length = lp._length
def _patched_length(x: Any) -> int:
    if HAS_NUMPY and isinstance(x, NDOpArray):
        return len(x.data)
    return _orig_length(x)

lp._length = _patched_length


# Register Vector/Slice and NumPy primitives in global_env
extra_primitives = {
    'make-num-vector': _make_num_vector,
    'vector-fill!': _vector_fill,
    'vector-slice-set!': _vector_slice_set,
    'sum': _sum_fn,
    'length': _patched_length,
}

if HAS_NUMPY:
    extra_primitives.update({
        'array?': lambda x: isinstance(x, NDOpArray),
        'array': lambda *args: NDOpArray(args),
        'zeros': lambda shape, dtype='float64': NDOpArray(np.zeros(shape, dtype=dtype)),
        'ones': lambda shape, dtype='float64': NDOpArray(np.ones(shape, dtype=dtype)),
        'arange': lambda *args: NDOpArray(np.arange(*args)),
        'linspace': lambda start, stop, num=50: NDOpArray(np.linspace(start, stop, int(num))),
        'array->list': lambda arr: arr.data.tolist() if isinstance(arr, NDOpArray) else list(arr),
        'list->array': lambda lst, dtype=None: NDOpArray(lst, dtype=dtype),
        'a+': lambda a, b: NDOpArray(_to_raw(a) + _to_raw(b)),
        'a-': lambda a, b: NDOpArray(_to_raw(a) - _to_raw(b)),
        'a*': lambda a, b: NDOpArray(_to_raw(a) * _to_raw(b)),
        'a/': lambda a, b: NDOpArray(_to_raw(a) / _to_raw(b)),
        'dot': lambda a, b: _wrap_result(np.dot(_to_raw(a), _to_raw(b))),
        'matmul': lambda a, b: _wrap_result(np.matmul(_to_raw(a), _to_raw(b))),
        'mean': lambda arr, axis=None: _wrap_result(np.mean(_to_raw(arr), axis=axis)),
        'std': lambda arr, axis=None: _wrap_result(np.std(_to_raw(arr), axis=axis)),
        'reshape': lambda arr, *shape: NDOpArray(
            np.reshape(_to_raw(arr), shape[0] if len(shape) == 1 and isinstance(shape[0], (list, tuple)) else shape)
        ),
        'shape': lambda arr: list(arr.data.shape) if isinstance(arr, NDOpArray) else [],
    })

for _key, _fn in extra_primitives.items():
    lp.global_env[_key] = lp.Procedure(parms=['*args'], body=None, env=lp.global_env, native_fn=_fn, name=_key)


# --- 2. Fast Primitives & Evaluator Loop ---
def _fast_add(*args: Any) -> Any:
    if len(args) == 2:
        res = args[0] + args[1]
        return res.numerator if type(res) is Fraction and res.denominator == 1 else res
    return lp.normalize(sum(args, 0))

def _fast_sub(*args: Any) -> Any:
    if len(args) == 2:
        res = args[0] - args[1]
        return res.numerator if type(res) is Fraction and res.denominator == 1 else res
    return lp.normalize(lp._variadic_sub(*args))

def _fast_le(*args: Any) -> bool:
    if len(args) == 2:
        return args[0] <= args[1]
    return all(args[i] <= args[i + 1] for i in range(len(args) - 1))

def _fast_lt(*args: Any) -> bool:
    if len(args) == 2:
        return args[0] < args[1]
    return all(args[i] < args[i + 1] for i in range(len(args) - 1))

def _fast_eq(*args: Any) -> bool:
    if len(args) == 2:
        a, b = args[0], args[1]
        if type(a) is int and type(b) is int:
            return a == b
        return lp._lisp_eq(a, b)
    return all(lp._lisp_eq(args[i], args[i + 1]) for i in range(len(args) - 1))

for _k, _fn in [('+', _fast_add), ('-', _fast_sub), ('<=', _fast_le), ('<', _fast_lt), ('=', _fast_eq)]:
    lp.global_env[_k].native_fn = _fn

_orig_eval_exp = lp.eval_exp
SPECIAL_FORMS = lp.SPECIAL_FORMS
macro_table = lp.macro_table
Procedure = lp.Procedure
is_true = lp.is_true

def fast_eval_exp(x: Any, env: lp.Env = lp.global_env) -> Any:
    while True:
        kind = type(x)
        if kind is str:
            if x[0] == ':':
                return x
            curr = env
            while curr is not None:
                if x in curr:
                    return curr[x]
                curr = curr.outer
            raise NameError(f"Undefined symbol: {x}")

        if kind is int or kind is float or kind is Fraction:
            return x

        if kind is list and x:
            proc_exp = x[0]
            if type(proc_exp) is str:
                if proc_exp == 'set!':
                    var = x[1]
                    val = fast_eval_exp(x[2], env)
                    curr = env
                    while curr is not None:
                        if var in curr:
                            curr[var] = val
                            return None
                        curr = curr.outer
                    raise NameError(f"Undefined symbol: {var}")

                if proc_exp == 'if':
                    if is_true(fast_eval_exp(x[1], env)):
                        x = x[2]
                    else:
                        x = x[3] if len(x) > 3 else None
                    continue

                if proc_exp == 'begin':
                    if len(x) == 1:
                        return None
                    for exp in x[1:-1]:
                        fast_eval_exp(exp, env)
                    x = x[-1]
                    continue

                if proc_exp == 'while':
                    test_exp = x[1]
                    body_exps = x[2:]
                    result = None
                    while is_true(fast_eval_exp(test_exp, env)):
                        for b in body_exps:
                            result = fast_eval_exp(b, env)
                    return result

                if not (proc_exp in SPECIAL_FORMS or proc_exp[0] == ':' or ('/' in proc_exp and proc_exp != '/')):
                    if proc_exp in macro_table:
                        x = macro_table[proc_exp](*x[1:])
                        continue

                    nargs = len(x) - 1
                    if nargs == 2:
                        if proc_exp == '+':
                            return fast_eval_exp(x[1], env) + fast_eval_exp(x[2], env)
                        if proc_exp == '-':
                            return fast_eval_exp(x[1], env) - fast_eval_exp(x[2], env)
                        if proc_exp == '<=':
                            return fast_eval_exp(x[1], env) <= fast_eval_exp(x[2], env)
                        if proc_exp == '=':
                            return fast_eval_exp(x[1], env) == fast_eval_exp(x[2], env)
                        if proc_exp == 'vector-ref':
                            return fast_eval_exp(x[1], env)[fast_eval_exp(x[2], env)]
                    elif nargs == 3 and proc_exp == 'vector-set!':
                        fast_eval_exp(x[1], env)[fast_eval_exp(x[2], env)] = fast_eval_exp(x[3], env)
                        return None

                    curr = env
                    proc = None
                    while curr is not None:
                        if proc_exp in curr:
                            proc = curr[proc_exp]
                            break
                        curr = curr.outer
                    if proc is None:
                        raise NameError(f"Undefined symbol: {proc_exp}")

                    args = [fast_eval_exp(arg, env) for arg in x[1:]]
                    if type(proc) is Procedure:
                        if proc.native_fn is not None:
                            if proc.name == 'apply' and len(args) >= 2 and type(args[0]) is Procedure and args[0].native_fn is None:
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

        return _orig_eval_exp(x, env)

lp.eval_exp = fast_eval_exp


def main(argv: list[str]) -> int:
    return lp.main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))