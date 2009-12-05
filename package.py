#!/usr/bin/python

import getopt
import os
import sys
import tarfile

PackageName = 'pwdb.tgz'

Dirs = ('bin', 'lib')
Files = ('install.py',)

def copyfile(src, dst):
    inf = open(src, 'rb')
    outf = open(dst, 'wb')
    block = inf.read(8192)
    while block:
        outf.write(block)
        block = inf.read(8192)
    outf.close()
    inf.close()
    st = os.stat(src)
    mode = os.path.stat.S_IMODE(st.st_mode)
    os.chmod(dst, mode)
    os.utime(dst, (st.st_atime, st.st_mtime))

def rmtree(dir):
    if os.path.islink(dir):
        raise OSError('cannot call on symlink')
    names = os.listdir(dir)
    for name in names:
        fullname = os.path.join(dir, name)
        try:
            mode = os.lstat(fullname).st_mode
        except os.error:
            mode = 0
        if os.path.stat.S_ISDIR(mode):
            rmtree(fullname)
        else:
            os.remove(fullname)
    os.rmdir(dir)

def mkdir(dir, mode=0777):
    if not dir:
        return
    if not os.path.exists(os.path.dirname(dir)):
        mkdir(os.path.dirname(dir), mode)
    if not os.path.exists(dir):
        os.mkdir(dir, mode)

if __name__ == '__main__':
    cleanup = False
    dstdir = os.path.join(os.curdir, 'dist')
    srcdir = os.curdir

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'cd:f:hs:', [
            'clean', 'dst=', 'file=', 'help', 'src=',
        ])
    except getopt.error, e:
        raise SystemExit(e)
    for opt, val in opts:
        if opt == '--':
            break
        elif opt in ('-c', '--clean'):
            cleanup = True
        elif opt in ('-f', '--file'):
            PackageName = os.path.expanduser(val)
        elif opt in ('-d', '--dst'):
            dstdir = os.path.expanduser(val)
        elif opt in ('-s', '--src'):
            srcdir = os.path.expanduser(val)
        elif opt in ('-h', '--help'):
            print sys.argv[0], '[options]'
            print '\t-h|--help\t\tthis information'
            print '\t-c|--clean\t\tremove distribution directory and tarfile'
            print '\t-f|--file\t\tfilename of tarfile'
            print '\t-s|--src\t\tdirectory of sources'
            print '\t-d|--dst\t\tdirectory of destination'
            raise SystemExit

    if cleanup:
        try:
            os.remove(PackageName)
        except OSError:
            pass
        if os.path.exists(dstdir):
            rmtree(dstdir)
        raise SystemExit

    if not os.path.exists(srcdir):
        raise SystemExit('%s source directory does not exist')
    if os.path.exists(dstdir):
        rmtree(dstdir)
    mkdir(dstdir)

    files = []
    for name in Files:
        sfname = os.path.join(srcdir, name)
        dfname = os.path.join(dstdir, name)
        if name == '.svn' or name.endswith('.pyc'):
            pass # ignore subversion control directory
        elif os.path.islink(sfname):
            data = os.readlink(sfname)
            os.symlink(data, dfname)
            files.append(name)
        elif os.path.isdir(sfname):
            raise ValueError('%s should not be a directory' % sfname)
        elif os.path.isfile(sfname):
            copyfile(sfname, dfname)
            files.append(name)
    dirs = list(Dirs)
    for dir in dirs:
        sdir = os.path.join(srcdir, dir)
        ddir = os.path.join(dstdir, dir)
        if os.path.isdir(sdir):
            mkdir(ddir)
            for name in os.listdir(sdir):
                sfname = os.path.join(sdir, name)
                dfname = os.path.join(ddir, name)
                if name == '.svn' or name.endswith('.pyc'):
                    pass # ignore subversion control directory
                elif os.path.islink(sfname):
                    data = os.readlink(sfname)
                    os.symlink(data, dfname)
                    files.append(os.path.join(dir, name))
                elif os.path.isdir(sfname):
                    dirs.append(os.path.join(dir, name))
                elif os.path.isfile(sfname):
                    copyfile(sfname, dfname)
                    files.append(os.path.join(dir, name))

    if os.path.exists(PackageName):
        os.remove(PackageName)
    outfile = tarfile.open(PackageName, 'w:gz')
    for file in files:
        outfile.add(os.path.join(dstdir, file), file)
    outfile.close()

