from __future__ import annotations

import os
import os.path as op
import typing
from ..config import conf

__all__ = ['mail', 'Path']


class Path(object):
    def __init__(self, *path: str):
        self.datapath = op.realpath(conf.datafiles)
        if path:
            if str(path[0]).startswith('/'):
                self.absolute = op.realpath(op.join(*path))
            else:
                self.absolute = op.realpath(op.join(self.datapath, *path))
            self.name = op.relpath(self.absolute, self.datapath).replace('\\', '/')
        else:
            self.absolute = self.datapath
            self.name = '/'

    @property
    def basename(self)->str:
        return op.basename(self.absolute)

    @property
    def href(self)->str:
        return f'{conf.root_url}/download/{self.name}'

    @property
    def markdown(self)->str:
        if self.islegal():
            return 'file:' + str(self)
        else:
            return ''

    def __bool__(self):
        return op.exists(self.absolute)

    def __str__(self):
        return self.name

    def formatsize(self)->str:
        size = op.getsize(self.absolute)
        unit = 0
        units = "B KB MB GB".split()
        while size > 1024 and unit < 3:
            size = size / 1024.
            unit += 1
        return "%5.4g %s" % (size, units[unit])

    def islegal(self) -> bool:
        return self.absolute.startswith(self.datapath)

    def __lt__(self, other):
        return ('%s' % self) < ('%s' % other)

    def __eq__(self, other):
        return ('%s' % self) == ('%s' % other)

    def __gt__(self, other):
        return ('%s' % self) > ('%s' % other)

    def __add__(self, fn):
        return Path(op.join(self.absolute, fn))

    def make(self):
        os.makedirs(self.absolute, mode=0o770)

    def breadcrumbs(self) -> str:
        res = [self]
        p = op.dirname(self.absolute)
        while self.datapath in p:
            res.insert(0, Path(p))
            p = op.dirname(p)
        return res

    def child(self, filename):
        return Path(op.join(self.absolute, filename))

    def isdir(self):
        return op.isdir(self.absolute)

    def isroot(self):
        return self.absolute == self.datapath

    def isfile(self):
        return op.isfile(self.absolute)

    def exists(self):
        return op.exists(self.absolute)

    def parent(self):
        return Path(op.dirname(self.absolute))

    def ishidden(self):
        return self.basename.startswith('.') or self.basename == 'index.html'

    def listdir(self) -> (typing.List[Path], typing.List[Path]):
        """
        Lists all members of the path in
        2 lists:

        directories, files: The subdirectories and the files in path


        """
        files = []
        directories = []
        if self.isdir() and self.islegal():
            for fn in os.listdir(self.absolute):
                if not fn.startswith('.'):
                    child = self.child(fn)
                    if child.isdir():
                        directories.append(child)
                    elif child.isfile():
                        files.append(child)
            return directories, files
        else:
            return [], []

    def isempty(self) -> bool:
        """
        Returns True, if self isdir and has no entries
        """
        dirs, files = self.listdir()
        files = [f for f in files
                 if not f.ishidden()
                 ]
        return not bool(dirs or files)

    def up(self) -> str:
        return op.dirname(self.name)

    def delete(self):
        os.unlink(self.absolute)

