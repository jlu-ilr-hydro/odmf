'''
Created on 05.09.2012

@author: philkraf
The file borrows heavily from 
http://tools.cherrypy.org/wiki/AuthenticationAndAccessRestrictions
'''
from operator import le
import os.path as op
import collections
#import md5
import cherrypy

import db
from sqlalchemy import func
import bcrypt

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


def sessionuser():
    "Returns the username saved in the session"
    return cherrypy.session.get(SESSION_KEY)


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
                    raise cherrypy.HTTPRedirect(
                        "/login?error=You are missing privileges to do what you liked to do.&frompage=" + cherrypy.request.path_info)
        else:
            raise cherrypy.HTTPRedirect(
                "/login?error=You need to be logged in, to access this page&frompage=" + cherrypy.request.path_info)


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

    def __init__(self, name, level, password):
        self.name = name
        self.level = int(level)
        self.password = password
        self.person = None

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
        self.dict = {}
        self.load()

    def __getitem__(self, name):
        return self.dict[name]

    def __len__(self):
        return len(self.dict)

    def __iter__(self):
        return iter(self.dict)

    def __contains__(self, user):
        return user in self.dict

    def load(self):
        session = db.Session()

        q = session.query(db.Person).filter(db.Person.active == True)

        self.dict = {}
        allpersons = q.all()

        for person in allpersons:
            self.dict[person.username] = User(
                person.username, person.access_level, person.password)

    def check(self, username, password):

        if username not in self:
            return "User '%s' not found" % username
        elif self[username].check(password):
            return
        else:
            return "Password not correct"

    def list(self):
        return sorted(self)

    def save(self):
        f = open(Users.filename, 'w')
        for name in self.dict:
            f.write('%s %i %s\n' % self[name].as_tuple())
        f.close()

    @property
    def current(self):
        return self.get(cherrypy.request.login)

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
        return f
    return decorate


def is_self(name):
    return users.current.name == name


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
