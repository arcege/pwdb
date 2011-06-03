#!/usr/bin/python
# Copyright @ 2010 Michael P. Reilly. All rights reserved.
# pyerector.py
#
# from pyerector import *
# Compile.dependencies = ('PythonPrecompile',)
# class PreCompile_utd(Uptodate):
#     sources = ('*.py',)
#     destinations = ('build/*.pyc',)
# class PyCopy_t(Copy):
#     sources = ('*.py',)
#     destination = 'build'
# class PyCopy(Target):
#     files = ('*.py',)
#     tasks = ("PyCopy_t",)
# class PythonPreCompile(Target):
#     dependencies = ("PyCopy",)
#     uptodates = ("PreCompile_utd",)
#     files = ('build/*.py',)
#     def run(self):
#         from py_compile import compile
#         for file in self.get_files():
#             compile(file)
#
# $Id$

# Future Py3000 work prevents the use of string formatting using '%'
# trying to use both string formatting and ''.format is UGLY!!!!
# A LOT of the code below will be using the less efficient string
# concatentation which is supposed across both sets of releases.
try:
    ''.format
except AttributeError:
    hasformat = False
else:
    hasformat = True

__all__ = [
  'Target', 'Uptodate', 'pymain',
  # standard targets
  'All', 'Default', 'Help', 'Clean', 'Init', 'InitDirs',
  'Build', 'Compile', 'Dist',
  # tasks
  'Task', 'Spawn', 'Remove', 'Copy', 'CopyTree', 'Mkdir', 'Chmod', 'Java',
  'Tar', 'Untar', 'Zip', 'Unzip',
]

Config = {
    'initialized': False,
    'basedir': None,
}

class Verbose(object):
    import os, sys
    stream = sys.stdout
    eoln = os.linesep
    del os, sys
    def __init__(self, state=False):
        self.state = state
    def on(self):
        self.state = True
    def off(self):
        self.state = False
    def _write(self, msg):
        if self.state:
            self.stream.write(msg)
            self.stream.write(self.eoln)
            self.stream.flush()
        #print('state =', self.state)
    def __call__(self, *args):
        self._write(' '.join([str(s) for s in args]))
verbose = Verbose()

# the main program, to be called by pymake
def pymain(*args):
    global verbose
    from sys import argv, exc_info
    # need to "import __main__" and not "from __main__ import Default"
    import getopt
    basedir = None
    targets = []
    try:
        opts, args = getopt.getopt(args or argv[1:], 'd:v', [
                'directory=', 'verbose',
            ]
        )
    except getopt.error:
        e = exc_info()[1]
        raise SystemExit(e)
    else:
        for opt, val in opts:
            if opt == '--':
                break
            elif opt in ('-d', '--directory'):
                basedir = val
            elif opt in ('-v', '--verbose'):
                verbose.on()
            else:
                raise SystemExit('invalid option: ' + str(opt))
    # map arguments into classes above: e.g. 'all' into All
    if len(args) == 0:
        try:
            import __main__
            targets.append(__main__.Default)
        except AttributeError:
            raise SystemExit('Must supply at least a Default target')
    else:
        all_targets = Target.get_targets()
        for name in args:
            try:
                obj = all_targets[name.capitalize()]
            except KeyError:
                raise SystemExit('Error: unknown target: ' + str(name))
            else:
                if not issubclass(obj, Target):
                    raise SystemExit('Error: unknown target: ' + str(name))
                targets.append(obj)
    # validate the dependency tree, make sure that all are subclasses of
    # Target, validate all Uptodate values and all Task values
    for target in targets:
        try:
            target.validate_tree()
        except ValueError:
            e = exc_info()[1]
            raise SystemExit('Error: ' + str(e))
    # run all the targets in the tree of each argument
    for target in targets:
        try:
            target(basedir)()
        except target.Error:
            e = exc_info()[1]
            raise SystemExit(e)
        except KeyboardInterrupt:
            e = exc_info()[1]
            raise SystemExit(e)

# the classes

