#!/usr/bin/python

import os
import sys
import termios

__version = '$Id$'

__all__ = [
    'Ed',
    'get_key',
    'Paginator',
    'YorN',
]

class Ed:
    """A wrapper class around the "ed" editor."""
    def __init__(self, lines):
        from tempfile import mktemp
        self.filename = mktemp('ed')
        if lines:
            self.buffer = lines + '\n'
        else:
            self.buffer = ''
    def run(self):
        open(self.filename, 'w').write(self.buffer)
        os.system('ed %s' % self.filename)
        self.buffer = open(self.filename, 'r').read()
        os.remove(self.filename)
        return self.buffer.rstrip()

def get_key(prompt, allowintr=True, usestdout=False):
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
        os.write(outfd, real_prompt)
        ch = None
        while ch != '\n':
            ch = os.read(infd, 1)
            if allowintr and ch == '\003': raise KeyboardInterrupt
            if allowintr and ch == '\004': raise EOFError
            if ch == '\n': # newline
                break
            elif ch == '\177' or ch == '\b': # '^?' or '^H' keys
                if resp:
                    resp = resp[:-1]
                    os.write(outfd, '\b \b')
            elif ch == '\025': # '^U' key
                for i in xrange(len(resp)):
                    os.write(outfd, '\b \b')
                resp = ''
            else:
                resp += ch
                os.write(outfd, '*')
    finally:
        termios.tcsetattr(outfd, termios.TCSADRAIN, old)
        os.write(outfd, '\n')
    return resp

class Paginator:
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
        os.write(self.outfd, self.clrscn)
    def display(self):
        diff = 0
        tl = len(self.textlines)
        start = self.pos
        end = min(tl, self.pos + self.lines - 1)
        if end > tl:
            diff = tl - end
            start -= diff
            end = tl
        #print 'pos =', self.pos, 'textlines =', tl,
        #print 'start =', start, 'end =', end, 'diff =', diff
        for i in xrange(start, end):
            print self.textlines[i]
    def more(self):
        os.write(self.outfd, 'More>')
        ch = os.read(self.infd, 1)
        os.write(self.outfd, '\r     \r')
        return ch
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
    get_lines = classmethod(get_lines)

def YorN(prompt, reqresp=True, allowintr=False):
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
        os.write(outfd, real_prompt)
        while not resp:
            ch = os.read(infd, 1)
            if allowintr and ch == '\003': raise KeyboardInterrupt
            if allowintr and ch == '\004': raise EOFError
            if ch.lower() == 'y': resp = 'y'
            elif ch.lower() == 'n': resp = 'n'
            elif not reqresp: break
    finally:
        termios.tcsetattr(outfd, termios.TCSADRAIN, old)
        os.write(outfd, resp)
        os.write(outfd, '\n')
    return resp == 'y'

