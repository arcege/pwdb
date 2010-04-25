#!/usr/bin/python

import curses
import os
import sys

from pwdb.database import Database, EncryptDatabase, Key

__all__ = [
    'CursesApp',
    'Editor',
    'OK_Dialog',
    'YorN_Dialog',
    'Pad',
]

def log_out(*args):
    global log
    log.write(' '.join([str(s) for s in args]))
    log.write('\n')
    log.flush()

def split_words_to_lines(words, maxlen):
    lines = []
    buffer = ''
    for w in words:
        #print 'buffer =', repr(buffer), 'word =', repr(w)
        if not buffer:
            if len(w) >= maxlen:
                lines.append(w[:maxlen])
                buffer = w[maxlen:]
            else:
                buffer = w
        elif len(buffer + ' ' + w) > maxlen:
            lines.append(buffer)
            if len(w) >= maxlen:
                lines.append(w[:maxlen])
                buffer = w[maxlen:]
            else:
                buffer = w
        else:
            buffer += (' ' + w)
    lines.append(buffer)
    return lines

class Dialog:
    dialog_scale = 0.7
    def __init__(self, root, msg):
        self.root   = root
        maxlen = root.maxwidth * self.dialog_scale
        self.lines  = split_words_to_lines(msg.split(), maxlen)
        #log_out(self.lines)
        self.width  = max([len(l) for l in self.lines]) + 2
        self.height = len(self.lines) + 3
        self.win    = curses.newwin(self.height, self.width,
             (root.maxheight-self.height)/2, (root.maxwidth-self.width)/2,
        )
        lno = 1
        for l in self.lines:
            self.win.move(lno, 1)
            for w in l:
                self.win.addstr(w)
                self.win.addstr(' ')
        self.win.box()
        self.add_buttons()
        self.win.noutrefresh()
    def __del__(self):
        self.close()
    def close(self):
        if self.win:
            self.win.move(0, 0)
            self.win.clrtobot()
            self.win.refresh()
            del self.win
            self.win = None
    def add_buttons(self):
        pass

class OK_Dialog(Dialog):
    def add_buttons(self):
        self.win.addstr(self.height-1, (self.width/2)-1, "OK", curses.A_BOLD)
    def run(self):
        curses.doupdate()
        while True:
            c = self.win.getch()
            if c == 033: # ESC
                return False
            elif c == 012: # CR
                return True
class YorN_Dialog(Dialog):
    def add_buttons(self):
        tl = len('Yes No')
        self.ysp = ((self.width-tl)/2)-1
        self.nsp = self.ysp + 4
        self.win.addstr(self.height-1, self.ysp, "Yes", curses.A_BOLD)
        self.win.addstr(self.height-1, self.nsp, "No")
    def run(self):
        value = 'Y'
        while True:
            curses.doupdate()
            c = self.win.getch()
            if c == 033: # ESC
                return None
            elif c == 012: # CR
                return value
            elif c == 011: # Tab
                if value == 'Y':
                    value = 'N'
                    self.win.attroff(curses.A_BOLD)
                    self.win.addstr(self.height-1, self.ysp, "Yes")
                    self.win.attron(curses.A_BOLD)
                    self.win.addstr(self.height-1, self.nsp, "No")
                    self.win.attroff(curses.A_BOLD)
                elif value == 'N':
                    value = 'Y'
                    self.win.attroff(curses.A_BOLD)
                    self.win.addstr(self.height-1, self.nsp, "No")
                    self.win.attron(curses.A_BOLD)
                    self.win.addstr(self.height-1, self.ysp, "Yes")
                    self.win.attroff(curses.A_BOLD)
            elif c == ord('Y') or c == ord('y'):
                return 'Y'
            elif c == ord('N') or c == ord('n'):
                return 'N'

