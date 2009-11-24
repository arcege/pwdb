#!/usr/bin/python

import os

__all__ = [
  'FileLock',
]

class FileLock:
    class Locked(Exception):
        pass
    def __init__(self, filename):
        self.name = filename
        self.pid = os.getpid()
        self.tmpname = '%s.%d.tmp' % (self.name, self.pid)
        self.lckname = '%s.lck' % self.name
        if os.path.exists(self.lckname):
            self.state = 'locked'
        else:
            self.state = 'unlocked'
    def __nonzero__(self):
        return os.path.exists(self.lckname)
    def lock(self):
        if self:
            raise self.Locked(self.name)
        open(self.tmpname, 'w').write('%s\n' % self.pid)
        try:
            try:
                os.link(self.tmpname, self.lckname)
            except OSError:
                raise self.Locked(self.name)
        finally:
            os.remove(self.tmpname)
        return True
    def unlock(self):
        try:
            os.remove(self.lckname)
        except OSError:
            pass

class TestHarness:
    def __init__(self):
        self.rootdir = 'tmp%d.d' % os.getpid()
        os.mkdir(self.rootdir)
        self.os_remove = os.remove
        self.os_listdir = os.listdir
        self.os_rmdir = os.rmdir
    def __del__(self):
        for fname in self.os_listdir(self.rootdir):
            self.os_remove(os.path.join(self.rootdir, fname))
        self.os_rmdir(self.rootdir)
    def run(self):
        failures = []
        filename = os.path.join(self.rootdir, 'test01')
        lock01 = FileLock(filename)
        try:
            me = lock01.lock()
        except FileLock.Locked:
            failures.append('lock01: Could not lock')
            me = True
        if not os.path.exists(lock01.lckname):
            failures.append('lock01: lock file not created')
        if not me:
            failures.append('lock01: Return value incorrect')
        if not lock01:
            failures.append('lock01: boolean test failed')
        if os.path.exists(lock01.tmpname):
            failures.append('lock01: Tempfile still exists')
        lock02 = FileLock(filename)
        try:
            me = lock02.lock()
        except FileLock.Locked:
            pass
        else:
            failures.append('lock02: Could still lock already locked file')
        if not lock02:
            failures.append('lock02: bookean test failed')
        if os.path.exists(lock02.tmpname):
            failures.append('lock02: tempfile still exists')
        if failures:
            print 'failure'
            print '\n'.join(failures)
        else:
            print 'success'

if __name__ == '__main__':
    TestHarness().run()

