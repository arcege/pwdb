#!/usr/bin/python

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
from pwdb.database import Database

DB_Filename = os.path.expanduser(os.path.join('~', '.pwdb'))
#DB_Filename = 'passwordy.db'

__all__ = [
  'PwdbCmd'
]

class Ed:
    def __init__(self, lines):
        from tempfile import mktemp
        self.filename = mktemp('ed')
        if lines:
            self.buffer = lines + '\n'
        else:
            self.buffer = ''
    def run(self):
        open(self.filename, 'w').write(self.buffer)
        os.system('ed %s' % self.filename)
        self.buffer = open(self.filename, 'r').read()
        return self.buffer.rstrip()

def YorN(prompt, reqresp=True, allowintr=False):
    resp = ''
    import sys, termios
    real_prompt = '%s [y/N]' % prompt
    infd = sys.stdin.fileno()
    outfd = sys.stdout.fileno()
    old = termios.tcgetattr(infd)
    new = old[:]
    new[3] &= ~(termios.ECHO|termios.ICANON)
    try:
        termios.tcsetattr(infd, termios.TCSADRAIN, new)
        os.write(outfd, real_prompt)
        while not resp:
            ch = os.read(infd, 1)
            if allowintr and ch == '\003': raise KeyboardInterrupt
            if allowintr and ch == '\004': raise EOFError
            if ch.lower() == 'y': resp = 'y'
            elif ch.lower() == 'n': resp = 'n'
            elif not reqresp: break
    finally:
        termios.tcsetattr(outfd, termios.TCSADRAIN, old)
        os.write(outfd, resp)
        os.write(outfd, '\n')
    return resp == 'y'

class Paginator:
    def __init__(self, lines, input=None, output=None):
        self.oldtermio = self.newtermio = None
        import sys, termios
        self.textlines = lines
        self.pos = 0
        self.lines = self.get_lines()
        if input:
            self.infd = input.fileno()
        else:
            self.infd = sys.stdin.fileno()
        if output:
            self.outfd = output.fileno()
        else:
            self.outfd = sys.stdout.fileno()
        self.tcsetattr = termios.tcsetattr
        self.TCSADRAIN = termios.TCSADRAIN
        self.oldtermio = termios.tcgetattr(self.infd)
        self.newtermio = self.oldtermio[:]
        self.newtermio[3] &= ~(termios.ECHO | termios.ICANON)
        self.clrscn = os.popen('tput clear', 'r').readline()
    def __del__(self):
        self.reset()
    def set(self):
        if self.newtermio is not None:
            self.tcsetattr(self.infd, self.TCSADRAIN, self.newtermio)
    def reset(self):
        if self.oldtermio is not None:
            self.tcsetattr(self.infd, self.TCSADRAIN, self.oldtermio)
        self.oldtermio = None
    def run(self):
        done = False
        try:
            self.set()
            while not done:
                self.clear_screen()
                self.display()
                ch = self.more()
                if ch == 'q':
                    done = True
                elif ch == ' ': # space
                    self.pos = min(len(self.textlines), self.pos + self.lines)
                elif ch == 'j' or ch == '\n': # carriage return
                    self.pos = min(len(self.textlines), self.pos + 1)
                elif ch == 'b':
                    self.pos = max(0, self.pos - self.lines)
                elif ch == 'k':
                    self.pos = max(0, self.pos - 1)
                elif ch == 'g':
                    self.pos = 0
                elif ch == 'G':
                    self.pos = len(self.textlines) - self.lines
                elif ch == '\003': # ctrl-C
                    raise KeyboardInterrupt
                elif ch == '\004': # ctrl-D
                    raise EOFError
        finally:
            self.reset()
    def clear_screen(self):
        os.write(self.outfd, self.clrscn)
    def display(self):
        diff = 0
        tl = len(self.textlines)
        start = self.pos
        end = min(tl, self.pos + self.lines - 1)
        if end > tl:
            diff = tl - end
            start -= diff
            end = tl
        #print 'pos =', self.pos, 'textlines =', tl,
        #print 'start =', start, 'end =', end, 'diff =', diff
        for i in xrange(start, end):
            print self.textlines[i]
    def more(self):
        os.write(self.outfd, 'More>')
        ch = os.read(self.infd, 1)
        os.write(self.outfd, '\r     \r')
        return ch
    def get_lines(cls):
        try:
            return cls.lines
        except AttributeError:
            try:
                cls.lines = int(os.environ['LINES'])
            except KeyError:
                f = os.popen('stty size', 'r')
                r, c = f.readline().strip().split()
                cls.lines = int(r)
                f.close()
            return cls.lines
    get_lines = classmethod(get_lines)