# the base class to set up the others
class _Initer:
    global Config
    config = Config
    from os import curdir
    def __init__(self, basedir=None, curdir=curdir):
        from os.path import normpath, realpath
        if basedir is None:
            basedir = curdir
        if not self.config['initialized']:
            self.config['basedir'] = normpath(realpath(basedir))
            self.config['initialized'] = True
    del curdir
    def get_files(self, files=None, noglob=False, subdir=None):
        from glob import glob
        from os.path import join
        from os import curdir
        if noglob:
            glob = lambda x: [x]
        if subdir is None:
            subdir = curdir
        if not files:
            files = self.files
        filelist = []
        for entry in files:
            s = glob(join(self.config['basedir'], subdir, entry))
            filelist.extend(s)
        return filelist
    def join(self, *path):
        from os.path import join
        return join(self.config['basedir'], *path)

class Uptodate(_Initer):
    sources = ()
    destinations = ()
    def __call__(self, *args):
        from os.path import getmtime
        try:
            from sys import maxsize as maxint
        except ImportError:
            from sys import maxint
        self.srcs = []
        self.dsts = []
        if not self.sources or not self.destinations:
            return False
        self.srcs = self.get_files(self.sources)
        self.dsts = self.get_files(self.destinations)
        # if no actual destination files then nothing is uptodate
        if not self.dsts and self.destinations:
            return False
        # compare the latest mtime of the sources with the earliest
        # mtime of the destinations
        latest_src = 0
        earliest_dst = maxint
        for src in self.srcs:
            latest_src = max(latest_src, getmtime(src))
        for dst in self.dsts:
            earliest_dst = min(earliest_dst, getmtime(dst))
        return earliest_dst >= latest_src

