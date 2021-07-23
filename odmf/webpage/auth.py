'''
Created on 05.09.2012

@author: philkraf
The file borrows heavily from 
http://tools.cherrypy.org/wiki/AuthenticationAndAccessRestrictions
'''

import os.path as op
import collections

import cherrypy

from ..tools import hashpw, get_bcrypt_salt

ACCESS_LEVELS = [["Guest", "0"],
                 ["Logger", "1"],
                 ["Editor", "2"],
                 ["Supervisor", "3"],
                 ["Admin", "4"]]


def levels_supervisor():
    return levels_admin()[:2]


def levels_admin():
    return ACCESS_LEVELS[1:5]


def get_levels(level):
    if level == int(ACCESS_LEVELS[3][1]):
        return levels_supervisor()
    elif level == int(ACCESS_LEVELS[4][1]):
        return levels_admin()
    else:
        return ACCESS_LEVELS


SESSION_KEY = '#!35625/Schwingbach?Benutzer'


def sessionuser()->str:
    "Returns the username saved in the session"
    return cherrypy.session.get(SESSION_KEY)


class HTTPAuthError(cherrypy.HTTPError):
    def __init__(self, referrer=None):
        self.referrer = referrer or cherrypy.request.path_info
        super().__init__(401, f"You do not have sufficient rights to access {self.referrer}")

    def get_error_page(self, *args, **kwargs):
        from .lib import render
        user = users.current
        error = f'Sorry, {user.name}, your status as a **{user.group}** is not sufficient to access **{self.referrer}**. ' \
                f'Either log in with more privileges or ask the administrators for elevated privileges.'
        return render('login.html', error=error, frompage='').render().encode('utf-8')


def check_auth(*args, **kwargs):
    """Checks the authentification for a given page. 
    Function is exported as a cherrypy tool
    """
    conditions = cherrypy.request.config.get('auth.require')
    user = sessionuser()
    if user:
        cherrypy.request.login = user
    if conditions is not None:
        if user:
            for condition in conditions:
                # A condition is just a callable that returns true or false
                if not condition():
                    raise HTTPAuthError()
        else:
            raise HTTPAuthError()


cherrypy.tools.auth = cherrypy.Tool('before_handler', check_auth)


def abspath(fn):
    "Returns the absolute path to the relative filename fn"
    basepath = op.abspath(op.dirname(__file__))
    normpath = op.normpath(fn)
    return op.join(basepath, normpath)


class group:
    "This class is only a constant holder, for using code completion for require "
    guest = 'guest'
    logger = 'logger'
    editor = 'editor'
    supervisor = 'supervisor'
    admin = 'admin'


class User(object):
    groups = ('guest', 'logger', 'editor', 'supervisor', 'admin')

    @classmethod
    def __level_to_group(cls, level):
        if level >= 0 and level < len(User.groups):
            return User.groups[level]
        else:
            return "Unknown level %i" % level

    def __init__(self, name, level, password, projects=None):
        self.name = name
        self.level = int(level)
        self.password = password
        self.person = None
        self.projects = projects or []

    @property
    def group(self):
        return User.__level_to_group(self.level)

    def is_member(self, group):
        grouplevel = User.groups.index(group)
        return self.level >= grouplevel

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


class Users(collections.Mapping):
    filename = abspath('../users')

    def __init__(self):
        self.default = User('guest', 0, None)
        self.dict = {}

    def __getitem__(self, name):
        return self.dict[name]

    def __len__(self):
        return len(self.dict)

    def __iter__(self):
        return iter(self.dict)

    def __contains__(self, user):
        return user in self.dict

    def load(self):
        from .. import db
        with db.session_scope() as session:
            q = session.query(db.Person).filter(db.Person.active == True)

            self.dict = {}
            allpersons = q.all()

            for person in allpersons:
                self.dict[person.username] = User(
                    person.username, person.access_level, person.password, [pr.project.id for pr in person.projects])

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
        for name in self.dict:
            f.write('%s %i %s\n' % self[name].as_tuple())
        f.close()

    @property
    def current(self) -> User:
        return self.get(cherrypy.request.login, self.default)

    def set_default(self, name):
        self.default = self.dict.get(name, self.default)


    def login(self, username, password):
        self.load()
        error = self.check(username, password)
        if error:
            return error
        else:
            cherrypy.session.regenerate()
            cherrypy.session[SESSION_KEY] = cherrypy.request.login = username
            return

    def logout(self):
        sess = cherrypy.session
        username = sess.get(SESSION_KEY, None)
        sess[SESSION_KEY] = None
        if username:
            cherrypy.request.login = None


users = Users()



def is_member(group):
    return bool(users.current) and users.current.is_member(group)


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


def member_of(groupname):
    def check():
        user = users.current
        return user and user.is_member(groupname)
    return check


def has_level(level):
    def check():
        user = users.current
        return user and user.level >= int(level)
    return check


def expose_for(groupname=None):
    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = {}
        if groupname:
            f._cp_config.setdefault('auth.require', []).append(
                member_of(groupname))
        f.exposed = True
        f.level = groupname
        return f
    return decorate


def is_self(name):
    return users.current.name == name

