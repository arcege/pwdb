#!/usr/bin/python

import os
import sys
if os.path.exists(os.path.join(os.curdir, 'lib', 'pwdb')):
    libdir = os.path.join(os.curdir, 'lib')
else:
    libdir = os.path.expanduser(os.path.join('~', 'lib'))
sys.path.insert(0, libdir)
import pwdb.database

def show_diff(l, r):
    def dist(l, r):
        if l == r:
            print l
        else:
            print '%39.39s %39.39s' % (str(l)[:39], str(r)[:39])
    print '%39s %39s' % ('differences: left', 'right')
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
        rn = r.notes.split('\n')
        for i in xrange(min(len(ln), len(rn))):
            print '%39.39s %39.39s' % (ln[i][:39], rn[i][:39])
        if len(ln) > len(rn):
            for i in xrange(len(ln), len(rn)):
                print '%39.39s %39.39s' % (ln[i][:39], '')
        else:
            for i in xrange(len(rn), len(ln)):
                print '%39.39s %39.39s' % ('', rn[i][:39])
def show_entry(e, caption):
    print caption
    print '%39.39s' % e.uid[:39]
    print '%39.39s' % e.mtime
    print '%39.39s' % e.name[:39]
    print '%39.39s' % e.acct[:39]
    print '%39.39s' % e.pswd[:39]
    print '%39.39s' % e.url[:39]
    print '%39.39s' % e.label[:39]
    print '%39.39s' % e.notes[:39]

def merge(db, e1, e2):
    if e1.mtime < e2.mtime:
        e = Entry(db,
            e2.name, e2.label, e2.url, e2.acct, e2.pswd,
            e2.notes, e2.mtime, e2.uid
        )
    else:
        e = Entry(db,
            e1.name, e1.label, e1.url, e1.acct, e1.pswd,
            e1.notes, e1.mtime, e1.uid
        )
    return e

if __name__ == '__main__':
    perform = 'merge'
    if sys.argv[1] == 'diff':
        perform = 'diff'
        del sys.argv[1]
    try:
        leftname = sys.argv[1]
        rightname = sys.argv[2]
        if perform == 'merge':
            newname = sys.argv[3]
    except IndexError:
        raise SystemExit('expecting at least three arguments')
    dbleft  = pwdb.database.Database(leftname)
    dbright = pwdb.database.Database(rightname)
    if perform == 'merge':
        dbnew   = pwdb.database.Database(newname)

    entries = {}

    if perform == 'diff':
        left = list(dbleft)
        right = list(dbright)
        dbleft.close()
        dbright.close()
        for e in left:
            if e in right:
                p = right.index(e)
                show_diff(e, right[p])
                del right[p]
                left.remove(e)
            else:
                show_entry(e, caption='only in left')
        for e in right:
            if e in left:
                p = left.index(e)
                show_diff(left[p], e)
                del left[p]
                right.remove(e)
            else:
                show_entry(e, caption='only in right')

    if perform == 'merge':
        for db in (dbleft, dbright):
            for entry in db:
                if entries.has_key(entry.uid):
                    entries[entry.uid].append(entry)
                else:
                    entries[entry.uid] = [entry]

        newentries = []
        dbnew.open()
        for key in sorted(entries.keys()):
            e = entries[key]
            if len(e) == 1:
                newentries.append(e)
            elif len(e) > 2:
                print 'error: more than two entries with #%s' % key
            else:
                newentries.append(dbnew, merge(e[0], e[1]))
        if dbleft.uid > dbright.uid:
            dbnew.set_uid(dbleft.uid)
        else:
            dbnew.set_uid(dbright.uid)
        dbleft.close()
        dbright.close()

        for entry in newentries:
            dbnew.append(entry)
        dbnew.update()
        dbnew.close()