class Target(_Initer):
    class Error(Exception):
        def __str__(self):
            return str(self[0]) + ': ' + str(self[1])
        def __format__(self, format_spec):
            if isinstance(spec, unicode):
                return unicode(str(self))
            else:
                return str(self)
    dependencies = ()
    uptodates = ()
    tasks = ()
    _been_called = False
    def get_been_called(self):
        return self.__class__._been_called
    def set_been_called(self, value):
        self.__class__._been_called = value
    been_called = property(get_been_called, set_been_called)
    def __str__(self):
        return self.__class__.__name__
    #def __repr__(self):
    #    return '<%s>' % self
    def validate_tree(klass):
        name = klass.__name__
        targets = klass.get_targets()
        uptodates = klass.get_uptodates()
        tasks = klass.get_tasks()
        try:
            deps = klass.dependencies
        except AttributeError:
            pass
        else:
            for dep in deps:
                if dep not in targets:
                    raise ValueError(
                        str(name) + ': invalid dependency: ' + str(dep)
                    )
                targets[dep].validate_tree()
        try:
            utds = klass.uptodates
        except AttributeError:
            pass
        else:
            for utd in utds:
                if utd not in uptodates:
                    raise ValueError(
                        str(name) + ': invalid uptodate: ' + str(utd)
                    )
        try:
            tsks = klass.tasks
        except AttributeError:
            pass
        else:
            for tsk in tsks:
                if tsk not in tasks:
                    raise ValueError(
                        str(name) + ': invalid task: ' + str(tsk)
                    )
    validate_tree = classmethod(validate_tree)
    def call_uptodate(self, klassname):
        uptodates = self.get_uptodates()
        try:
            klass = uptodates[klassname]
        except KeyError:
            raise self.Error(str(self), 'no such uptodate: ' + str(klassname))
        return klass()()
    def call_dependency(self, klassname):
        targets = self.get_targets()
        try:
            klass = targets[klassname]
        except KeyError:
            raise self.Error(str(self), 'no such dependency: ' + str(klassname))
        klass()()
    def call_task(self, klassname, args):
        tasks = self.get_tasks()
        try:
            klass = tasks[klassname]
        except KeyError:
            raise self.Error(str(self), 'no such task: ' + str(klassname))
        return klass()(*args)
    def __call__(self, *args):
        from sys import exc_info
        if self.been_called:
            return
        if self.uptodates:
            for utd in self.uptodates:
                if not self.call_uptodate(utd):
                    break
            else:
                self.verbose('uptodate.')
                return
        for dep in self.dependencies:
            self.call_dependency(dep)
        for task in self.tasks:
            try:
                self.call_task(task, args) # usually args would be (), but...
            except self.Error:
                e = exc_info()[1]
                raise self.Error(str(self) + ':' + str(e[0]), e[1])
        try:
            self.run()
        except (TypeError, RuntimeError, AttributeError):
            raise
        except Task.Error:
            e = exc_info()[1]
            raise self.Error(str(self) + ':' + str(e[0]), e[1])
        except self.Error:
            raise
        except Exception:
            e = exc_info()[1]
            raise self.Error(str(self), e)
        else:
            self.verbose('done.')
            self.been_called = True
    def run(self):
        pass
    def verbose(self, *args):
        from sys import stdout
        stdout.write(str(self))
        stdout.write(': ')
        stdout.write(' '.join([str(s) for s in args]))
        stdout.write('\n')
        stdout.flush()
    def get_tasks():
        import __main__
        if not hasattr(__main__, '_tasks_cache'):
            tasks = {}
            for name, obj in list(vars(__main__).items()):
                if not name.startswith('_') \
                   and obj is not Task \
                   and isinstance(obj, type(Task)) \
                   and issubclass(obj, Task):
                    tasks[name] = obj
            setattr(__main__, '_tasks_cache', tasks)
        return getattr(__main__, '_tasks_cache')
    get_tasks = staticmethod(get_tasks)
    def get_targets():
        import __main__
        if not hasattr(__main__, '_targets_cache'):
            targets = {}
            for name, obj in list(vars(__main__).items()):
                if not name.startswith('_') \
                   and obj is not Target \
                   and isinstance(obj, type(Target)) \
                   and issubclass(obj, Target):
                    targets[name] = obj
            setattr(__main__, '_targets_cache', targets)
        return getattr(__main__, '_targets_cache')
    get_targets = staticmethod(get_targets)
    def get_uptodates():
        import __main__
        if not hasattr(__main__, '_uptodates_cache'):
            uptodates = {}
            for name, obj in list(vars(__main__).items()):
                if not name.startswith('_') \
                   and obj is not Uptodate \
                   and isinstance(obj, type(Uptodate)) \
                   and issubclass(obj, Uptodate):
                    uptodates[name] = obj
            setattr(__main__, '_uptodates_cache', uptodates)
        return getattr(__main__, '_uptodates_cache')
    get_uptodates = staticmethod(get_uptodates)

# Tasks
class Task(_Initer):
    Error = Target.Error
    args = []
    def __str__(self):
        return self.__class__.__name__
    def __call__(self, *args, **kwargs):
        self.handle_args(args, kwargs)
        try:
            rc = self.run()
        except (TypeError, RuntimeError):
            raise
        except Exception:
            raise #raise self.Error(str(self), e)
        if rc:
            raise self.Error(str(self), 'return error = ' + str(rc))
    def run(self):
        pass
    def handle_args(self, args, kwargs):
        self.args = list(args)
        self.kwargs = dict(kwargs)

