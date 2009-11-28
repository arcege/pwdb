#!/usr/bin/python

import lock
import os
import gzip

__all__ = [
    'Database',
]

class UIDGenerator:
    def __init__(self, seed):
        self.seed = long(seed or 0)
    def next(self):
        self.seed = self.seed + 1
        return str(self.seed)
    def __str__(self):
        return str(self.seed)
    def __trunc__(self):
        return self.seed
    def __long__(self):
        return self.seed
    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.seed)
    def __cmp__(self, other):
        return -cmp(other, self.seed)

class Entry:
    fieldnames = {
        'name': 'Name',
        'acct': 'Account',
        'pswd': 'Password',
        'label': 'Labels',
        'notes': 'Notes',
        'url': 'URL',
    }
    def __init__(self, db, name, label, url, acct, pswd, notes, mtime, uid=None):
        if uid is None:
            self.uid = db.gen_uid()
        else:
            self.uid = uid
        self.name = name
        self.label = label
        self.url = url
        self.acct = acct
        self.pswd = pswd
        self.notes = notes
        self.mtime = mtime
    def __hash__(self):
        return hash(self.uid)
    def __contains__(self, key):
        return (
            self.name == key or
            self.acct == key or
            self.pswd == key or
            self.label.find(key) != -1 or
            self.notes.find(key) != -1 or
            self.url.find(key) != -1
        )
    def find(self, key):
        return (
            self.name.find(key) != -1 or
            self.acct.find(key) != -1 or
            self.pswd.find(key) != -1 or
            self.label.find(key) != -1 or
            self.notes.find(key) != -1 or
            self.url.find(key) != -1
        )
    def __cmp__(self, other):
        if isinstance(other, Entry):
            return cmp(self.uid, other.uid)
        else:
            return -cmp(other, self.name)
    def __str__(self):
        return str(self.name)
    def __repr__(self):
        return '<%s "%s">' % (self.__class__.__name__, self.name)

class Date:
    fmtpatt = '%Y%d%m.%H%M%S'
    def __init__(self, datestr):
        if datestr is None:
            self.when = self.now()
        else:
            self.when = self.parse(datestr)
    def now():
        import time
        return time.gmtime()
    now = staticmethod(now)
    def parse(cls, datestr):
        import time
        return time.strptime(datestr, cls.fmtpatt)
    def __trunc__(self):
        import time
        return long(time.mktime(self.when))
    def __long__(self):
        import time
        return long(time.mktime(self.when))
    def __str__(self):
        import time
        return time.strftime(self.fmtpatt, self.when)
    def __repr__(self):
        import time
        return '<%s "%s">'% (self.__class__.__name__, time.asctime(self.when))
    def __cmp__(self, other):
        import time
        return -cmp(other, long(self))

