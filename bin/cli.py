#!/usr/bin/python

try:
    #raise ImportError
    from argparse import ArgumentParser
except ImportError:
    ArgumentParser = None
    try:
        #raise ImportError
        from optparse import OptionParser
    except ImportError:
        OptionParser = None
        import getopt
import os
import sys
from cmd import Cmd
if os.path.exists(os.path.join(os.curdir, 'lib', 'pwdb')):
    libdir = os.path.join(os.curdir, 'lib')
elif os.path.exists(os.path.expanduser(os.path.join('~', 'lib'))):
    libdir = os.path.expanduser(os.path.join('~', 'lib'))
else:
    libdir = os.path.normpath(
        os.path.join(os.path.dirname(sys.argv[0]), os.pardir, 'lib')
    )
sys.path.insert(0, libdir)
from pwdb.database import Database, EncryptDatabase, Key
from pwdb.console import Console, Ed, Paginator

__version = '$Id$'

DB_Filename = os.path.expanduser(os.path.join('~', '.pwdb'))
#DB_Filename = 'passwordy.db'

__all__ = [
  'PwdbCmd'
]

class DebugCmd(Cmd):
    prompt = 'debug> '
    doc_leader = """\
Database debugging.
"""
    def __init__(self, db, *args, **kws):
        Cmd.__init__(self, *args, **kws)
        self.db = db

    def do_list(self, argstr):
        try:
            self.db.open()
            if argstr:
                entries = [
                    '%s\t%s' % (e.uid, e.name) for e in self.db
                        if e == argstr
                ]
            else:
                entries = [
                    '%s\t%s' % (e.uid, e.name) for e in self.db
                ]
        finally:
            self.db.close()
        try:
            Paginator(entries).run()
        except (EOFError, KeyboardInterrupt):
            console.write('\n')
    def help_list(self):
        console.write('Display list, with uids.\n')

    def do_show(self, argstr):
        args = argstr.split()
        try:
            self.db.open()
            for entry in self.db:
                for arg in args:
                    if arg[:1] == '#':
                        if entry.uid == arg[1:]:
                            self.display_entry(entry)
                    elif entry.name == arg:
                        self.display_entry(entry)
        finally:
            self.db.close()
    def help_show(self):
        console.write('Display entry with more detail.\n')

    def display_entry(self, entry):
        console.write('uid: #%s\n' % entry.uid, fg='yellow')
        console.write('mtime: %s\n' % entry.mtime, fg='yellow')
        for field in ('name', 'acct', 'pswd', 'url', 'label'):
            val = getattr(entry, field)
            console.write('%s: %s\n' % (entry.fieldnames[field], val), fg='yellow')
        console.write('%s:\t%s\n' % (
            entry.fieldnames['notes'], entry.notes.replace('\n', '\n\t')
        ), fg='yellow')

    def do_mtime(self, argstr):
        args = argstr.split()
        if len(args) != 2:
            console.write('mtime requires to arguments: uid mtime\n', fg='red')
            return False
        uid, mtime = tuple(args)
        if uid[:1] == '#':
            uid = uid[1:]
        from pwdb.database import Date
        try:
            mtime = Date(mtime)
        except ValueError:
            console.write('mtime should be YYYYDDMM.HHMMSS format\n', fg='red')
            return False
        try:
            self.db.open()
            entry = None
            for e in self.db:
                if e.uid == uid:
                    entry = e
                    break
            else:
                console.write('uid not found\n', fg='red')
            entry.mtime = mtime
            self.db.update(True)
        finally:
            self.db.close()
    def help_mtime(self):
        console.write('Modify the mtime of an entry\n')

    def do_EOF(self, argstr):
        console.write('\n')
        return True
    def do_return(self, args):
        return True
    def help_return(self, args):
        return 'return - exit the debug section'
    def do_quit(self, args):
        return True
    def help_quit(self):
        console.write('\n')

