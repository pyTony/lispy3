"""Line-oriented mini-basic session; program editing never evaluates source."""
import re
from pathlib import Path


class BasicRepl:
    def __init__(self, runtime, read_source=None):
        self.runtime = runtime
        self.manager = runtime.workspaces
        self.workspace = None
        self.lines = {}
        self.read_source = read_source or self._read_source

    @staticmethod
    def _read_source(path):
        if path.suffix.lower() == '.bbc':
            raise ValueError('Tokenised .bbc input requires the configured Python mini_basic decoder')
        return path.read_text(encoding='utf-8-sig')

    def close(self):
        if self.workspace is not None:
            old, self.workspace = self.workspace, None
            self.manager.discard(old)

    def _fresh(self):
        self.close()
        self.workspace = self.manager.create('BASIC REPL')
        with self.manager.use(self.workspace):
            r = self.runtime
            r.eval_exp(r.parse('(import (only mini-basic bbc-run))'), r.global_env)

    def _execute(self, source):
        if self.workspace is None:
            self._fresh()
        with self.manager.use(self.workspace):
            r = self.runtime
            form = r.expand(['bbc-run', r.String(source)], toplevel=True)
            r.eval_exp(form, r.global_env)

    @staticmethod
    def _filename(text):
        match = re.fullmatch(r'"((?:[^"]|"")+)"', text.strip())
        if not match:
            raise ValueError('Use a quoted filename, for example LOAD "program.bas"')
        return Path(match[1].replace('""', '"')).expanduser()

    def source(self):
        return ''.join(f'{number} {body}\n' for number, body in sorted(self.lines.items()))

    def submit(self, line):
        line = line.strip()
        if not line:
            return
        numbered = re.fullmatch(r'(\d+)\s*(.*)', line)
        if numbered:
            number = int(numbered[1])
            if not 1 <= number <= 65535:
                raise ValueError('Line number must be between 1 and 65535')
            body = numbered[2] or ''
            if body: self.lines[number] = body
            else: self.lines.pop(number, None)
            return
        parts = line.split(maxsplit=1)
        command, argument = parts[0], parts[1] if len(parts) == 2 else ''
        command = command.upper()
        if command in ('RUN', 'LIST', 'NEW', 'HELP'):
            if argument.strip():
                raise ValueError(f'{command} takes no arguments')
            if command == 'LIST':
                print(self.source(), end='')
            elif command == 'HELP':
                print('BASIC statements; numbered lines store/replace, a bare number deletes.\n'
                      'RUN  LIST  NEW  LOAD "file.bas"  SAVE "file.bas"\n'
                      'RUN starts fresh; immediate statements retain session variables.')
            elif command == 'NEW':
                self.lines.clear()
                self._fresh()
            else:
                self._fresh()
                if self.lines: self._execute(self.source())
            return
        if command in ('LOAD', 'SAVE'):
            path = self._filename(argument)
            if command == 'SAVE':
                if path.suffix.lower() == '.bbc':
                    raise ValueError('SAVE writes text; choose a .bas filename, not .bbc')
                path.write_text(self.source(), encoding='utf-8')
            else:
                text = self.read_source(path)
                rows = [row for row in text.splitlines() if row.strip()]
                numbered = [re.fullmatch(r'\s*(\d+)\s*(.*)', row) for row in rows]
                reserved = {int(match[1]) for match in numbered if match}
                lines = {}
                previous = 0
                for i, row in enumerate(rows):
                    number = (int(numbered[i][1]) if numbered[i] else
                              (i+1)*10 if not reserved else previous+1)
                    if not numbered[i] and reserved:
                        while number in reserved: number += 1
                        following = next((int(match[1]) for match in numbered[i+1:] if match), None)
                        if following is not None and number >= following:
                            raise ValueError('No free line numbers for unnumbered source; number the file consistently')
                    if not 1 <= number <= 65535:
                        raise ValueError('Line number must be between 1 and 65535')
                    lines[number] = numbered[i][2] if numbered[i] else row
                    previous = number
                self.lines = lines
            return
        self._execute(line)


def setup_completion():
    try:
        import readline
    except ImportError:
        return False
    from repl_completion import filename_completion
    import syntax_highlight as syntax
    languages, _ = syntax.load_languages()
    language = syntax.language_for('repl.bas', languages)
    names = {name.upper() for name in language.words} | {'RUN','LIST','NEW','LOAD','SAVE','HELP','QUIT'}
    matches = []
    def complete(text, state):
        nonlocal matches
        if state == 0:
            before = readline.get_line_buffer()[:readline.get_endidx()]
            files = filename_completion(before, basic=True)
            if files is not None:
                start, paths = files
                matches = [before[:start]+path for path in paths]
            else:
                word = re.search(r'[A-Za-z]*$', before)
                matches = [before[:word.start()]+name for name in sorted(names)
                           if name.startswith(word[0].upper())]
        return matches[state] if state < len(matches) else None
    readline.set_completer_delims('\n')
    readline.set_completer(complete)
    readline.parse_and_bind('bind ^I rl_complete' if 'libedit' in (readline.__doc__ or '') else 'tab: complete')
    return True


def main():
    import lispy3
    session = BasicRepl(lispy3)
    setup_completion()
    print('Lispy mini-basic. HELP for commands; QUIT to exit.')
    try:
        while True:
            try:
                line = input('BASIC> ')
                if line.strip().upper() == 'QUIT':
                    break
                session.submit(line)
            except EOFError:
                break
            except KeyboardInterrupt:
                print('\nStopped')
            except Exception as error:
                print(f'Error: {error}')
    finally:
        session.close()


if __name__ == '__main__':
    main()