class DebugCmd(Cmd):
    prompt = 'debug> '
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
            print
    def help_list(self):
        print 'list entries with uids'
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
        print 'display details of an uid or named entry'
    def display_entry(self, entry):
        print 'uid: #%s' % entry.uid
        print 'mtime: %s' % entry.mtime
        for field in ('name', 'acct', 'pswd', 'url', 'label'):
            val = getattr(entry, field)
            print '%s: %s' % (entry.fieldnames[field], val)
        print '%s:\t%s' % (
            entry.fieldnames['notes'], entry.notes.replace('\n', '\n\t')
        )
    def do_mtime(self, argstr):
        args = argstr.split()
        if len(args) != 2:
            print 'mtime requires to arguments: uid mtime'
            return False
        uid, mtime = tuple(args)
        if uid[:1] == '#':
            uid = uid[1:]
        from pwdb.database import Date
        try:
            mtime = Date(mtime)
        except ValueError:
            print 'mtime should be YYYYDDMM.HHMMSS format'
            return False
        try:
            self.db.open()
            entry = None
            for e in self.db:
                if e.uid == uid:
                    entry = e
                    break
            else:
                print 'uid not found'
            entry.mtime = mtime
            self.db.update(True)
        finally:
            self.db.close()
    def help_mtime(self):
        print 'set the mtime of an entry'

    def do_EOF(self, argstr):
        print
        return True
    def do_return(self, args):
        return True
    def help_return(self, args):
        return 'Exit the debug section'
    def do_quit(self, args):
        return True
    def help_quit(self):
        print 'Exit the tag management section'

class TagCmd(Cmd):
    prompt = 'tag> '
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
        print '\n'.join(sorted(tags))
    def help_list(self):
        print 'Display all tags'

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
                        print entry.name
                        break
        finally:
            self.db.close()
    def help_show(self):
        print 'Display list of entries with matching tags'

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
                    tagset.append(name)
                    tagset.sort()
                    entry.label = ','.join(tagset)
                    force = True
            self.db.update(force)
        finally:
            self.db.close()
    def help_add(self):
        print 'Add tag to given entries'

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
                    print entry.name
                    entry.label = ','.join(tagset)
                    force = True
            self.db.update(force)
        finally:
            self.db.close()
    def help_delete(self):
        print 'Delete one or more tags from each entry'

    def do_rename(self, argstr):
        args = argstr.split()
        if len(args) != 2:
            print 'tag rename requires two arguments'
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
                    #print 'tagset[%d] = %s' % (i, repr(tagset[i]))
                    if tagset[i] == oldtag:
                        tagset[i] = newtag
                        tagset.sort()
                        ch = True
                        break
                else:
                    ch = False
                if ch:
                    print entry.name
                    entry.label = ','.join(tagset)
                    force = True
            self.db.update(force)
        finally:
            self.db.close()
    def help_rename(self):
        print 'Rename a tag in each entry'

    def do_EOF(self, args):
        print
        return True
    def do_return(self, args):
        return True
    def help_return(self):
        print 'Exit the tag management section'
    def do_quit(self, args):
        return True
    def help_quit(self):
        print 'Exit the tag management section'

