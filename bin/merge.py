#!/usr/bin/python

import os
import sys
if os.path.exists(os.path.join(os.curdir, 'lib', 'pwdb')):
    libdir = os.path.join(os.curdir, 'lib')
else:
    libdir = os.path.expanduser(os.path.join('~', 'lib'))
sys.path.insert(0, libdir)
import pwdb.database
from pwdb.console import get_key

__version = '$Id$'

fmt = '%39.39s'
fmtstr = '%s %s' % (fmt, fmt)
#fmtstr = '%39.39s %39.39s'

def show_diff(l, r):
    def dist(l, r):
        if l == r:
            print fmt % str(l)[:39]
        else:
            print fmtstr % (str(l)[:39], str(r)[:39])
    print fmtstr % ('differences: left', 'right')
    dist(l.uid, r.uid)
    dist(l.mtime, r.mtime)
    dist(l.name, r.name)
    dist(l.acct, r.acct)
    dist(l.pswd, r.pswd)
    dist(l.url, r.url)
    dist(l.label, r.label)
    if l.notes == r.notes:
        print l.notes
    else:
        ln = l.notes.split('\n')
        rn = l.notes.split('\n')
        for i in xrange(min(len(ln), len(rn))):
            print fmtstr % (ln[i][:39], rn[i][:39])
        if len(ln) > len(rn):
            for i in xrange(len(ln), len(rn)):
                print fmtstr % (ln[i][:39], '')
        else:
            for i in xrange(len(ln), len(rn)):
                print fmtstr % ('', rn[i][:39])
def show_entry(e, caption):
    print fmt % caption
    print fmt % str(e.uid)[:39]
    print fmt % e.mtime
    print fmt % e.name[:39]
    print fmt % e.acct[:39]
    print fmt % e.pswd[:39]
    print fmt % e.url[:39]
    print fmt % e.label[:39]
    print fmt % e.notes[:39]

def merge(db, e1, e2):
    if e1.uid != e2.uid:
        assert e1.name == e2.name, 'names of entries not equal'
        # better thing to do is create an entry with new UID
        if e1.mtime < e2.mtime:
            e = psdb.database.Entry(db,
                e2.name, e2.label, e2.url, e2.acct, e2.pswd,
                e2.notes, e2.mtime, None # force new UID
            )
        else:
            e = psdb.database.Entry(db,
                e1.name, e1.label, e1.url, e1.acct, e1.pswd,
                e1.notes, e1.mtime, None # force new UID
            )
    elif e1.mtime < e2.mtime:
        e = pwdb.database.Entry(db,
            e2.name, e2.label, e2.url, e2.acct, e2.pswd,
            e2.notes, e2.mtime, e2.uid
        )
    else:
        e = pwdb.database.Entry(db,
            e1.name, e1.label, e1.url, e1.acct, e1.pswd,
            e1.notes, e1.mtime, e1.uid
        )
    return e

def normuserpath(filename):
    return os.path.normpath(os.path.expanduser(filename))