class Spawn(Task):
    cmd = ''
    infile = None
    outfile = None
    errfile = None
    def run(self):
        if self.args:
            cmd = self.args[0]
        else:
            cmd = self.cmd
        if 'infile' in self.kwargs:
            infile = self.kwargs['infile']
        else:
            infile = self.infile
        if 'outfile' in self.kwargs:
            outfile = self.kwargs['outfile']
        elif len(self.args) > 1:
            outfile = self.args[1]
        else:
            outfile = self.outfile
        if 'errfile' in self.kwargs:
            errfile = self.kwargs['errfile']
        elif len(self.args) > 2:
            errfile = self.args[2]
        else:
            errfile = self.errfile
        from os import WIFSIGNALED, WTERMSIG, WEXITSTATUS
        try:
            from subprocess import call
            ifl = of = ef = None
            if infile:
                ifl = open(infile, 'r')
            if outfile:
                of = open(outfile, 'w')
            if errfile == outfile:
                ef = of
            elif errfile:
                ef = open(errfile, 'w')
            verbose('spawn("' + str(cmd) + '")')
            rc = call(cmd, shell=True, stdin=ifl, stdout=of, stderr=ef, bufsize=0)
            if rc < 0:
                raise self.Error(str(self), 'signal ' + str(abs(rc)) + 'raised')
            elif rc > 0:
                raise self.Error(str(self), 'returned error + ' + str(rc))
            pass
        except ImportError:
            from popen2 import Popen3
            pcmd = cmd
            if outfile:
                pcmd += '>"' + str(outfile) + '"'
            if errfile == outfile:
                pcmd += '2>&1'
            elif errfile:
                pcmd += '2>"' + str(errfile) + '"'
            verbose('spawn("' + str(pcmd) + '")')
            rc = Popen3(pcmd, capturestderr=False, bufsize=0).wait()
            if WIFSIGNALED(rc):
                raise self.Error(str(self),
                                 'signal ' + str(WTERMSIG(rc)) + 'raised')
            elif WEXITSTATUS(rc):
                raise self.Error(str(self), 'returned error = ' + str(rc))
            pass
class Remove(Task):
    files = ()
    noglob = False
    def run(self):
        from os import remove
        from os.path import isdir, isfile, islink
        from shutil import rmtree
        for fname in self.get_files(self.args or None, self.noglob):
            if isfile(fname) or islink(fname):
                verbose('remove(' + str(fname) + ')')
                remove(fname)
            elif isdir(fname):
                verbose('rmtree(' + str(fname) + ')')
                rmtree(fname)
class Copy(Task):
    files = ()
    dest = None
    noglob = False
    def run(self):
        from shutil import copy2
        if 'dest' in self.kwargs:
            dst = self.join(self.kwargs['dest'])
        elif not self.dest:
            raise RuntimeError('configuration error: Copy missing destination')
        else:
            dst = self.join(self.dest)
        if self.args:
            srcs = self.get_files(self.args[:-1])
        else:
            srcs = self.get_files(self.files)
        if ('noglob' in self.kwargs and self.kwargs['noglob']) or \
           self.noglob:
            glob = lambda x: [x]
        for fname in srcs:
            verbose('copy2(' + str(fname) + ', ' + str(dst) + ')')
            copy2(fname, dst)
class CopyTree(Task):
    srcdir = None
    dstdir = None
    excludes = ('.svn',)
    def run(self):
        from fnmatch import fnmatch
        from os.path import exists, join, isdir, normpath
        import os
        if self.args:
            srcdir, dstdir = self.args
        else:
            srcdir, dstdir = self.srcdir, self.dstdir
        if not srcdir or not exists(self.join(srcdir)):
            raise os.error(2, "No such file or directory: " + str(srcdir))
        elif not isdir(self.join(srcdir)):
            raise os.error(20, "Not a directory: " + str(srcdir))
        copy_t = Copy()
        mkdir_t = Mkdir()
        copy_t.noglob = True
        dirs = [os.curdir]
        while dirs:
            dir = dirs[0]
            del dirs[0]
            if self.check_exclusion(dir):
                mkdir_t(normpath(self.join(dstdir, dir)))
                for fname in os.listdir(self.join(srcdir, dir)):
                    if self.check_exclusion(fname):
                        spath = self.join(srcdir, dir, fname)
                        dpath = self.join(dstdir, dir, fname)
                        if isdir(spath):
                            dirs.append(join(dir, fname))
                        else:
                            copy_t(spath, dpath)
    def check_exclusion(self, filename):
        from fnmatch import fnmatch
        for excl in self.excludes:
            if fnmatch(filename, excl):
                return False
        else:
            return True
class Mkdir(Task):
    files = ()
    def run(self):
        for arg in (self.args or self.files):
            self.mkdir(self.join(arg))
    def mkdir(klass, path):
        from os import mkdir, remove
        from os.path import dirname, isdir, isfile, islink
        if islink(path) or isfile(path):
            verbose('remove(' + str(path) + ')')
            remove(path)
            klass.mkdir(path)
        elif not isdir(path):
            klass.mkdir(dirname(path))
            verbose('mkdir(' + str(path) + ')')
            mkdir(path)
    mkdir = classmethod(mkdir)
