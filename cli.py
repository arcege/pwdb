#!/usr/bin/python

import os
from cmd import Cmd
from database import Database

DB_Filename = os.path.expanduser(os.path.join('~', '.pwdb'))
DB_Filename = 'passwordy.db'

__all__ = [
  'PwdbCmd'
]

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
        print '\n'.join(sorted(tags))
    def help_list(self):
        print 'Display all tags'

    def do_show(self, argstr):
        args = argstr.split()
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
        try:
            self.db.open()
            force = False
            for entry in self.db:
                tagset = entry.label.split(',')
                for i in xrange(len(tagset)):
                    print 'tagset[%d] = %s' % (i, repr(tagset[i]))
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
            entries = list(self.db)
        finally:
            self.db.close()
        count = 0
        try:
            for entry in entries:
                if args:
                    if args[0] in entry:
                        print entry.name
                        count += 1
                else:
                    print entry.name
                    count += 1
                count = self.paginator(count)
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
            notes = raw_input('Notes: ')
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
                    if self.yesorno('Remove %s' % entry.name):
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
            notes = raw_input('%s: ' % entry.fieldnames['notes'])
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
            print '%s:' % entry.fieldnames['name'], new_name
            print '%s:' % entry.fieldnames['acct'], new_acct
            print '%s:' % entry.fieldnames['pswd'], new_pswd
            print '%s:' % entry.fieldnames['url'], new_url
            print '%s:' % entry.fieldnames['label'], new_label
            print '%s:' % entry.fieldnames['notes'], new_notes
            if self.yesorno('Is this correct?'):
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
        length = raw_input('Length? [10] ')
        if not length:
            length = '10'
        symbols = self.yesorno('Symbols?', resprequired=False, allowintr=True)
        cmd = 'newpasswd --number=%s' % length
        if symbols:
            cmd = cmd + ' --symbols'
        while True:
            f = os.popen(cmd + ' 2>/dev/null', 'r')
            line = f.readline()
            rc = f.close()
            if rc:
                print 'Error generating new password'
                raise KeyboardInterrupt  # caught in the caller
            (strength, password) = line.rstrip().split('\t', 1)
            print line.rstrip()
            if self.yesorno('Is this acceptable?', allowintr=True):
                break
        return password

    def yesorno(self, prompt, resprequired=True, allowintr=False):
        resp = ''
        if allowintr:
            exceptions = (RuntimeError,)
        else:
            exceptions = (EOFError, KeyboardInterrupt)
        while not resp:
            try:
                resp = raw_input('%s [y/N]' % prompt)
            except exceptions:
                print
                return False
            else:
                if not resp and resprequired:
                    continue
                else:
                    return (resp[:1].lower() == 'y')
        return False

    def paginator(self, count):
        lines = self.get_lines()
        #print 'paginator(count=%d, lines=%d)' % (count, lines)
        if count < lines-1:
            return count
        raw_input('Type ENTER for more>')
        return 0
    def get_lines(self):
        try:
            return self.lines
        except AttributeError:
            try:
                self.lines = int(os.environ['LINES'])
            except KeyError:
                f = os.popen('stty size', 'r')
                r, c = f.readline().strip().split()
                self.lines = int(r)
                f.close()
            return self.lines

if __name__ == '__main__':
    try:
        cli = PwdbCmd()
        cli.cmdloop()
    except KeyboardInterrupt:
        print

