'''
Created on 05.09.2012

@author: philkraf
The file borrows heavily from http://tools.cherrypy.org/wiki/AuthenticationAndAccessRestrictions
'''
import os.path as op
import collections
import md5
import cherrypy

SESSION_KEY='#!35625/Schwingbach?Benutzer'
def sessionuser():
    "Returns the username saved in the session"
    return cherrypy.session.get(SESSION_KEY)

def check_auth(*args,**kwargs):
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
                    raise cherrypy.HTTPRedirect("/login?error=You are missing privileges to do what you liked to do.&frompage="+cherrypy.request.path_info)
        else:
            raise cherrypy.HTTPRedirect("/login?error=You need to be logged in, to access this page&frompage="+cherrypy.request.path_info)

cherrypy.tools.auth = cherrypy.Tool('before_handler', check_auth)    

def abspath(fn):
    "Returns the absolute path to the relative filename fn"
    basepath = op.abspath(op.dirname(__file__))
    normpath = op.normpath(fn)
    return op.join(basepath,normpath)

class group:
    "This class is only a constant holder, for using code completion for require "
    guest='guest'
    logger='logger'
    editor='editor'
    supervisor='supervisor'
    admin='admin'
class User(object):
    groups = ('guest','logger','editor','supervisor','admin')
    @classmethod 
    def __level_to_group(cls,level):
        if level>=0 and level<len(User.groups):
            return User.groups[level]
        else:
            return "Unknown level %i" % level

    def __init__(self,name,level,password):
        self.name=name
        self.level = int(level)
        self.password = password
        self.person=None
    @property
    def group(self):
        return User.__level_to_group(self.level)
    def is_member(self,group):
        grouplevel = User.groups.index(group)
        return self.level>= grouplevel
    def check(self,password):
        return password == self.password
    def as_tuple(self):
        return self.name,self.level,self.password
    def __repr__(self):
        return "User(%s,%i,'xxxx')" % (self.name,self.level)
    def __str__(self):
        return "%s (%s)" % (self.name,self.group)

class Users(collections.Mapping):
    filename = abspath('../users')
    def __init__(self):
        self.dict={}
        self.load()
    def __getitem__(self,name):
        return self.dict[name]
    def __len__(self):
        return len(self.dict)
    def __iter__(self):
        return iter(self.dict)
    def __contains__(self,user):
        return user in self.dict
    def load(self):
        if op.exists(Users.filename):
            f = file(Users.filename)
            self.dict={}
            for line in f:
                ls = line.split()
                self.dict[ls[0]] = User(*ls)
            f.close()
    def check(self,username,password):
        if not username in self:
            return "User '%s' not found" % username
        elif self[username].check(password):
            return
        else:
            return "Password not correct"
    def list(self):
        return sorted(self)
    def save(self):
        f = file(Users.filename,'w')
        for name in self.dict:
            f.write('%s %i %s\n' % self[name].as_tuple())
        f.close()
    @property
    def current(self):
        return self.get(cherrypy.request.login)
    def login(self,username,password):
        self.load()
        error=self.check(username, password)
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
        return f
    return decorate

def member_of(groupname):
    def check():
        user=users.current
        return user and user.is_member(groupname)
    return check

def has_level(level):
    def check():
        user=users.current
        return user and user.level>=int(level)
    return check


