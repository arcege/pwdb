#!/usr/bin/python

import os
import sys
import termios

try:
    bytes
except NameError:
    bytes = lambda s, e=None: str(s)
else:
    # the python 3.x 'bytes' requires an encoding argument
    if bytes == str:
        bytes = lambda s, e=None: str(s)
try:
    xrange
except NameError:
    xrange = range

__version = '$Id$'

__all__ = [
    'Console',
    'Ed',
    'Paginator',
]

class Console(object):
    encoding = 'utf-8'

    class Colors:
        map = {
            'black': '0',
            'red': 1,
            'green': 2,
            'yellow': 3,
            'blue': 4,
            'magenta': 5,
            'cyan': 6,
            'white': 7,
        }

        @classmethod
        def show(cls, *text, **kwargs):
            bold = fg = bg = ''
            try:
                if 'attr' in kwargs:
                    if kwargs['attr'] == 'bold':
                        bold = '1'
                    elif kwargs['attr'] == 'dim':
                        bold = '2'
                    elif kwargs['attr'] == 'underscore':
                        bold = '4'
                    elif kwargs['attr'] == 'blink':
                        bold = '5'
                    elif kwargs['attr'] == 'reverse':
                        bold = '7'
                    elif kwargs['attr'] == 'hidden':
                        bold = '8'
                    else:
                        raise ValueError('invalid attr: %s' % kwargs['attr'])
                if 'bg' in kwargs:
                    bg = str(40 + cls.map[kwargs['bg']])
                if 'fg' in kwargs:
                    fg = str(30 + cls.map[kwargs['fg']])
                if bold and (fg or bg):
                    bold += ';'
                if fg and bg:
                    fg += ';'
                s = '\033[' + bold + fg + bg + 'm'
                b = '' # '\033[' + str(bg) + 'm'
                e = '\033[0m'
                txt = ' '.join([str(st) for st in text])
                if not bg and not bold and not fg:
                    return txt
                else:
                    return s + b + txt + e
            except KeyError:
                raise ValueError('no such color: %s' % color)
    show = Colors.show

    def __init__(self, stdin=None, stdout=None, encoding=None):
        self.stdin  = stdin  or sys.stdin
        self.stdout = stdout or sys.stdout
        if encoding:
            self.encoding = encoding

    def write(self, *msg, **kwargs):
        if 'encoding' in kwargs:
            encoding = kwargs['encoding']
        else:
            encoding = self.encoding
        msg = self.show(*msg, **kwargs)
        os.write(self.stdout.fileno(), bytes(msg, encoding))

    def input(self, prompt=''):
        resp = ''
        if prompt:
            self.write(prompt + ' ')
        infd = self.stdin.fileno()
        outfd = self.stdout.fileno()
        old = termios.tcgetattr(infd)
        new = old[:]
        new[3] &= ~(termios.ECHO|termios.ICANON)
        try:
            termios.tcsetattr(infd, termios.TCSAFLUSH, new)
            ch = None
            while ch != '\n':
                ch = os.read(infd, 1)
                if ch == bytes('\x03', 'latin-1'): raise KeyboardInterrupt
                if ch == bytes('\x04', 'latin-1'): raise EOFError
                if ch == bytes('\n', 'latin-1'): # newline
                    break
                if ch in (bytes('\x7f', 'latin-1'), bytes('\b', 'latin-1')):
                    if resp:
                        resp = resp[:-1]
                        self.write('\b \b')
                elif ch == bytes('\x15', 'latin-1'): # '^U' key
                    for i in xrange(len(resp)):
                        self.write('\b \b')
                    resp = ''
                else:
                    resp += str(ch)
                    self.write(ch)
        finally:
            termios.tcsetattr(outfd, termios.TCSADRAIN, old)
            self.write('\n')
        return resp

    def YorN(self, prompt, reqresp=True, allowintr=False):
        """Return True if 'y' or 'Y' are entered, False if 'n' or 'N'
if allowintr is True, then '^C' and '^D' have their usual meanings."""
        resp = ''
        real_prompt = '%s [y/N]' % prompt
        infd = sys.stdin.fileno()
        outfd = sys.stdout.fileno()
        old = termios.tcgetattr(infd)
        new = old[:]
        new[3] &= ~(termios.ECHO|termios.ICANON)
        try:
            termios.tcsetattr(infd, termios.TCSADRAIN, new)
            self.write(real_prompt)
            while not resp:
                ch = os.read(infd, 1)
                if allowintr and ch == '\003': raise KeyboardInterrupt
                if allowintr and ch == '\004': raise EOFError
                if ch.lower() == 'y': resp = 'y'
                elif ch.lower() == 'n': resp = 'n'
                elif not reqresp: break
        finally:
            termios.tcsetattr(outfd, termios.TCSADRAIN, old)
            self.write(resp + '\n')
        return resp == 'y'

    def get_key(self, prompt, allowintr=True, usestdout=False):
        """Using stdin and stderr, prompt for a password key, process certain
terminal special characters like ^C, ^D, ^U, ^H.
"""
        resp = ''
        real_prompt = '%s: ' % prompt
        if not sys.stdin.isatty():
            raise RuntimeError('stdin must be a tty')
        infd = sys.stdin.fileno()
        if usestdout:
            outfd = sys.stdout.fileno()
        else:
            outfd = sys.stderr.fileno()
        old = termios.tcgetattr(infd)
        new = old[:]
        new[3] &= ~(termios.ECHO|termios.ICANON)
        try:
            termios.tcsetattr(infd, termios.TCSAFLUSH, new)
            self.write(real_prompt)
            ch = None
            while ch != '\n':
                ch = os.read(infd, 1)
                #print(repr(ch))
                if allowintr and ch == bytes('\x03', 'latin-1'): raise KeyboardInterrupt
                if allowintr and ch == bytes('\x04', 'latin-1'): raise EOFError
                if ch == bytes('\n', 'latin-1'): # newline
                    break
                elif ch == bytes('\x7f', 'latin-1') or ch == bytes('\b', 'latin-1'): # '^?' or '^H' keys
                    if resp:
                        resp = resp[:-1]
                        self.write('\b \b')
                elif ch == bytes('\x15', 'latin-1'): # '^U' key
                    for i in xrange(len(resp)):
                        self.write('\b \b')
                    resp = ''
                else:
                    resp += str(ch)
                    self.write('*')
        finally:
            termios.tcsetattr(outfd, termios.TCSADRAIN, old)
            self.write('\n')
        return resp