class Pad:
    def __init__(self, root, elist):
        self.root = root
        self.width = root.maxwidth
        self.maxheight = root.maxheight - 2
        self.list = elist
        maxelen = max([len(e) for e in elist])
        self.numcol, r = divmod(self.width, maxelen)
        if self.numcol < 1:
            self.numcol = 1
            self.maxlen = self.width - 1
        else:
            if r:
                self.numcol += 1
            self.maxlen = self.width / self.numcol - 1
        self.height, r = divmod(len(elist), self.numcol)
        if r:
            self.height += 1
        log_out('Pad.width =', self.width)
        log_out('Pad.height =', self.height)
        log_out('Pad.numcol =', self.numcol)
        log_out('Pad.maxheight =', self.maxheight)
        log_out('Pad.maxlen =', self.maxlen)
        self.win = curses.newpad(self.height, self.width)
        i = j = 0
        for e in self.list:
            log_out('addstr(%d, %d, %s)' % (j, i, repr(e[:self.maxlen])))
            self.win.addstr(j, i, e[:self.maxlen])
            i += (self.maxlen + 1)
            if i >= self.width:
                i = 0
                j += 1
        self.pos = None
        self.scrpos = (0, 0)
        self.move( (0, 0) )
    def refresh(self):
        self.win.refresh(
            self.scrpos[1], self.scrpos[0],
            0, 0,
            self.maxheight, self.width
        )
        self.root.refresh()
    def move(self, pos):
        i, j = pos
        if i < 0:
            i = 0
        elif i >= self.numcol - 1:
            i = self.numcol - 1
        if j < 0:
            j = 0
        elif j >= self.height - 1:
            j = self.height - 1
        y, x = j, i * (self.maxlen + 1)
        l = (j * self.numcol) + i
        try:
            s = self.list[l]
        except IndexError:
            return
        if self.pos:
            oi, oj = self.pos
            oy, ox = oj, oi * (self.maxlen + 1)
            ol = (oj * self.numcol) + oi
            try:
                log_out('move old pos:', self.pos, (oy,ox), repr(self.list[ol]))
            except IndexError:
                log_out('move old pos:', self.pos, (oy,ox))
                raise
            try:
                self.win.addstr(oy, ox, self.list[ol][:self.maxlen])
            except curses.error:
                raise
        log_out('move new pos:', pos, (y,x), repr(self.list[l]))
        try:
            self.win.addstr(y, x, s[:self.maxlen], curses.A_STANDOUT)
        except curses.error:
            self.move(self.pos)
            return
        self.pos = (i, j)
        a = self.need_to_scroll(pos)
        self.scroll(a)
        self.refresh()
    def need_to_scroll(self, pos):
        j = pos[1]
        s = self.scrpos[1]
        e = s + self.maxheight
        if j < s:
            a = j - s
        elif j > e:
            a = j - e
        else:
            a = 0
        return a
    def scroll(self, amt):
        if amt == 0:
            return
        i, j = self.scrpos
        k = j + amt
        if k < 0:
            k = 0
        elif k > self.height - self.maxheight:
            k = self.height - self.maxheight
        else:
            self.scrpos = (i, k)
        self.root.clear()
        self.refresh()

