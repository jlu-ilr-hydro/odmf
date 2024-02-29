from glob import glob
import os
import os.path as op
import typing
import bcrypt
from ..config import conf
import pathlib

__all__ = ['mail', 'Path']


class Path(object):
    def __init__(self, *path: str|Path|pathlib.Path, absolute=False):
        self.datapath = op.realpath(conf.datafiles)
        if path:
            if type(path[0]) is pathlib.Path:
                self.absolute = str(path[0].absolute())
            elif type(path[0]) is Path:
                self.absolute = path[0].absolute
            elif str(path[0]).startswith('/') or absolute:
                self.absolute = op.realpath(op.join(*path))
            else:
                self.absolute = op.realpath(op.join(self.datapath, *path))
            self.name = op.relpath(self.absolute, self.datapath).replace('\\', '/')
        else:
            self.absolute = self.datapath
            self.name = '/'

    def __hash__(self):
        return hash(self.datapath)

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

    @property
    def raw_url(self)->str:
        return f'{conf.root_url}/datafiles/{self.name}'

    def __bool__(self):
        return op.exists(self.absolute)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"odmf.tools.Path('{self.name}')"

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

    def as_path(self):
        import pathlib
        return pathlib.Path(self.absolute)

    def __lt__(self, other):
        return ('%s' % self) < ('%s' % other)

    def __eq__(self, other):
        return ('%s' % self) == ('%s' % other)

    def __gt__(self, other):
        return ('%s' % self) > ('%s' % other)

    def __add__(self, fn):
        return Path(op.join(self.absolute, fn))

    def __truediv__(self, fn):
        return Path(op.join(self.absolute, fn))

    def make(self):
        os.makedirs(self.absolute, mode=0o770)

    def breadcrumbs(self) -> list[Path]:
        res = [self]
        p = op.dirname(self.absolute)
        while self.datapath in p:
            res.insert(0, Path(p))
            p = op.dirname(p)
        return res

    def child(self, filename) -> Path:
        return Path(op.join(self.absolute, filename))

    def isdir(self) -> bool:
        return op.isdir(self.absolute)

    def isroot(self) -> bool:
        return self.absolute == self.datapath

    def isfile(self) -> bool:
        return op.isfile(self.absolute)

    def exists(self) -> bool:
        return op.exists(self.absolute)

    def parent(self) -> Path:
        return Path(op.dirname(self.absolute))

    def ishidden(self):
        return self.basename.startswith('.') or self.basename == 'index.html'

    def listdir(self, hidden=False) -> (typing.List[Path], typing.List[Path]):
        """
        Lists all members of the path in
        2 lists:

        directories, files: The subdirectories and the files in path


        """
        files = []
        directories = []
        if self.isdir() and self.islegal():
            for child in self.iterdir(hidden):
                if child.isdir():
                    directories.append(child)
                elif child.isfile():
                    files.append(child)
            return directories, files
        else:
            return [], []

    def iterdir(self, hidden=False) -> typing.Generator[Path]:
        if self.isdir() and self.islegal():
            for fn in os.listdir(self.absolute):
                if hidden or not fn.startswith('.'):
                    yield self.child(fn)


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

    def to_pythonpath(self) -> pathlib.Path:
        return pathlib.Path(self.absolute)

    def glob(self, pattern: str):
        """
        Finds all files fitting the glob pattern in this path. This path should be a directory
        :param pattern: a wild card pattern, eg. *.txt
        :return: List of Paths
        """
        return [
            Path(g, True)
            for g in glob((self / pattern).absolute)
        ]

    def glob_up(self, pattern: str):
        """
        A generator that yields files fitting the glob pattern in this path or any parent directories of self. Stops
        at the home directory.

        :raises: StopIteration if pattern is not found
        :param pattern: a wildcard pattern, eg. *.txt
        :yield: the first fitting file
        """
        path = Path(self.absolute, True)
        while not path.glob(pattern):
            path = path.parent()
            # if stoppath is found raise an error
            if not path.islegal():
                raise IOError('Could not find lab-config.yml file for file description')
        # Use the first .conf file in the directory
        return Path(glob(path / pattern))[0]

    @classmethod
    def from_pythonpath(cls, pypath: pathlib.Path):
        return cls(str(pypath.absolute()), absolute=True)


def hashpw(password, salt=None):
    """
    This function is written as generic solution for using a hashing algorithm

    :param password: unicode or string
    :param salt: unicode or string, when it's not given salt is generated randomly
    :return: hashed password
    """
    password = password.encode(encoding='utf-8', errors='xmlcharrefreplace')

    if salt:
        salt = salt.encode(encoding='utf-8', errors='xmlcharrefreplace')
        hashed_password = bcrypt.hashpw(password, salt)
    else:
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

    # important to decode again, is byte otherwise
    return hashed_password.decode()


def get_bcrypt_salt(hashed):
    """
    Get the salt from on bcrypt hashed string
    """
    return hashed[:29]