class Ed(object):
    """A wrapper class around the "ed" editor."""
    def __init__(self, lines):
        from tempfile import mktemp
        self.filename = mktemp('ed')
        if lines:
            self.buffer = lines + '\n'
        else:
            self.buffer = ''
    def run(self):
        open(self.filename, 'w').write(bytes(self.buffer, 'utf-8'))
        os.system('ed %s' % self.filename)
        self.buffer = open(self.filename, 'r').read().encode('utf-8')
        os.remove(self.filename)
        return self.buffer.rstrip()

class Paginator(object):
    """Similar to the more(1) utility."""
    def __init__(self, lines, input=None, output=None):
        self.oldtermio = self.newtermio = None
        self.textlines = lines
        self.pos = 0
        self.lines = self.get_lines()
        if input:
            self.infd = input.fileno()
        else:
            self.infd = sys.stdin.fileno()
        if output:
            self.outfd = output.fileno()
        else:
            self.outfd = sys.stdout.fileno()
        self.tcsetattr = termios.tcsetattr
        self.TCSADRAIN = termios.TCSADRAIN
        self.oldtermio = termios.tcgetattr(self.infd)
        self.newtermio = self.oldtermio[:]
        self.newtermio[3] &= ~(termios.ECHO | termios.ICANON)
        self.clrscn = os.popen('tput clear', 'r').readline()
    def __del__(self):
        self.reset()
    def set(self):
        if self.newtermio is not None:
            self.tcsetattr(self.infd, self.TCSADRAIN, self.newtermio)
    def reset(self):
        if self.oldtermio is not None:
            self.tcsetattr(self.infd, self.TCSADRAIN, self.oldtermio)
        self.oldtermio = None
    def run(self):
        done = False
        try:
            self.set()
            while not done:
                self.clear_screen()
                self.display()
                ch = self.more()
                if ch == 'q':
                    done = True
                elif ch == ' ': # space
                    self.pos = min(len(self.textlines), self.pos + self.lines)
                elif ch == 'j' or ch == '\n': # carriage return
                    self.pos = min(len(self.textlines), self.pos + 1)
                elif ch == 'b':
                    self.pos = max(0, self.pos - self.lines)
                elif ch == 'k':
                    self.pos = max(0, self.pos - 1)
                elif ch == 'g':
                    self.pos = 0
                elif ch == 'G':
                    self.pos = len(self.textlines) - self.lines
                elif ch == '\003': # ctrl-C
                    raise KeyboardInterrupt
                elif ch == '\004': # ctrl-D
                    raise EOFError
        finally:
            self.reset()
    def clear_screen(self):
        os.write(self.outfd, bytes(self.clrscn, 'utf-8'))
    def display(self):
        diff = 0
        tl = len(self.textlines)
        start = self.pos
        end = min(tl, self.pos + self.lines - 1)
        if end > tl:
            diff = tl - end
            start -= diff
            end = tl
        #print('pos =', self.pos, 'textlines =', tl,)
        #print('start =', start, 'end =', end, 'diff =', diff)
        for i in xrange(start, end):
            print(self.textlines[i])
    def more(self):
        os.write(self.outfd, bytes('More>', 'utf-8'))
        ch = os.read(self.infd, 1)
        os.write(self.outfd, bytes('\r     \r', 'utf-8'))
        return ch

    @classmethod
    def get_lines(cls):
        try:
            return cls.lines
        except AttributeError:
            try:
                cls.lines = int(os.environ['LINES'])
            except KeyError:
                f = os.popen('stty size', 'r')
                r, c = f.readline().strip().split()
                cls.lines = int(r)
                f.close()
            return cls.lines

