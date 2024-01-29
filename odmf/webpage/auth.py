'''
Created on 05.09.2012

@author: philkraf
The file borrows heavily from 
http://tools.cherrypy.org/wiki/AuthenticationAndAccessRestrictions
'''

import os.path as op
import collections
import typing

import cherrypy
from ..config import conf
from ..tools import hashpw, get_bcrypt_salt
from enum import IntEnum


def sessionuser()->str:
    "Returns the username saved in the session"
    return cherrypy.session.get(conf.session_key)


class HTTPAuthError(cherrypy.HTTPError):
    def __init__(self, referrer=None):
        self.referrer = referrer or cherrypy.request.path_info
        super().__init__(401, f"You do not have sufficient rights to access {self.referrer}")

    def get_error_page(self, *args, **kwargs):
        from .lib import render
        from .. import db
        user = users.current
        error = f'Sorry, {user.name}, your status as a **{user.group}** is not sufficient to access **{self.referrer}**. ' \
                f'Either log in with more privileges or ask the administrators for elevated privileges.'
        try:
            with db.session_scope() as session:
                admins = session.scalars(db.sql.select(db.Person).where(db.Person.access_level >= 4, db.Person.active == True))
                return render('login.html', admins=admins, error=error, frompage='').render().encode('utf-8')
        except:
            return render('login.html', admins=[], error=error, frompage='').render().encode('utf-8')


def check_auth(*args, **kwargs):
    """Checks the authentification for a given page. 
    Function is exported as a cherrypy tool
    """
    conditions = cherrypy.request.config.get('auth.require')
    user = sessionuser()
    if user:
        cherrypy.request.login = user
    if conditions is not None:
        for condition in conditions:
            # A condition is just a callable that returns true or false
            if not condition():
                raise HTTPAuthError()


cherrypy.tools.auth = cherrypy.Tool('before_handler', check_auth)


def abspath(fn):
    "Returns the absolute path to the relative filename fn"
    basepath = op.abspath(op.dirname(__file__))
    normpath = op.normpath(fn)
    return op.join(basepath, normpath)



class Level(IntEnum):
    guest = 0
    logger = 1
    editor = 2
    supervisor = 3
    admin = 4

    @staticmethod
    def my(project=None):
        """
        Returns the level of the current user
        """
        if users.current:
            return users.current.get_level(project)
        else:
            return Level.guest


class User(object):

    def __init__(self, name, level, password, projects=None):
        self.name = name
        self.level = Level(level)
        self.password = password
        self.person = None
        self.projects: typing.Dict[int, Level] = projects or {}

    @property
    def group(self) -> str:
        return self.level.name

    def is_member(self, level: Level|str|int, project:int=None) -> bool:
        if type(level) is str:
            level=Level[level]
        else:
            level = Level(level or 0)
        return self.get_level(project) >= level

    def get_level(self, project: int|None = None) -> Level:
        """
        Returns the level of this user. If a project is given, return the level for that project
        :param project: int (project-id) or db.Project
        :return:
        """
        if project is None or self.level>=Level.admin:
            return self.level
        else:
            if hasattr(project, 'id'):
                project = project.id
            return self.projects.get(project, Level.guest)


    def check(self, password):

        # Salt of the password out of the db into unicode too
        salt = get_bcrypt_salt(self.password)

        # Input password and the salt out of the db
        hashed_password = hashpw(password, salt)

        return hashed_password == self.password

    def as_tuple(self):
        return self.name, self.level, self.password

    def __repr__(self):
        return "User(%s,%i,'xxxx')" % (self.name, self.level)

    def __str__(self):
        return "%s (%s)" % (self.name, self.group)


class Users(collections.UserDict):
    filename = abspath('../users')

    def __init__(self):
        self.default = User('guest', 0, None)
        super().__init__()


    def load(self):
        from .. import db
        with db.session_scope() as session:
            q = session.query(db.Person).filter(db.Person.active == True)

            self.data = {
                person.username: User(
                    person.username, person.access_level, person.password,
                    projects={project.id: Level(l) for project, l in person.projects()}
                )
                for person in q
            }

    def check(self, username, password):

        if username not in self:
            self.load()
            return "User '%s' not found" % username
        elif self[username].check(password):
            return
        else:
            return "Password not correct"

    def list(self):
        if not self:
            self.load()
        return sorted(self)

    def save(self):
        f = open(Users.filename, 'w')
        for name in self.data:
            f.write('%s %i %s\n' % self[name].as_tuple())
        f.close()

    @property
    def current(self) -> User:
        if not self:
            self.load()
        return self.get(cherrypy.request.login, self.default)

    def set_default(self, name):
        self.default = self.data.get(name, self.default)

    def login(self, username, password):
        self.load()
        error = self.check(username, password)
        if error:
            return error
        else:
            cherrypy.session.regenerate()
            cherrypy.session[conf.session_key] = cherrypy.request.login = username
            return

    def logout(self):
        cherrypy.request.login = None
        cherrypy.session[conf.session_key] = None
        cherrypy.lib.sessions.expire()


users = Users()



def is_member(level: Level|str, project=None):
    return bool(users.current) and users.current.is_member(level, project)


def require(*conditions):
    """A decorator that appends conditions to the auth.require config
    variable."""
    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = dict()
        if 'auth.require' not in f._cp_config:
            f._cp_config['auth.require'] = []
        f._cp_config['auth.require'].extend(conditions)
        f.exposed = True
        return f
    return decorate


def member_of(level: Level|str|int, project: int = None):
    def check():
        if level:
            user = users.current
            return bool(user) and user.is_member(level, project)
        else:
            return True
    return check


def has_level(level):
    def check():
        user = users.current
        return user and user.level >= Level(level)
    return check


def expose_for(groupname=None):
    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = {}
        else:
            f._cp_config.setdefault('auth.require', []).append(
                member_of(groupname)
            )
        f.exposed = True
        f.level = groupname
        return f
    return decorate


def is_self(name):
    return users.current.name == name

