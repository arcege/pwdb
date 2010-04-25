#!/usr/bin/python

import getopt
import os
import sys
if os.path.exists(os.path.join(os.curdir, 'lib', 'pwdb')):
    libdir = os.path.join(os.curdir, 'lib')
elif os.path.exists(os.path.expanduser(os.path.join('~', 'lib'))):
    libdir = os.path.expanduser(os.path.join('~', 'lib'))
else:
    libdir = os.path.os.path.normpath(
        os.path.join(os.path.dirname(sys.argv[0]), os.pardir, 'lib')
    )
sys.path.insert(0, libdir)
from pwdb.database import Database, EncryptDatabase, Key
from screen.app import CursesApp, Editor, OK_Dialog, YorN_Dialog, Pad

DB_Filename = os.path.expanduser(os.path.join('~', '.pwdb'))

class App:
    def __init__(self, ui, key):
        global DB_Filename
        self.ui = ui
        #kls = Database.check_file_type(DB_Filename)
        #if issubclass(kls, EncryptDatabase):
        #    k = ui.prompt_key()
        #    if not k:
        #        raise SystemExit
        #    key = Key(k)
        #    del k
        self.db = kls(DB_Filename, key)

    def run(self):
        self.db.open()
        entrynames = [ e.name for e in self.db ]
        self.ui.display_error_msg('Starting...')
        self.ui.refresh()
        self.pad = Pad(self.ui, entrynames)
        self.main_screen()
    def main_screen(self):
        while True:
            self.ui.refresh()
            c = self.ui.stdscr.getch()
            if c == 033: # ESC  quit
                break
            elif c == 012: # CR  select
                i, j = self.pad.pos
                p = j * self.pad.numcol + i
                self.show_entry(self.pad.list[p])
                self.pad.move(self.pad.pos)
            elif c == 014: # ^L  refresh
                self.ui.refresh()
            elif c == ord('/'): # search
                self.search()
            elif c == ord('h'): # left
                i, j = self.pad.pos
                self.pad.move( (i-1, j) )
            elif c == ord('l'): # right
                i, j = self.pad.pos
                self.pad.move( (i+1, j) )
            elif c == ord('k'): # up
                i, j = self.pad.pos
                self.pad.move( (i, j-1) )
            elif c == ord('j'): # down
                i, j = self.pad.pos
                self.pad.move( (i, j+1) )
            elif c == ord('K'): # up screen
                i, j = self.pad.pos
                self.pad.move( (i, j-self.pad.maxheight) )
            elif c == ord('J'): # down screen
                i, j = self.pad.pos
                self.pad.move( (i, j+self.pad.maxheight) )
    def show_entry(self, entryname):
        e = self.db.find(entryname)
        self.ui.display_entry(e)
    def edit_entry(self, entryname):
        e = self.db.find(entryname)
        if self.ui.display_entry(e):
            self.db.set(e)
    def enter_new(self):
        pass
    def search(self):
        e = self.ui.search(self.db)
        if e:
            self.ui.display_entry(e)
    def tag_management(self):
        pass
    def advanced(self):
        pass
    def help(self):
        pass

def real_main(ui, key):
    App(ui, key).run()

def profile_main(ui, key):
    global Profile_fname
    profile.runctx("real_main(ui, key)", globals(), locals(), Profile_fname)

if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'f:h',
                                    ['file=', 'help'])
    except getopt.error, e:
        raise SystemExit(e)
    for opt, val in opts:
        if opt == '--':
            break
        elif opt in ('-h', '--help'):
            print sys.argv[0], '[opts]'
            print '  -h|--help'
            print '  -f|--file=dbfile'
            raise SystemExit
        elif opt in ('-f', '--file'):
            DB_Filename = val

    kls = Database.check_file_type(DB_Filename)
    import screen.app
    screen.app.log = open('screen.app.log', 'w')
    ui = CursesApp()
    try:
        if kls == EncryptDatabase:
            k = ui.prompt_key()
            if not k:
                raise SystemExit
            key = Key(k)
            del k
        else:
            key = None
        if os.environ.has_key('PROFILING'):
            if os.environ['PROFILING']:
                Profile_fname = os.environ['PROFILING']
            else:
                Profile_fname = os.path.basename(sys.argv[0] + '.prof')
            profiling = True
            try:
                import cProfile as profile
            except ImportError:
                import profile
            mainfunc = profile_main
        else:
            profiling = False
            mainfunc = real_main
        try:
            mainfunc(ui, key)
        except RuntimeError, msg:
            raise SystemExit(msg)
        except KeyboardInterrupt:
            pass  # should we get this?
    finally:
        ui.close()
