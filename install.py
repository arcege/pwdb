#!/usr/bin/python
# install.py

import getopt
import os
import sys

install_dir = '~'
#install_dir = '/tmp/foo'

Bin_dirs = [
  'bin'
]
Bin_files = [
  ('cli.py', 'pwdb'),
  ('merge.py', 'pwdb-merge'),
]

Lib_dir = [
  os.path.join('lib', 'pwdb'),
  os.path.join('lib', 'encrypt'),
]
Lib_files = [
]

def mkdir(dir, perm=0755):
    if not os.path.exists(os.path.dirname(dir)):
        mkdir(os.path.dirname(dir), perm)
    if not os.path.exists(dir):
        os.mkdir(dir, perm)

def installfile(srcfilename, dstfilename, perm):
    if os.path.exists(dstfilename):
        os.chmod(dstfilename, 0700)
    srcfile = open(srcfilename, 'rb')
    dstfile = open(dstfilename, 'wb')
    block = srcfile.read(8192)
    while block:
        dstfile.write(block)
        block = srcfile.read(8192)
    dstfile.close()
    srcfile.close()
    os.chmod(dstfilename, perm)

if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'd:h', [
                'directory=',
                'help',
            ]
        )
    except getopt.error, e:
        raise SystemExit(e)
    for opt, val in opts:
        if opt == '--':
            break
        elif opt in ('-d', '--directory'):
            install_dir = val
        elif opt in ('-h', '--help'):
            print sys.argv[0]
            print '\t-h|--help'
            print '\t-d <instdir>|--directory=<instdir>'
    install_dir = os.path.expanduser(install_dir)
    mkdir(install_dir)

    for dir in Bin_dirs:
        bin_dir = os.path.join(install_dir, dir)
        mkdir(bin_dir)
        for sname, dname in Bin_files:
            sfname = os.path.join(dir, sname)
            dfname = os.path.join(bin_dir, dname)
            installfile(sfname, dfname, 0555)

    for dir in Lib_dir:
        tree = [(os.path.join(os.curdir, dir), os.path.join(install_dir, dir))]
        while tree:
            node = tree.pop()
            sdir, ddir = node
            if os.path.exists(sdir):
                mkdir(ddir)
                for name in os.listdir(sdir):
                    if name in ('.svn'):
                        continue
                    sfname = os.path.join(sdir, name)
                    dfname = os.path.join(ddir, name)
                    if os.path.islink(sfname):
                        data = os.readlink(sfname)
                        if os.path.exists(dfname):
                            os.remove(dfname)
                        os.symlink(data, dfname)
                    elif os.path.isdir(sfname):
                        mkdir(dfname)
                        tree.append((sfname, dfname))
                    elif os.path.isfile(sfname):
                        installfile(sfname, dfname, 0444)

