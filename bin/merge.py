#!/usr/bin/python

import os
import sys
if os.path.exists(os.path.join(os.curdir, 'lib', 'pwdb')):
    libdir = os.path.join(os.curdir, 'lib')
else:
    libdir = os.path.expanduser(os.path.join('~', 'lib'))
sys.path.insert(0, libdir)
import pwdb.database

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
    print fmt % e.uid[:39]
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

if __name__ == '__main__':
    perform = 'merge'
    if sys.argv[1] == 'help':
        print os.path.basename(sys.argv[0]), "left right output"
        print os.path.basename(sys.argv[0]), "diff left right"
        print os.path.basename(sys.argv[0]), "dump dbfile"
        raise SystemExit
    try:
        if sys.argv[1] == 'diff':
            perform = 'diff'
            del sys.argv[1]
        elif sys.argv[1] == 'dump':
            perform = 'dump'
            del sys.argv[1]
    except IndexError:
        pass
    try:
        leftname = sys.argv[1]
        if perform != 'dump':
            rightname = sys.argv[2]
            if perform == 'merge':
                newname = sys.argv[3]
    except IndexError:
        raise SystemExit('expecting at least three arguments')
    fleft = open(leftname, 'rb').read(6)
    if perform != 'dump':
        fright = open(rightname, 'rb').read(6)

    leftkls  = pwdb.database.Database.check_file_type(leftname)
    if perform != 'dump':
        rightkls = pwdb.database.Database.check_file_type(rightname)
    leftkey = rightkey = None
    if leftkls.need_key:
        leftkey  = raw_input('Key for %s: ' % leftname)
    dbleft = leftkls(leftname, leftkey)
    if perform != 'dump':
        if rightkls.need_key:
            rightkey = raw_input('Key for %s: ' % rightname)
        dbright = rightkls(rightname, rightkey)

    left = list(dbleft)
    if perform != 'dump':
        right = list(dbright)
    else:
        right = list()
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
                # same names, different UIDs = possible merge; check data
                tomerge.append( (False, lval, rightnames[lkey]) )
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

    if perform == 'dump':
        for e in dbleft:
            show_entry(e, caption='-' * 40)
    elif perform == 'diff':
        for same, lval, rval in tomerge:
            if same:
                pass # ignore entries that are the same
            elif lval is None:
                show_entry(rval, caption='only in right')
            elif rval is None:
                show_entry(lval, caption='only in left')
            else:
                show_diff(lval, rval)

    elif perform == 'merge':
        newkey = raw_input('New key: ')
        dbnew = pwdb.database.EncryptDatabase(newname, newkey)
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
        dbleft.close()
        dbright.close()

        dbnew.extend(newentries)
        dbnew.update()
        dbnew.close()