class PwdbCmd(Cmd):
    prompt = 'pwdb> '
    intro = '''Password Database command interpreter
System to view and manupulate passwords and their metadata.'''
    def __init__(self, *args, **kws):
        Cmd.__init__(self, *args, **kws)
        self.db = Database(DB_Filename)
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
            print
    def help_list(self):
        print 'Display a list of entries, by name'

    def do_show(self, argstr):
        args = argstr.split()
        try:
            self.db.open()
            for name in args:
                e = self.db.find(name)
                if e:
                    self.display_entry(e)
                else:
                    print repr(name), 'not found'
        finally:
            self.db.close()
    def help_show(self):
        print 'Display the details of one or more entries'

    def do_new(self, args):
        try:
            while True:
                name  = raw_input('Entry Name: ')
                if ' ' in name:
                    print 'Error: spaces not allowed in entry names'
                else:
                    break
            acct  = raw_input('Account Name: ')
            print "Enter '!' to generate a password"
            pswd  = raw_input('Password: ')
            if pswd == '!':
                pswd = self.gen_password()
            url   = raw_input('URL: ')
            label = raw_input('Labels: ')
            print 'Notes:'
            notes = Ed('').run()
        except (EOFError, KeyboardInterrupt):
            print
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
        print 'Enter information for a new entry into the pswd database'

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
        print 'Edit an existing entry'

    def do_remove(self, argstr):
        args = argstr.split()
        try:
            self.db.open()
            for arg in args:
                entry = self.db.find(arg)
                if entry is not None:
                    if YorN('Remove %s' % entry.name):
                        del self.db[entry]
                else:
                    print arg, 'not found'
            self.db.update()
        finally:
            self.db.close()
    def help_remove(self):
        print 'Remove one or more entries'

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
                    print entry.name
    def help_find(self):
        print 'Return list of entries with a string'

    def do_search(self, argstr):
        try:
            entries = []
            self.db.open()
            for entry in self.db:
                if entry.find(argstr):
                    entries.append(entry)
        finally:
            self.db.close()
        for entry in entries:
            print entry.name
            for key in entry.fieldnames.keys():
                val = getattr(entry, key)
                if val.find(argstr) != -1:
                    print '\t%s: %s' % (entry.fieldnames[key], val)
    def help_search(self):
        print 'Search for a string'

    def do_tag(self, argstr):
        args = argstr.split()
        cli = TagCmd(self.db)
        if not args:
            cli.cmdloop()
        else:
            cli.onecmd(argstr)
    def help_tag(tags):
        print 'tag management'

    def do_debug(self, argstr):
        cli = DebugCmd(self.db)
        if not argstr:
            cli.cmdloop()
        else:
            cli.onecmd(argstr)

    def do_EOF(self, args):
        print
        return True
    def do_quit(self, args):
        return True
    def help_quit(self):
        print 'Exit the program'

    def help_help(self):
        print 'Show information about the commands available'

    def display_entry(self, entry):
        for field in ('name', 'acct', 'pswd', 'url', 'label'):
            val = getattr(entry, field)
            print '%s: %s' % (entry.fieldnames[field], val)
        print '%s:\t%s' % (
            entry.fieldnames['notes'], entry.notes.replace('\n', '\n\t')
        )

    def edit_entry(self, entry):
        self.display_entry(entry)
        print 'Editing...'
        try:
            name  = raw_input('%s: ' % entry.fieldnames['name'])
            acct  = raw_input('%s: ' % entry.fieldnames['acct'])
            pswd  = raw_input('%s: ' % entry.fieldnames['pswd'])
            url   = raw_input('%s: ' % entry.fieldnames['url'])
            label = raw_input('%s: ' % entry.fieldnames['label'])
            print 'Notes:'
            notes = Ed(entry.notes).run()
        except (EOFError, KeyboardInterrupt):
            print
            print 'Aborting edit'
            return False
        else:
            new_name  = name  or entry.name
            new_acct  = acct  or entry.acct
            new_pswd  = pswd  or entry.pswd
            new_url   = url   or entry.url
            new_label = label or entry.label
            new_notes = notes or entry.notes
            print 'Verify...'
            for name, value in (
                ('name', new_name), ('acct', new_acct), ('pswd', new_pswd),
                ('url', new_url), ('label', new_label)):
                print '%s: ' % entry.fieldnames[name], value
            print 'Notes:\t%s' % new_notes
            if YorN('Is this correct?'):
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
            length = raw_input('Length? [10] ')
            try:
                if length != '' and int(length) <= 6:
                    print 'must be greater than 6 characters'
                else:
                    done = True
            except ValueError:
                pass
        if not length:
            length = '10'
        symbols = YorN('Symbols?', reqresp=False, allowintr=True)
        cmd = 'newpasswd --quiet --number=%s' % length
        if symbols:
            cmd = cmd + ' --symbols'
        cmd += ' 2>/dev/null'
        while True:
            f = os.popen(cmd, 'r')
            line = f.readline()
            rc = f.close()
            if rc:
                print 'Error generating new password'
                raise KeyboardInterrupt  # caught in the caller
            (strength, password) = line.rstrip().split('\t', 1)
            print line.rstrip()
            if YorN('Is this acceptable?', allowintr=True):
                break
        return password

if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'f:h',
                                    ['file=', 'help'])
    except getopt.error, e:
        raise SystemExit(e)
    for opt, val in opts:
        if opt == '--':
            break
        elif opt in ('-h', '--help'):
            print sys.argv[0], '[opts]'
            print '  -h|--help'
            print '  -f|--file=dbfile'
            raise SystemExit
        elif opt in ('-f', '--file'):
            DB_Filename = val

    try:
        try:
            cli = PwdbCmd()
            cli.cmdloop()
        except KeyboardInterrupt:
            print
    finally:
        os.system('clear')