class Chmod(Task):
    files = ()
    mode = int('666', 8) # gets around Python 2.x vs 3.x octal issue
    def run(self):
        from os import chmod
        if 'mode' in self.kwargs:
            mode = self.kwargs['mode']
        else:
            mode = self.mode
        if self.args:
            files = self.args[:-1]
        else:
            files = self.files
        for fname in self.get_files(files):
            verbose('chmod(' + str(fname) + ', ' + oct(mode) + ')')
            chmod(fname, mode)
class Tar(Task):
    name = None
    root = None
    files = ()
    exclude = None
    def run(self):
        from tarfile import open
        from os.path import join
        if 'name' in self.kwargs:
            name = self.kwargs['name']
        else:
            name = self.name
        if 'root' in self.kwargs:
            root = self.kwargs['root']
        else:
            root = self.root
        if self.args:
            files = tuple(self.args)
        else:
            files = self.files
        if 'exclude' in self.kwargs:
            excludes = self.kwargs['exclude']
        else:
            excludes = self.exclude
        if excludes:
            exctest = lambda t, e=excludes: [v for v in e if t.endswith(v)]
            filter = lambda t, e=exctest: not e(t.name) and t or None
            exclusion = lambda t, e=exctest: e(t)
        else:
            exctest = None
            filter = None
            exclusion = None
        import os
        if not root:
            root = os.curdir
        toadd = []
        # do not use Task.get_files()
        from glob import glob
        queue = list(files)
        while queue:
            entry = queue[0]
            del queue[0]
            for fn in glob(self.join(root, entry)):
                if exctest and exctest(fn):  # if pass, then ignore
                    pass
                elif os.path.islink(fn) or os.path.isfile(fn):
                    toadd.append(fn)
                elif os.path.isdir(fn):
                    fnames = [os.path.join(fn, f) for f in os.listdir(fn)]
                    queue.extend(fnames)
        file = open(self.join(name), 'w:gz')
        for fname in toadd:
            fn = fname.replace(
                self.config['basedir'] + os.sep, ''
            ).replace(
                root + os.sep, ''
            )
            verbose('tar.add(' +
                    str(fname) + ', ' +
                    str(fn) + ')'
            )
            file.add(fname, fn)
        file.close()
class Untar(Task):
    name = None
    root = None
    files = ()
    def run(self):
        from tarfile import open
        from os.path import join
        from os import pardir, sep
        if self.args:
            name, root = self.args[0], self.args[1]
            files = tuple(self.args[2:])
        else:
            name, root, files = self.name, self.root, self.files
        file = open(tarname, 'r:gz')
        fileset = []
        for member in file.getmembers():
            if member.name.startswith(sep) or member.name.startswith(pardir):
                pass
            elif not files or member.name in files:
                fileset.append(member)
        for fileinfo in fileset:
            verbose('tar.extract(' + str(fileinfo.name) + ')')
            file.extract(fileinfo, path=(root or ""))
        file.close()
        return True
class Zip(Task):
    def zip(self, zipname, root, *files):
        from zipfile import ZipFile
        from os.path import join
        file = ZipFile(zipname, 'w')
        for filename in files:
            verbose('zip.add(' + str(join(root, filename)) + ')')
            file.write(join(root, filename), filename)
        file.close()
class Unzip(Task):
    def unzip(self, zipname, root, *files):
        from zipfile import ZipFile
        from os.path import dirname, join
        from os import pardir, sep
        file = open(zipname, 'r')
        fileset = []
        for member in file.namelist():
            if member.startswith(sep) or member.startswith(pardir):
                pass
            elif not files or member in files:
                fileset.append(member)
        for member in fileset:
            dname = join(root, member)
            self.mkdir(dirname(dname))
            dfile = open(dname, 'wb')
            dfile.write(file.read(member))
        file.close()
