# PIL x86 engine

PIL (Processor Instruction Language) is Tony's x86 project,
[pyTony/PIL-Processor-Instruction-Language](https://github.com/pyTony/PIL-Processor-Instruction-Language).
Its `.pil` files describe what each 386 instruction does; a Rust engine decodes
real x86 code, runs those descriptions and provides a small DOS. Lispy does not
copy any of it: it starts the built `pil` program and talks to it, the same way
PIL's own debugger window does.

## Setting up

1. Clone the PIL repository's `dev` branch (it has the `tools/` windows), for
   example next to the Lispy folder.
2. Build it once: `cargo build --release`.
3. In the Machine, open **Eval > PIL x86 engine > PIL Settings** and choose the
   PIL folder. Lispy uses the newest `pil.exe` under `target/`. A PIL folder
   next to the Lispy folder is found without setting anything.
4. For assembly buffers, install NASM (see below). Everything else works
   without it.

For `python lispy3.py` the environment variables `PIL_DIRECTORY`, `PIL_ENGINE`
and `NASM` do the same.

## NASM (optional)

[NASM](https://www.nasm.us) is the assembler Lispy uses for `.asm` buffers.
Only F5/F6 in an assembly buffer and **Assemble and run x86 buffer** need it;
`(pil ...)`, the PIL debugger and running a ready `.COM` or `.EXE` do not.

- **Windows:** run the installer from [nasm.us](https://www.nasm.us), or
  `winget install NASM.NASM`. The installer does not add NASM to PATH, but
  Lispy still finds it in `C:\Program Files\NASM` and in
  `%LOCALAPPDATA%\bin\NASM`, where a per-user install goes.
- **Linux:** `sudo apt install nasm` (or your distribution's package).
- **macOS:** `brew install nasm`.

If NASM is somewhere else, choose `nasm.exe` in **PIL Settings**, or set the
`NASM` environment variable for `python lispy3.py`. `nasm -v` in a terminal
shows whether NASM is on PATH.

## Checking the setup

    pytest -rs tests/test_pil_engine.py tests/test_pil_live.py

`test_pil_engine.py` needs nothing installed; only its assembly test is
skipped without NASM. `test_pil_live.py` uses the real PIL: it runs the hello
demo through the built engine, runs a NASM-assembled monitor program, and
checks that PIL's own `programs/dos/*.asm` assemble in Lispy to the same bytes
as their `.COM` files. Each test is skipped, with the reason shown by `-rs`,
when the PIL checkout, the build or NASM is missing.

## From Lisp

`(pil "command")` sends one command to the engine's debugger, starting the
engine on first use. Anything the guest program writes to its serial port is
printed; the result is the engine's reply text. `(pil-run n)` runs up to `n`
instructions and returns why it stopped.

```lisp
(pil "demo hello")
(pil-run 1000)            ; prints Hello, world! and returns halt
(get (pil-state) 'eip)    ; registers, eip, flags, status and demo
(pil "regs")              ; any debugger command: step, list, mem 0x500 8, ...
(pil "help")
(pil-stop)
```

`(pil-start "prog.bin")` starts a fresh engine with a raw image at CS:0100.

## From the menu

**Eval > PIL x86 engine** opens PIL's own windows:

- **Open PIL debugger** - registers, listing, memory and PIL token stepping.
- **Run DOS program in PIL…** - a `.COM` or `.EXE` in PIL's DOS text window.
- **Assemble and run x86 buffer** - the same as F5/F6 in an assembly buffer.

## x86 assembly buffers

Files ending `.asm` are coloured as x86 assembly. F5 or F6 assembles the whole
buffer with `nasm -f bin` and runs the result in PIL. `%include` and `incbin`
look in the buffer's folder. A NASM error is shown in the Listener and its line
is marked in the buffer.

Write the program as a DOS `.COM`, as PIL's `programs/dos/*.asm` are:

```nasm
; pil-args: 30
        org 100h
        cpu 386
        mov dx,msg
        mov ah,9
        int 21h
        mov ax,4c00h
        int 21h
msg:    db 'Hello from PIL',13,10,'$'
```

Two optional comment lines, which NASM ignores, choose how Lispy runs it:

| Line | Meaning |
|------|---------|
| `; pil: dos` | run as a DOS `.COM` in PIL's DOS window (the default) |
| `; pil: monitor` | load the raw bytes into the PIL debugger at CS:0100, without DOS; output goes to port E9 (`out 0e9h,al`) |
| `; pil-args: TEXT` | the program's command line, as in `FACTOR 30` |

## `.pil` buffers

`.pil` description files are coloured too. The engine has its descriptions
built in, so F5/F6 does not run a `.pil` buffer; rebuild PIL after changing
one, or step through instructions with **pilstep** in the PIL debugger.