class TagCmd(Cmd):
    """tag management"""
    prompt = 'tag> '
    doc_leader = """\
Manage unified tags across entries.
"""
    def __init__(self, db, *args, **kws):
        Cmd.__init__(self, *args, **kws)
        self.db = db

    def do_list(self, argstr):
        try:
            tags = []
            self.db.open()
            for entry in self.db:
                tagset = entry.label.split(',')
                for tag in tagset:
                    if tag not in tags:
                        tags.append(tag)
        finally:
            self.db.close()
        if '' in tags:
            p = tags.index('')
            tags[p] = '-'
        console.write('\n'.join(sorted(tags))+'\n')
    def help_list(self):
        console.write('Display list of tags.\n')

    def do_show(self, argstr):
        args = argstr.split()
        if '-' in args:
            p = args.index('-')
            args[p] = ''
        try:
            self.db.open()
            for entry in self.db:
                tagset = entry.label.split(',')
                for arg in args:
                    if arg in tagset:
                        console.write(entry.name + '\n')
                        break
        finally:
            self.db.close()
    def help_show(self):
        console.write('Display entries with a specific tag.\n')

    def do_add(self, argstr):
        args = argstr.split()
        name = args[0]
        if name == '-':
            name = ''
        del args[0]
        try:
            self.db.open()
            force = False
            for entry in self.db:
                if entry.name in args:
                    tagset = entry.label.split(',')
                    if name not in tagset:
                        tagset.append(name)
                        tagset.sort()
                    entry.label = ','.join(tagset)
                    force = True
            self.db.update(force)
        finally:
            self.db.close()
    def help_add(self):
        console.write('Add tag to set of entries.\n')

    def do_delete(self, argstr):
        args = argstr.split()
        try:
            self.db.open()
            force = False
            for entry in self.db:
                tagset = entry.label.split(',')
                ch = False
                for arg in args:
                    if arg == '-':
                        arg = ''
                    if arg in tagset:
                        tagset.remove(arg)
                        tagset.sort()
                        ch = True
                if ch:
                    console.write(entry.name + '\n')
                    entry.label = ','.join(tagset)
                    force = True
            self.db.update(force)
        finally:
            self.db.close()
    def help_delete(self):
        console.write('Remove tag from set of entries.\n')

    def do_rename(self, argstr):
        args = argstr.split()
        if len(args) != 2:
            console.write('tag rename requires two arguments\n', fg='red')
            return
        oldtag, newtag = args
        if oldtag == '-':
            oldtag = ''
        if newtag == '-':
            newtag = ''
        try:
            self.db.open()
            force = False
            for entry in self.db:
                tagset = entry.label.split(',')
                for i in xrange(len(tagset)):
                    #console.write('tagset[%d] = %s\n' % (i, repr(tagset[i])))
                    if tagset[i] == oldtag:
                        tagset[i] = newtag
                        tagset.sort()
                        ch = True
                        break
                else:
                    ch = False
                if ch:
                    console.write(entry.name + '\n')
                    entry.label = ','.join(tagset)
                    force = True
            self.db.update(force)
        finally:
            self.db.close()
    def help_rename(self):
        console.write('Rename existing tag.\n')

    def do_EOF(self, args):
        console.write('\n')
        return True
    def do_return(self, args):
        return True
    def help_return(self):
        console.write('\n')
    def do_quit(self, args):
        return True
    def help_quit(self):
        console.write('\n')

