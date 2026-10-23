"""Incremental ANSI removal for the GUI's plain-text output sink."""
class PlainTextOutput:
    def __init__(self):
        self.state = 'text'

    def feed(self, text):
        result = []
        for char in text:
            code = ord(char)
            if self.state == 'text':
                if char == '\x1b': self.state = 'escape'
                elif char == '\x9b': self.state = 'csi'
                elif char in ('\x9d', '\x90', '\x98', '\x9e', '\x9f'): self.state = 'string'
                elif not 0x80 <= code <= 0x9f: result.append(char)
            elif self.state == 'escape':
                if char == '[': self.state = 'csi'
                elif char in ']PX^_': self.state = 'string'
                elif 0x20 <= code <= 0x2f: self.state = 'escape-intermediate'
                elif char != '\x1b': self.state = 'text'
            elif self.state == 'escape-intermediate':
                if 0x30 <= code <= 0x7e: self.state = 'text'
                elif char == '\x1b': self.state = 'escape'
            elif self.state == 'csi':
                if 0x40 <= code <= 0x7e: self.state = 'text'
                elif char == '\x1b': self.state = 'escape'
            elif self.state == 'string':
                if char in ('\x07', '\x9c'): self.state = 'text'
                elif char == '\x1b': self.state = 'string-escape'
            elif self.state == 'string-escape':
                self.state = 'text' if char == '\\' else 'string'
        return ''.join(result)