class Database:
    Locked = lock.FileLock.Locked
    rec_delim = ('--' * 38)
    header = 'PWDB\n'
    def __init__(self, filename):
        self.filename = filename
        self.flock = lock.FileLock(filename)
        self.file = None
        self.uid = None
        self.dirty = False
        self.mtime = 0
        self.cache = {}
    def __del__(self):
        if self.dirty:
            self.update()
        self.close()
    def close(self):
        if self.file:
            self._close()
            self.flock.unlock()
    def open(self):
        if not self.file:
            self.flock.lock()
            try:
                self._open()
            except IOError, e:
                self.flock.unlock()
                raise
    def _open(self):
        if not os.path.exists(self.filename):
            open(self.filename, 'w') # 'touch'
        self.file = gzip.GzipFile(self.filename, "r")
        if self.uid is None:
            # load the uid from the file
            try:
                self.reset_uid()
            except ValueError:
                self.close()
                raise
        self.dirty = False
    def _reopen(self):
        self._close()
        self._open()
    def _close(self):
        self.file.close()
        self.file = None
        self.dirty = False
    def refresh(self):
        self.open()
        self.file.seek(0)
        self.file.readline()
        mtime = os.path.getmtime(self.filename)
        if self.need_refresh(mtime):
            counts = {'entries': 0, 'lines': 1}
            try:
                entry = self._read_next(counts)
                while entry:
                    self.cache[entry.uid] = entry
                    counts['entries'] += 1
                    entry = self._read_next(counts)
            except AttributeError, e:
                raise ValueError(
                    'invalid database entry#%d, line %d' %
                        (counts['entries'], counts['lines'])
                )
            else:
                self.mtime = mtime
    def need_refresh(self, mtime=0):
        if not mtime:
            mtime = os.path.getmtime(self.filename)
        return (mtime > self.mtime)
    def clear(self):
        self.mtime = 0
        self.dirty = False
        self.refresh()

    def keys(self):
        if self.need_refresh():
            self.refresh()
        return sorted(self.cache.keys())
    def values(self):
        if self.need_refresh():
            self.refresh()
        return sorted(self.cache.values())
    def __len__(self):
        if self.need_refresh():
            self.refresh()
        return len(self.cache)
    def __getitem__(self, uid):
        if self.need_refresh():
            self.refresh()
        if isinstance(uid, Entry):
            uid = uid.uid
        return self.cache[uid]
    def __setitem__(self, uid, value):
        if self.need_refresh():
            self.refresh()
        if isinstance(uid, Entry):
            uid = uid.uid
        self.cache[uid] = value
        self.dirty = True
    def __delitem__(self, uid):
        if self.need_refresh():
            self.refresh()
        if isinstance(uid, Entry):
            uid = uid.uid
        del self.cache[uid]
        self.dirty = True
    def find(self, name):
        if self.need_refresh():
            self.refresh()
        if self.cache.has_key(name):
            return self.cache[name]
        values = self.values()
        try:
            p = values.index(str(name))
        except ValueError:
            return None
        else:
            return values[p]
    def set(self, value):
        if self.need_refresh():
            self.refresh()
        self[value.uid] = value
    def append(self, item):
        assert isinstance(item, Entry)
        if self.need_refresh():
            self.refresh()
        self.cache[item.uid] = item
        self.dirty = True
    def extend(self, items):
        for item in items:
            assert isinstance(item, Entry)
        if self.need_refresh():
            self.refresh()
        for item in items:
            self.cache[item.uid] = item
        self.dirty = True

    def new(self):
        e = Entry(self, '', '', '', '', '', '', Date(None), None)
        return e

    def reset_uid(self):
        if not self.file:
            raise RuntimeError('database not opened')
        self.file.seek(0)
        self.uid = UIDGenerator(self.file.readline().strip())
    def set_uid(self, value):
        if not self.file:
            raise RuntimeError('database not opened')
        self.uid = UIDGenerator(value)
    def gen_uid(self):
        self.open()
        uid = self.uid.next()
        self.dirty = True
        return uid

    def __contains__(self, key):
        for entry in self:
            if key in entry:
                return True
        else:
            return False
    def __iter__(self):
        for entry in self.values():
            yield entry

    def _read_next(self, counts):
        line = self.file.readline()
        if not line:
            return None
        e = {
            'name': '',
            'label': '',
            'url': '',
            'acct': '',
            'pswd': '',
            'notes': '',
            'mtime': None,
            'uid': '',
        }
        try:
            while line.rstrip() != self.rec_delim:
                fname, fval = line.split(': ', 1)
                e[fname] = fval.strip()
                line = self.file.readline()
                counts['lines'] += 1
        except ValueError:
            raise AttributeError(count, 'invalid data entry')
        e = Entry(self,
            e['name'], e['label'], e['url'], e['acct'], e['pswd'],
            e['notes'].replace('###', '\n'),
            Date(e['mtime']),
            e['uid']
        )
        return e

    def update(self, force=False):
        if not self.file:
            raise RuntimeError('database not opened')
        if not self.dirty and not force:
            return
        tmpfname = '%s.tmp.%d' % (self.filename, os.getpid())
        file = gzip.GzipFile('w', fileobj=open(tmpfname, 'w'))
        file.write('%s\n' % self.uid)
        for entry in self:
            self.write_entry(file, entry)
        file.close()
        bakname = '%s.bak' % self.filename
        try:
            os.remove(bakname)
        except OSError:
            pass
        os.rename(self.filename, bakname)
        os.rename(tmpfname, self.filename)
        self._reopen()

    def write_entry(cls, file, entry):
        file.write('name: %s\n' % entry.name)
        file.write('label: %s\n' % entry.label)
        file.write('url: %s\n' % entry.url)
        file.write('acct: %s\n' % entry.acct)
        file.write('pswd: %s\n' % entry.pswd)
        file.write('notes: %s\n' % entry.notes.replace('\n', '###'))
        file.write('mtime: %s\n' % entry.mtime)
        file.write('uid: %s\n' % entry.uid)
        file.write('%s\n' % cls.rec_delim)
    write_entry = classmethod(write_entry)

