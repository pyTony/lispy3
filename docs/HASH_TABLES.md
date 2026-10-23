# Hash tables and manual memoization

`(make-hash-table)` creates a fresh mutable table. `(gethash key table)` returns
its stored value or `nil` when absent. `(gethash key table default)` uses the
default only when the key is missing, including when a stored value is zero or nil.

```lisp
(define memo (make-hash-table))
(setf (gethash 10 memo) 55) ; returns 55
(gethash 10 memo)         ; 55
(gethash 11 memo 0)       ; 0
```

`setf` supports variables and hash-table entries. Each place/value pair finishes
before the next pair starts. For a hash place, the key, table, optional lookup
default and assigned value are evaluated once, from left to right. The default
is evaluated but does not affect assignment. The result is the last assigned value.

The Common Lisp book's manual memoization pattern works directly:

```lisp
(let ((memo (make-hash-table)))
  (defun fibonacci (n)
    (let ((value (gethash n memo)))
      (cond ((<= n 1) n)
            (value value)
            (t (setf (gethash n memo)
                     (+ (fibonacci (- n 1)) (fibonacci (- n 2)))))))))

(fibonacci 40) ; 102334155
```

`defun` publishes the function while its closure retains the local table.
Repeated calls reuse stored values. Redefining through another enclosing `let`
creates a fresh cache. `define-memo` remains an alternative when explicit cache
management is unnecessary.

This is a small Common Lisp compatibility subset: table storage uses Python dict
key equality and requires hashable keys. `make-hash-table` accepts no keyword
options, and `gethash` returns one value (no second presence value). Built-in generalized
places such as `(car x)`, `defsetf` and `define-setf-expander` are not supported.

## User-defined setters

A setter has a separate function binding from its getter and from the `setf`
macro. It takes the new value first, followed by the accessor arguments:

```lisp
(defun area (square)
  (expt (gethash :width square) 2))

(defun (setf area) (new-area square)
  (setf (gethash :width square) (sqrt new-area)))

(define square (make-hash-table))
(setf (gethash :width square) 21)
(setf (area square) 100) ; returns 10, the setter's final value
(area square)           ; 100
```

Accessor arguments are evaluated once, left to right, then the new-value form
is evaluated once. The setter receives the new value first. As in Common Lisp,
the result comes from the storing function: return the new value explicitly at
the end of a setter if that is the desired result. See the
[Common Lisp SETF specification](https://www.lispworks.com/documentation/HyperSpec/Body/m_setf_.htm).

Setters defined inside a `let` retain that local environment and remain globally
named, like other Lispy `defun` definitions. Optional/rest/key parameters use the
normal function parameter rules. Unknown setters and malformed function names
produce errors. A book's `(defun (setf function-name) ... body)` template is an
illustration; replace its placeholders or leave it commented out.