class PwdbCmd(Cmd):
    prompt = 'pwdb> '
    intro = '''Password Database command interpreter
System to view and manipulate passwords and their metadata.'''
    doc_leader = """\
Command interpreter for securely managing account passwords.
"""
    def __init__(self, *args, **kws):
        key = kws['key']
        del kws['key']
        Cmd.__init__(self, *args, **kws)
        self.key = key
        #console.write('key=%s\n' % repr(key))
        kls = Database.check_file_type(DB_Filename)
        self.db = kls(DB_Filename, self.key)
        self.db.open() # to force data key decryption check
    def emptyline(self):
        pass

    def do_list(self, argstr):
        args = argstr.split()
        try:
            self.db.open()
            if argstr:
                entrynames = [ e.name for e in self.db if e == argstr ]
            else:
                entrynames = [ e.name for e in self.db ]
        finally:
            self.db.close()
        try:
            Paginator(entrynames).run()
        except (EOFError, KeyboardInterrupt):
            console.write('\n')
    def help_list(self):
        console.write('Display entries by name.\n')

    def do_show(self, argstr):
        args = argstr.split()
        try:
            self.db.open()
            for name in args:
                e = self.db.find(name)
                if e:
                    self.display_entry(e)
                else:
                    console.write(repr(name), 'not found\n', fg='red')
        finally:
            self.db.close()
    def help_show(self):
        console.write('\n')

    def do_new(self, args):
        try:
            while True:
                name  = console.input('Entry Name:')
                if ' ' in name:
                    console.write(
                        'Error: spaces not allowed in entry names\n',
                        fg='red'
                    )
                else:
                    break
            acct  = console.input('Account Name:')
            console.write("Enter '!' to generate a password\n")
            pswd  = console.input('Password:')
            if pswd == '!':
                pswd = self.gen_password()
            url   = console.input('URL:')
            label = console.input('Labels:')
            console.write('\n')
            notes = Ed('').run()
        except (EOFError, KeyboardInterrupt):
            console.write('\n')
        else:
            self.db.open()
            entry = self.db.new()
            entry.name = name
            entry.acct = acct
            entry.pswd = pswd
            entry.url = url
            entry.label = label
            entry.notes = notes
            self.db.set(entry)
            self.db.update()
            self.db.close()
    def help_new(self):
        console.write('Populate a new entry.\n')

    def do_edit(self, argstr):
        args = argstr.split()
        try:
            entries = []
            self.db.open()
            changed = False
            for entry in self.db:
                for arg in args:
                    if entry == str(arg):
                        if self.edit_entry(entry):
                            entry.mtime = entry.mtime.now()
                            changed = True
            self.db.update(changed)
        finally:
            self.db.close()
    def help_edit(self):
        console.write('Edit an existing entry; only modified fields are changed\n')

    def do_remove(self, argstr):
        args = argstr.split()
        try:
            self.db.open()
            for arg in args:
                entry = self.db.find(arg)
                if entry is not None:
                    if console.YorN('Remove %s' % entry.name):
                        del self.db[entry]
                else:
                    console.write(arg, 'not found\n', fg='red')
            self.db.update()
        finally:
            self.db.close()
    def help_remove(self):
        console.write('Remove an existing entry.\n')

    def do_find(self, argstr):
        args = argstr.split()
        try:
            self.db.open()
            entries = list(self.db)
        finally:
            self.db.close()
        for entry in entries:
            for arg in args:
                if arg in entry:
                    console.write(entry.name + '\n')
    def help_find(self):
        console.write('Display list of entries containing matching string.\n')

    def do_search(self, argstr):
        try:
            import re
            cmp = re.compile(argstr, re.IGNORECASE)
        except re.error:
            et, ev, es = sys.exc_info()
            console.write(str(ev) + '\n', fg='red')
            return
        try:
            lastentry = None
            self.db.open()
            for entry in self.db:
                for key in list(entry.fieldnames.keys()):
                    val = getattr(entry, key)
                    if cmp.search(val):
                        # was this entry's name printed already
                        if lastentry != entry:
                            console.write(entry.name + '\n')
                            lastentry = entry
                        console.write('\t%s: %s\n' % (entry.fieldnames[key], val))
        finally:
            self.db.close()
    def help_search(self):
        console.write('Display matches.\n')

    def do_tag(self, argstr):
        args = argstr.split()
        cli = TagCmd(self.db)
        if not args:
            cli.cmdloop()
        else:
            cli.onecmd(argstr)
    def help_tag(self):
        TagCmd(self.db).onecmd('help')

    def do_debug(self, argstr):
        cli = DebugCmd(self.db)
        if not argstr:
            cli.cmdloop()
        else:
            cli.onecmd(argstr)

    def do_EOF(self, args):
        console.write('\n')
        return True
    def do_quit(self, args):
        return True
    def help_quit(self):
        console.write('\n')

    def help_help(self):
        console.write('\n')

    def display_entry(self, entry):
        for field in ('name', 'acct', 'pswd', 'url', 'label'):
            val = getattr(entry, field)
            console.write('%s: %s\n' % (entry.fieldnames[field], val))
        console.write('%s:\t%s\n' % (
            entry.fieldnames['notes'], entry.notes.replace('\n', '\n\t')
        ))

    def edit_entry(self, entry):
        self.display_entry(entry)
        console.write('\n')
        try:
            name  = console.input('%s:' % entry.fieldnames['name'])
            acct  = console.input('%s:' % entry.fieldnames['acct'])
            pswd  = console.input('%s:' % entry.fieldnames['pswd'])
            url   = console.input('%s:' % entry.fieldnames['url'])
            label = console.input('%s:' % entry.fieldnames['label'])
            console.write('\n')
            notes = Ed(entry.notes).run()
        except (EOFError, KeyboardInterrupt):
            console.write('\n')
            console.write('Aborting edit\n', fg='red')
            return False
        else:
            new_name  = name  or entry.name
            new_acct  = acct  or entry.acct
            new_pswd  = pswd  or entry.pswd
            new_url   = url   or entry.url
            new_label = label or entry.label
            new_notes = notes or entry.notes
            console.write('\n')
            for name, value in (
                ('name', new_name), ('acct', new_acct), ('pswd', new_pswd),
                ('url', new_url), ('label', new_label)):
                if getattr(entry, name) == value:
                    console.write('%s: %s\n' % (entry.fieldnames[name], value))
                else:
                    console.write('%s: %s\n' % (entry.fieldnames[name], value), fg='green', attr='bold')
            if getattr(entry, 'notes') == new_notes:
                console.write('Notes:\t%s\n' % new_notes)
            else:
                console.write('Notes:\t%s\n' % new_notes, fg='green', attr='bold')
            if console.YorN('Is this correct?'):
                entry.name  = new_name
                entry.acct  = new_acct
                entry.pswd  = new_pswd
                entry.url   = new_url
                entry.label = new_label
                entry.notes = new_notes
                return True
            else:
                return False

    def gen_password(self):
        password = ''
        done = False
        while not done:
            length = console.input('Length? [10]')
            try:
                if length != '' and int(length) <= 6:
                    console.write('must be greater than 6 characters\n', fg='red')
                else:
                    done = True
            except ValueError:
                pass
        if not length:
            length = '10'
        symbols = console.YorN('Symbols?', reqresp=False, allowintr=True)
        cmd = 'newpasswd --number=%s' % length
        if symbols:
            cmd = cmd + ' --strong'
        cmd += ' 2>/dev/null'
        while True:
            f = os.popen(cmd, 'r')
            line = f.readline()
            rc = f.close()
            if rc:
                console.write('Error generating new password\n', fg='red')
                raise KeyboardInterrupt  # caught in the caller
            (strength, password) = line.rstrip().split('\t', 1)
            console.write(line.rstrip() + '\n')
            if console.YorN('Is this acceptable?', allowintr=True):
                break
        return password

