from .. import auth
from ...tools import Path
import yaml
import dataclasses
import typing
from enum import IntFlag

filename = '.access.yml'
owner_file = '.owner'
class Mode(IntFlag):
    """
    This flag shows what can be done with a file. Read only, read/write or admin rights
    """
    none = 0
    read = 1
    write = 3
    admin = 7
@dataclasses.dataclass
class AccessRule:
    """
    Access files are hidden files to steer the access to a directory and its children. They are in yaml format
    and contain a rule object. The rule properties are:

    - owner: str the user name of the owner of this directory (admin access)
    - write: int default 9, access level needed for write access
    - read: bool default write, access level needed for read access
    - projects: list[int] list of projects this rule relates to. If empty the global
            access level of the user is taken

    The site admin (user.level=4), the project admins and the directory owner have admin access (may delete files)

    """

    write: Mode = 0
    read: Mode = 0
    projects: list = dataclasses.field(default_factory=list)


    def __call__(self, user: auth.User, owner:str = None) -> Mode:
        """
        Returns if a user has admin access 7, read/write access 3, read only access 1 or 0 for no access to this ressource
        """
        if user.level>=4 or user.name==owner:
            return Mode.admin

        if self.projects:
            max_level = max([auth.Level.guest] + [user.projects[p] for p in self.projects if p in user.projects])
        else:
            max_level = user.level
        if max_level >= auth.Level.admin:
            return Mode.admin
        elif max_level >= self.write:
            return Mode.write
        elif max_level >= self.read:
            return Mode.read
        else:
            return Mode.none

    def save(self, path: Path):
        with open((path / filename).absolute, 'w') as f:
            yaml.safe_dump(self.__dict__, f)

    @classmethod
    def from_file(cls, path: Path):
        with open(path.absolute) as f:
            content = yaml.safe_load(f)
            return AccessRule(**content)

    @classmethod
    def find_rule(cls, path: Path):
        for bc in reversed(path.breadcrumbs()):
            if (yml := bc / filename).exists():
                return AccessRule.from_file(yml)
        else:
            return AccessRule()

def get_owner(path: Path) -> str|None:
    """
    Loads the owner of a directory. Returns the owner's user name or None if no owner present
    """
    path = Path(path)
    for bc in reversed(path.breadcrumbs()):
        if (fn := bc / owner_file).exists():
            with open(fn.absolute) as f:
                return f.read().strip()
    else:
        return 'odmf.admin'

def set_owner(path: Path, owner: str):
    with open((path / owner_file).absolute, 'w') as f:
        f.write(owner)


def check_directory(path: Path, user: auth.User) -> Mode:
    """
    Checks if a .access.yml file is in the directory path and applies the given user to the rules. If no .access.yml
    file is present, the function looks into the parent directories and uses their access rule.
    :param path:
    :param user:
    :return: 7: Admin access,
    """
    path = Path(path)
    owner = get_owner(path)
    rule = AccessRule.find_rule(path)
    return rule(user, owner)


def check_children(path: Path, user: auth.User) -> typing.Dict[Path, Mode]:
    """
    Checks the path like check_directory and all children directories for existing access rules. If rules are present,
    the rules of the children are returned, else the rule of the parent
    :param path: A path to a directory
    :param user: A auth.User
    :return: A dict[Path: int] containing for each path in [path, path/*] the accessibility value [7,3,1,0]
    """
    def check_child(p: Path):
        if (yml:=p / filename).exists():
            owner = get_owner(p)
            return p, AccessRule.from_file(yml)(user, owner)
        else:
            return p, parent_mode
    path = Path(path)
    parent_mode = check_directory(path, user)
    return {path: parent_mode} | dict(
        check_child(f)
        for f in path.iterdir()
    )


def walk(path: Path, user: auth.User, mode=Mode.read) -> typing.List[Path]:
    """
    Walks recursively through all files and directories in path respecting the access rules
    :param path: The parent path, should be a directory
    :param user: the user requesting the access rules
    :param mode: the minimal access mode, usually Mode.read
    :return: list of paths
    """
    result = []
    if check_directory(path, user) >= mode:
        directories, files = path.listdir()
        result.extend(files)
        for d in directories:
            result.extend(walk(d, user, mode))
    return result



