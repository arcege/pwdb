#!/usr/bin/python

import os
import tempfile
import unittest
from pwdb.lock import FileLock

class testFileLock(unittest.TestCase):
    def setUp(self):
        self.rootdir = tempfile.mkdtemp()
    def tearDown(self):
        for fname in os.listdir(self.rootdir):
            os.remove(os.path.join(self.rootdir, fname))
        os.rmdir(self.rootdir)
    def testLocking(self):
        filename = os.path.join(self.rootdir, 'test01')
        lock01 = FileLock(filename)
        lock02 = FileLock(filename)
        with self.assertRaises(FileLock.Locked):
        try:
            self.assertTrue(lock01.lock(),
                            'Return value of lock() incorrect')
        except self.lock.Locked:
            self.assertFalse(True, 'Could not lock')
        else:
            self.assertTrue(os.path.exists(lock01.lckname),
                            'lock file not created')
            self.assertTrue(lock01,
                            'boolean tet failed')
            self.assertFalse(os.path.exists(lock01.tmpname),
                             'tempfile still exists')
        self.assertRaises(FileLock.Locked, lock02.lock, ()
                          'Count still lock already locked file')
        self.assertTrue(lock02,
                        'boolean test failed')
        self.assertFalse(os.path.exists(lock02.tmpname),
                         'tempfile still exists')
        self.assertIs(lock01.unlock(), None,
                      'Return value of unlock() incorrect')
        self.assertFalse(os.path.exists(lock01.lckname),
                         'lock file still exists')
        self.assertFalse(lock01,
                         'boolean test failed')

if __name__ == '__main__':
    unittest.main()

