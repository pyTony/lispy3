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

## x86 binary buffers

Files ending `.hex`, `.bin` or `.com` are coloured as x86 binary. F5 or F6 runs
them directly in PIL without needing NASM:

- `.hex` files hold whitespace-separated hex bytes (e.g. `b0 48 e6 e9 f4`) and
  comments starting with `;` or `#`. They default to running in the PIL
  debugger (`monitor` mode).
- `.bin` files are raw monitor images. Opening a `.bin` file in the Machine
  formats it as hex text with an initial `; pil: monitor` directive; saving
  writes raw bytes back to disk.
- `.com` files are DOS executables. Opening a `.com` file formats it as hex text
  with an initial `; pil: dos` directive; saving writes raw bytes back to disk.

As with assembly buffers, `; pil: dos`, `; pil: monitor` and `; pil-args: TEXT`
choose how the binary runs. Any byte format error highlights the faulty line.

## Disassembling

**Eval > PIL x86 engine > Disassemble x86 program…** turns a `.com`, `.bin`
or `.hex` program back into NASM source and opens it as an `.asm` buffer.
**Disassemble x86 binary buffer** does the same for the hex buffer you are in.
From Lisp, `(pil-disassemble "PROG.COM")` returns the source as a string.
It uses `ndisasm`, which comes with NASM; PIL itself is not needed.

```nasm
; FACTOR.COM: 293 bytes, disassembled by ndisasm
; F5/F6 assembles it again with NASM and runs it in PIL.
; pil: dos
        org 0x100

        mov si,0x81                     ; 0100  BE8100        ...
L0107:
        lodsb                           ; 0107  AC            .
        cmp al,0x20                     ; 0108  3C20          .
        jz short L0107                  ; 010A  74FB          t.
```

- The buffer assembles back to exactly the same bytes, so F5 runs the
  program again: a `.com` gets `; pil: dos` and runs in PIL's DOS window,
  a `.bin` or `.hex` gets `; pil: monitor` and runs in the PIL debugger.
- Jump, call and loop targets become labels (`L0107`), so you can insert
  code. Data addresses such as `mov dx,0x1d7` stay numbers: after an edit
  that moves the data, change them to labels yourself.
- Each comment gives the address, the bytes and their ASCII, which shows
  where text is. The disassembler cannot tell data from code, so text comes
  out as odd instructions.
- A line NASM would encode differently, or would not accept, is written as
  `db` bytes with ndisasm's instruction after it.
- Programs load at 100h and decode as 16-bit code. MZ `.exe` files are not
  disassembled.

## `.pil` buffers

`.pil` description files are coloured too. The engine has its descriptions
built in, so F5/F6 does not run a `.pil` buffer; rebuild PIL after changing
one, or step through instructions with **pilstep** in the PIL debugger.
