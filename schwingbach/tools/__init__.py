import os
import os.path as op

__all__ = ['mail']

datapath = op.abspath(op.join(op.dirname(__file__),
                              '..', 'webpage', 'datafiles'))
home = op.dirname(datapath)
try:
    import grp
    try:
        osgroup = gid = grp.getgrnam("users").gr_gid
    except:
        osgroup = None
except ImportError:
    osgroup = None


class Path(object):
    def __init__(self, abspath):
        self.absolute = op.realpath(abspath)
        self.name = op.relpath(self.absolute, datapath).replace('\\', '/')
        self.basename = op.basename(self.absolute)
        if op.isdir(self.absolute):
            self.href = '/download?dir=%s' % self.name
        else:
            self.href = '/' + \
                op.relpath(self.absolute, home).replace('\\', '/')

    def __bool__(self):
        return op.exists(self.absolute)

    def __str__(self):
        return self.name

    def formatsize(self):
        size = op.getsize(self.absolute)
        unit = 0
        units = "B KB MB GB".split()
        while size > 1024 and unit < 3:
            size = size / 1024.
            unit += 1
        return "%5.4g %s" % (size, units[unit])

    @property
    def is_legal(self):
        return self.absolute.startswith(datapath)

    def __lt__(self, other):
        return ('%s' % self) < ('%s' % other)

    def __eq__(self, other):
        return ('%s' % self) == ('%s' % other)

    def __gt__(self, other):
        return ('%s' % self) > ('%s' % other)

    def __add__(self, fn):
        return Path(op.join(self.absolute, fn))

    def setownergroup(self, gid=None):
        gid = gid or osgroup
        if gid and hasattr(os, 'chown'):
            os.chown(self.absolute, -1, gid)

    def make(self):
        os.makedirs(self.absolute)

    def breadcrumbs(self):
        res = [self]
        p = op.dirname(self.absolute)
        while datapath in p:
            res.insert(0, Path(p))
            p = op.dirname(p)
        return res

    def child(self, filename):
        return Path(op.join(self.absolute, filename))

    def isdir(self):
        return op.isdir(self.absolute)

    def isfile(self):
        return op.isfile(self.absolute)

    def exists(self):
        return op.exists(self.absolute)

    def listdir(self):
        return os.listdir(self.absolute)

    def up(self):
        return op.dirname(self.name)