def real_main(key):
    PwdbCmd(key=key).cmdloop()

def profile_main(key):
    global Profile_fname
    profile.runctx("real_main(key)", globals(), locals(), Profile_fname)

console = None

if __name__ == '__main__':
    if ArgumentParser:
        #console.write('\n')
        parser = ArgumentParser()
        parser.add_argument('-f', '--file', dest='filename',
                            help="different database file",
                            metavar="dbfile")
        args = parser.parse_args()
        if args.filename:
            DB_Filename = args.filename
    elif OptionParser:
        #console.write('\n')
        parser = OptionParser()
        parser.add_option('-f', '--file', dest='filename',
                          help="different database file",
                          metavar="dbfile")
        (opts, args) = parser.parse_args()
        if opts.filename:
            DB_Filename = opts.filename
    else:
        #console.write('\n')
        try:
            opts, args = getopt.getopt(sys.argv[1:], 'f:h',
                                        ['file=', 'help'])
        except getopt.error:
            et, ev, es = sys.exc_info()
            raise SystemExit(ev)
        for opt, val in opts:
            if opt == '--':
                break
            elif opt in ('-h', '--help'):
                console.write('% [opts]\n' % sys.argv[0])
                console.write('  -h|--help\n')
                console.write('  -f|--file=dbfile\n')
                raise SystemExit
            elif opt in ('-f', '--file'):
                DB_Filename = val

    console = Console()

    kls = Database.check_file_type(DB_Filename)
    if kls == EncryptDatabase:
        try:
            key = Key(console.get_key('Key'))
        except (KeyboardInterrupt, EOFError):
            #console.write('\n')
            raise SystemExit
    else:
        key = None

    if 'PROFILING' in os.environ:
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
        try:
            mainfunc(key)
        #except ValueError:
        #    et, ev, es = sys.exc_info()
        #    raise SystemExit(ev)
        #except RuntimeError:
        #    et, ev, es = sys.exc_info()
        #    raise SystemExit(ev)
        except KeyboardInterrupt:
            console.write('\n')
    finally:
        os.system('clear')

