# Regression fixtures

Regression inputs here are stable test data. Tests must not depend on edits to
user-facing demo programs under `basic/examples/` or `lisp/programs/`.

`basic/primes_input.bas` exercises numeric INPUT followed by an Enter pause,
FOR/GOSUB control flow and output after the pause. Supply `30` and an empty
line: it counts 10 primes including 2 and finishes with BYE!.