class Java(Task):
    from os import environ
    java_home = 'JAVA_HOME' in environ and environ['JAVA_HOME'] or ''
    properties = []
    del environ
    jar = None
    def __init__(self):
        Task.__init__(self)
        from os.path import expanduser, exists, join
        import os
        if exists(self.java_home):
            self.java_prog = join(self.java_home, 'bin', 'java')
        elif exists(expanduser(join('~', 'java'))):
            self.java_prog = expanduser(
                join('~', 'java', 'bin', 'java')
            )
        else:
            raise RuntimeError("no java program to execute")
        if not os.access(self.java_prog, os.X_OK):
            raise RuntimeError("no java program to execute")
    def addprop(self, var, val):
        self.properties.append( (var, val) )
    def run(self):
        if 'jar' in self.kwargs:
            jar = self.kwargs['jar']
        else:
            jar = self.jar
        if self.properties:
            if hasformat:
                sp = ' ' + ' '.join(
                    ['-D{0}={1}'.format(x[0], x[1]) for x in self.properties]
                )
            else:
                sp = ' ' + ' '.join(['-D%s=%s' % x for x in self.properties])
        else:
            sp = ''
        if hasformat:
            cmd = '{prog}{sp} -jar {jar} {args}'.format(
                prog=self.java_prog, sp=sp, jar=jar,
                args=' '.join([str(s) for s in self.args])
            )
        else:
            cmd = '%s%s -jar %s %s' % (
                self.java_prog, sp, jar, ' '.join([str(s) for s in self.args])
            )
        Spawn()(
            cmd
        )

# standard targets

class Help(Target):
    """This information"""
    def run(self):
        for name, obj in sorted(self.get_targets().items()):
            if hasformat:
                print('{0:20}  {1}'.format(
                        obj.__name__.lower(),
                        obj.__doc__ or ""
                    )
                )
            else:
                print('%-20s  %s' % (obj.__name__.lower(), obj.__doc__ or ""))

class Clean(Target):
    """Clean directories and files used by the build"""
    files = ()
    def run(self):
        Remove()(*self.files)

class InitDirs(Target):
    """Create initial directories"""
    files = ()
    def run(self):
        Mkdir()(*self.files)

class Init(Target):
    """Initialize the build"""
    dependencies = ("InitDirs",)

class Compile(Target):
    """Do something interesting"""
    # meant to be overriden

class Build(Target):
    """The primary build"""
    dependencies = ("Init", "Compile")

class Dist(Target):
    """The primary packaging"""
    dependencies = ("Build",)
    # may be overriden

# default target
class All(Target):
    """Do it all"""
    dependencies = ("Clean", "Dist")

class Default(Target):
    dependencies = ("Dist",)

# test code
if __name__ == '__main__':
    from os.path import join
    import os, tempfile
    from sys import exc_info
    try:
        tmpdir = tempfile.mkdtemp('.d', 'pymake')
    except OSError:
        e = exc_info()[1]
        raise SystemExit(e)
    else:
        try:
            open(join(tmpdir, 'foobar'), 'w').write("""\
This is a story,
Of a lovely lady,
With three very lovely girls.
""")
            class Foobar_utd(Uptodate):
                sources = ('foobar',)
                destinations = (join('build', 'foobar'),)
            class DistTar_utd(Uptodate):
                sources = ('foobar',)
                destinations = (join('dist', 'xyzzy.tgz'),)
            class Compile(Target):
                uptodates = ('Foobar_utd',)
                def run(self):
                    Copy()(
                        'foobar',
                        join('build', 'foobar')
                    )
            class DistTar_t(Tar):
                name = join('dist', 'xyzzy.tgz')
                root = 'build'
                files = ('foobar',)
            Dist.tasks = ('DistTar_t',)
            Dist.uptodates = ('DistTar_utd',)
            Clean.files = ('build', 'dist')
            InitDirs.files = ('build', 'dist')
            tmpdiropt = '--directory=' + str(tmpdir)
            pymain('-v', tmpdiropt, 'clean')
            pymain('-v', tmpdiropt) # default
            pymain('-v', tmpdiropt) # default with uptodate
        finally:
            Remove()(tmpdir)

