#!/usr/bin/python

import os
import sys
import time
if os.path.exists(os.path.join(os.curdir, 'lib', 'pwdb')):
    libdir = os.path.join(os.curdir, 'lib')
else:
    libdir = os.path.expanduser(os.path.join('~', 'lib'))
sys.path.insert(0, libdir)
import pwdb.database

def parse_data(field):
    p = field.find(': ')
    if p != -1:
        return field[p+2:]
    return field

if __name__ == '__main__':
    try:
        impfname = sys.argv[1]
        dbfname = sys.argv[2]
    except IndexError:
        raise SystemExit('requires two arguments')
    try:
        uid = sys.argv[3]
    except IndexError:
        uid = 1000000
    mtime = os.path.getmtime(impfname)
    when = pwdb.database.Date(
        time.strftime(pwdb.database.Date.fmtpatt, time.gmtime(mtime))
    )

    infile = open(impfname)
    data = infile.read()
    infile.close()

    data = data.replace('\r\n', '\r')
    rec_delim = '\r' + ('-' * 62) + '\r'
    records = data.split(rec_delim)
    print '#%d records' % len(records)
    if records[0].startswith('Export Date: '):
        del records[0]
    db = pwdb.database.Database(dbfname)
    db.open()
    db.set_uid(uid)
    for record in records:
        fields = record.split('\r')
        for (i, v) in enumerate(fields):
            print i, parse_data(v)
        e = db.new()
        e.name = parse_data(fields[0])
        e.label = parse_data(fields[1])
        e.acct = parse_data(fields[2])
        e.pswd = parse_data(fields[3])
        e.notes = fields[5].rstrip()
        e.mtime = when
        db.set(e)
    db.update(force=True)
    db.close()