class CursesApp:
    maxheight = 1
    maxwidth  = 1
    def __init__(self):
        self.initialize()

    def initialize(self):
        global LINES, COLS
        self.stdscr = curses.initscr()
        self.maxheight = curses.LINES
        self.maxwidth = curses.COLS
        curses.noecho()     # do not echo what is typed
        try:
            curses.curs_set(0)  # turn off cursor
        except: # curses.error:
            pass  # not supported, ignore
        curses.cbreak()     # raw input mode
        self.stdscr.keypad(0) # allow keypad input mode
        self.errwin = curses.newwin(1, self.maxwidth, self.maxheight-1, 0)

    def __del__(self):
        self.close()

    def close(self):
        if self.stdscr and not curses.isendwin():
            curses.nocbreak()
            self.stdscr.keypad(0)
            curses.echo()
            curses.endwin()
            self.stdscr = None

    def clear(self):  # not sure if this is correct
        self.stdscr.clear()
        self.stdscr.noutrefresh()
    def refresh(self):
        curses.doupdate()

    def display_error_msg(self, message):
        self.clear_errwin()
        self.errwin.addstr(0, 0, message)
        self.errwin.noutrefresh()
    def clear_errwin(self):
        self.errwin.move(0, 0)
        self.errwin.clrtobot()
        self.errwin.noutrefresh()

    def display_entry_draw(self, win, okx, notesx, entry):
        win.box()
        win.addstr(1, 1, "Name:")
        win.addstr(2, 1, "Account:")
        win.addstr(3, 1, "Password:")
        win.addstr(4, 1, "URL:")
        win.addstr(5, 1, "Labels:")
        # "OK   Notes"
        win.addstr(6, okx, "OK", curses.A_BOLD)
        win.addstr(6, notesx, "Notes")
        x = 10
        win.addstr(1, x, str(entry.name)[:30])
        win.addstr(2, x, str(entry.acct)[:30])
        win.addstr(3, x, str(entry.pswd)[:30])
        win.addstr(4, x, str(entry.url)[:30])
        win.addstr(5, x, str(entry.label)[:30])
    def display_entry(self, entry):
        win = curses.newwin(8, 42, (self.maxheight-8)/2, (self.maxwidth-42)/2)
        okx = (self.maxheight/2)-5
        notesx = (self.maxheight/2)
        self.display_entry_draw(win, okx, notesx, entry)
        where = 'ok'
        while True:
            win.refresh()
            c = win.getch()
            if c == 033: # ESC
                break
            elif c == 012: # CR
                if where == 'ok':
                    break
                elif where == 'notes':
                    self.display_notes(entry.notes)
                    self.display_entry_draw(win, okx, notesx, entry)
                    where = 'ok'
                    win.addstr(6, notesx, 'Notes')
                    win.addstr(6, okx, 'OK', curses.A_BOLD)
            elif c == 011: # Tab
                if where == 'ok':
                    where = 'notes'
                    win.addstr(6, okx, 'OK')
                    win.addstr(6, notesx, 'Notes', curses.A_BOLD)
                elif where == 'notes':
                    where = 'ok'
                    win.addstr(6, notesx, 'Notes')
                    win.addstr(6, okx, 'OK', curses.A_BOLD)
        del win
        self.stdscr.refresh()
        self.refresh()
    def display_notes(self, text):
        d = OK_Dialog(self, text)
        r = d.run()
        del d

    def search(self, db):
        width = self.maxwidth-10
        collen = (width / 4) - 1
        win = curses.newwin(self.maxheight-5, self.maxwidth-10, 2, 5)
        win.box()
        term = self.getstr(win, "Search term:", 1, 1)
        try:
            import re
            cmp = re.compile(term, re.IGNORECASE)
        except re.error, e:
            self.display_error_msg(str(e))
            return
        y = 3
        try:
            table = {}
            db.open()
            for entry in db:
                keylen = max([len(k) for k in entry.fieldnames.values()])
                collen = (width - keylen) / 3 - 1
                for key in entry.fieldnames.keys():
                    val = getattr(entry, key)
                    if cmp.search(val):
                        # was this entry's name printed already
                        n = val.find('\n')
                        if n != -1:
                            m = n
                        else:
                            m = collen*2
                        s =  "%-*s %-*s %-*s" % (
                            collen, entry.name[:collen], keylen, entry.fieldnames[key], m, val[:m]
                        )
                        win.addstr(y, 2, s)
                        table[y] = {
                            'entry': entry,
                            'string': s,
                        }
                        y += 1
            l = y - 1
            y = 3
            win.addstr(y, 2, table[y]['entry'].name[:collen], curses.A_BOLD)
            while True:
                win.refresh()
                c = win.getch()
                if c == 033: # ESC
                    return None
                elif c == 012: # CR
                    return table[y]['entry']
                elif c == ord('k'):# up
                    if y > 3:
                        win.addstr(y, 2, table[y]['entry'].name[:collen])
                        y -= 1
                        win.addstr(y, 2, table[y]['entry'].name[:collen], curses.A_BOLD)
                elif c == ord('j'): # down
                    if y <= l:
                        win.addstr(y, 2, table[y]['entry'].name[:collen])
                        y += 1
                        win.addstr(y, 2, table[y]['entry'].name[:collen], curses.A_BOLD)
        finally:
            db.close()
            del win
        return None


    def getstr(self, win, prompt, y, x, mask=False):
        st = x + len(prompt) + 1
        win.addstr(y, x, prompt)
        p = st
        win.move(y, p)
        try:
            curses.curs_set(1)
        except:
            pass
        s = []
        while True:
            win.refresh()
            c = win.getch()
            self.clear_errwin()
            if c == 033: # ESC
                del s[:]
                break
            elif c == 012: # CR
                break
            elif c == 025: # ^U
                for i in xrange(p, st-1, -1):
                    win.addch(y, i, ord(' '))
                p = st
                win.move(y, p)
                win.noutrefresh()
                del s[:]
            elif c == 0177 or c == 010: # ^? (DEL) or ^H (BS)
                if p-1 >= st:
                    p -= 1
                    win.addch(y, p, ord(' '))
                    win.move(y, p)
                    win.noutrefresh()
                    del s[-1:]
            elif c >= 040 and c < 0177: # standard ASCII printables
                if mask:
                    win.addch(1, p, ord('*'))
                else:
                    win.addch(1, p, c)
                win.noutrefresh()
                p += 1
                s.append(chr(c))
            else:
                self.display_error_msg('Invalid character')
        return ''.join(s)

    def select_scrolling_list(self, elist):
        pass

    def prompt_key(self):
        win = curses.newwin(3, 32, (self.maxheight/2)-1, (self.maxwidth-30)/2)
        win.box()
        s = self.getstr(win, "Key:", 1, 1, mask=True)
        del win
        return s

class Editor:
    def __init__(self, lines):
        from tempfile import mktemp
        self.filename = mktemp('ed')
        if lines:
            self.buffer = lines + '\n'
        else:
            self.buffer = ''
        curses.savetty()
    def run(self):
        open(self.filename, 'w').write(self.buffer)
        #curses.nocbreak()
        #curses.echo()
        curses.reset_shell_mode()
        editor = 'vi'
        if os.environ.has_key('VISUAL') and os.environ['VISUAL']:
            editor = os.environ['VISUAL']
        elif os.environ.has_key('EDITOR') and os.environ['EDITOR']:
            editor = os.environ['EDITOR']
        os.system('%s %s' % (editor, self.filename))
        curses.reset_prog_mode()
        curses.resetty()
        lines = open(self.filename, 'r').read()
        os.remove(self.filename)
        if lines == self.buffer:
            return None
        else:
            return lines.rstrip()

if __name__ == '__main__':
    log = open('screen.app.log', 'w')
    app = CursesApp()
    try:
        key = app.prompt_key()
        log_out('Key =', repr(key))
        app.clear()
        ed = Editor('Hello, World')
        lines = ed.run()
        app.clear()
        log_out('editor results =', repr(lines))
        d = YorN_Dialog(app, 'Hello, World')
        r = d.run()
        log_out('response =', r)
    finally:
        app.close()