class App:
    def __init__(self, args):
        self.args = args
        self.oper = 'merge'
        self.getargs()
        if self.oper == 'dump':
            db = self.retrieve_db(self.dbfile)
            self.task_dump(db)
            db.close()
        elif self.oper == 'diff':
            dbleft = self.retrieve_db(self.leftfname)
            dbright = self.retrieve_db(self.rightfname)
            tomerge = self.analyze_databases(dbleft, dbright)
            dbleft.close()
            dbright.close()
            self.task_diff(tomerge)
        elif self.oper == 'merge':
            dbleft = self.retrieve_db(self.leftfname)
            dbright = self.retrieve_db(self.rightfname)
            tomerge = self.analyze_databases(dbleft, dbright)
            self.task_merge(dbleft, dbright, tomerge)
            dbleft.close()
            dbright.close()
    def getargs(self):
        try:
            if len(self.args) < 1:
                self.help()
                raise SystemExit('Too few arguments')
            if len(self.args) == 1:
                self.oper = 'dump'
                self.dbfile = normuserpath(self.args[0])
            elif len(self.args) == 2:
                self.oper = 'diff'
                self.leftfname = normuserpath(self.args[0])
                self.rightfname = normuserpath(self.args[1])
            elif len(self.args) == 3:
                self.oper = 'merge'
                self.leftfname = normuserpath(self.args[0])
                self.rightfname = normuserpath(self.args[1])
                self.outfname = normuserpath(self.args[2])
            else:
                self.help()
                raise SystemExit('Too many arguments')
        except IndexError:
            self.help()
            raise SystemExit('Expected arguments')
        if self.args[0] in ('-h', '--help', 'help'):
            self.help()
            raise SystemExit
    def help(self):
        progname = os.path.basename(sys.argv[0])
        print progname, 'dbfile - dump dbfile'
        print progname, 'left right - show diff between left&right'
        print progname, 'left right output - merge left&right to output'
    def retrieve_db(self, filename):
        key = None
        kls = pwdb.database.Database.check_file_type(filename)
        if kls.need_key:
            key = pwdb.database.Key(get_key('Key for %s' % filename))
        db = kls(filename, key)
        return db
    def analyze_databases(self, dbleft, dbright):
        tomerge = []
        left = list(dbleft)
        right = list(dbright)
        leftids, rightids = {}, {}
        leftnames, rightnames = {}, {}
        for e in left:
            leftids[e.uid] = e
            leftnames[e.name] = e
        for e in right:
            rightids[e.uid] = e
            rightnames[e.name] = e
        left.sort()   # sort by uid
        right.sort()  # sort by uid
        tomerge = []
        # check for names before UIDs
        for lkey, lval in leftnames.items():
            if rightnames.has_key(lkey):
                if rightnames[lkey].uid != lval.uid:
                    # same name, different UIDs = possible merge; check data
                    tomerge.append( (False, lval, rightnames[lkey] ) )
                    del leftids[lval.uid]
                    del rightids[rightnames[lkey].uid]
        for lkey, lval in leftids.items():
            if rightids.has_key(lkey):
                if rightids[lkey].name != lval.name:
                    # same UIDs, different names = possible merge; check data
                    tomerge.append( (False, lval, rightids[lkey]) )
                elif rightids[lkey].mtime != lval.mtime:
                    # same UIDs&name, different mtimes = merge
                    tomerge.append( (False, lval, rightids[lkey]) )
                else:
                    # same UIDs&name&mtime
                    tomerge.append( (True, lval, None) )
            else:
                tomerge.append( (False, lval, None) )
        for rkey, rval in rightids.items():
            if not leftids.has_key(rkey):
                tomerge.append( (False, None, rval) )
        return tomerge
    def task_dump(self, db):
        for e in db:
            show_entry(e, caption='-' * 40)
    def task_diff(self, tomerge):
        for same, lval, rval in tomerge:
            if same:
                pass  # ignore entries that are the same
            elif lval is None:
                show_entry(rval, caption='only in right')
            elif rval is None:
                show_entry(lval, caption='only in left')
            else:
                show_diff(lval, rval)
    def task_merge(self, dbleft, dbright, tomerge):
        newkey = get_key(self.outfname)
        dbnew = pwdb.database.EncryptDatabase(self.outfname, newkey)
        newentries = []
        for same, lval, rval in tomerge:
            if same or rval is None:
                newentries.append( lval )
            elif lval is None:
                newentries.append( rval )
            else:
                newentries.append( merge(dbnew, lval, rval) )
        dbnew.open()
        if dbleft.uid > dbright.uid:
            dbnew.set_uid(dbleft.uid)
        else:
            dbnew.set_uid(dbright.uid)
        dbnew.extend(newentries)
        dbnew.update()
        dbnew.close()

def real_main(args):
    App(args)

def profile_main(args):
    global Profile_fname
    profile.runctx("real_main(args)", globals(), locals(), Profile_fname)

if __name__ == '__main__':
    if os.environ.has_key('PROFILING'):
        if os.environ['PROFILING']:
            Profile_fname = os.environ['PROFILING']
        else:
            Profile_fname = None
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
        mainfunc(sys.argv[1:])
    except ValueError, msg:
        raise SystemExit(msg)
    except RuntimeError, msg:
        raise SystemExit(msg)

