#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Web interface for ICON-machine, based on cherrypy

Author: Philipp Kraft
"""
from __future__ import division


from os import path as op

import cherrypy
import threading
import json
from datetime import datetime

from genshi.core import Stream
from genshi.output import encode, get_serializer
from genshi.template import Context, TemplateLoader
from genshi.core import Markup

import collections
import auth

def jsonhandler(obj):
    if hasattr(obj,'__jdict__'):
        return obj.__jdict__()
    elif hasattr(obj,'isoformat'):
        return obj.isoformat()
    else:
        return obj 

def as_json(iterable):
    return json.dumps(list(iterable),sort_keys=True,indent=4,default=jsonhandler)


def abspath(fn):
    "Returns the absolute path to the relative filename fn"
    basepath = op.abspath(op.dirname(__file__))
    normpath = op.normpath(fn)
    return op.join(basepath,normpath)



config =  { '/': {
                    'tools.staticdir.root' : abspath('.'),
                    
                  },
            '/media': {
                       'tools.staticdir.on': True,
                       'tools.staticdir.dir': 'media',
                       'tools.caching.on' : False,
                       },
           '/html': {
                       'tools.staticdir.on': True,
                       'tools.staticdir.dir': 'templates',
                       'tools.caching.on' : False,
                       },

           '/datafiles' : {
                       'tools.staticdir.on': True,
                       'tools.staticdir.dir': 'datafiles'
                       },
           }

class mime:
    json='application/json'
    plain='text/plain'
    xml='text/xml'
    html='text/html'
    jpeg='image/jpeg'
    png='image/png'
    csv='text/csv'

def mimetype(type):
    def decorate(func):
        def wrapper(*args, **kwargs):
            cherrypy.response.headers['Content-Type'] = type
            return func(*args, **kwargs)
        return wrapper
    return decorate


def setmime(type):
    cherrypy.response.headers['Content-Type'] = type
    
    
loader = TemplateLoader(abspath('templates'),
                            auto_reload=True)



expose = cherrypy.expose
HTTPRedirect = cherrypy.HTTPRedirect
def navigation():
    return Markup(render('navigation.html').render('xml'))
def attrcheck(kw,condition):
    if condition:
        return {kw:kw}
    else:
        return {kw:None}
def markoption(condition):
    return attrcheck('selected',condition)

def formatdate(t=None):
    if not t:
        return datetime.today().strftime('%d.%m.%Y')
    try:
        return t.strftime('%d.%m.%Y')
    except:
        return None
def formattime(t):
    try:
        return t.strftime('%H:%M:%S')
    except:
        return None
def formatdatetime(t=None):
    if not t:
        t=datetime.now()
    try:
        return t.strftime('%d.%m.%Y %H:%M:%S')
    except:
        return None
    
def parsedate(s):
    res=None
    formats = '%d.%m.%Y %H:%M:%S','%d.%m.%Y %H:%M','%d.%m.%Y','%Y/%m/%dT%H:%M:%S'
    for fmt in formats:
        try:
            res=datetime.strptime(s,fmt)
        except ValueError:
            pass
    if res is None:
        raise ValueError('%s is not a valid date/time format')
    return res 

def user():
    return cherrypy.request.login
    
    
class Renderer(object):
    def __init__(self):
        self.functions = {'attrcheck' : attrcheck,
                          'navigation' : navigation,
                          'markoption' : markoption,
                          'formatdate' : formatdate,
                          'formattime' : formattime,
                          'formatdatetime' : formatdatetime,
                          'user' : user,
                          'users': auth.users,
                          'is_member': auth.is_member,
                          'bool2js' : lambda b : str(b).lower()
                          }
    def __call__(self,*args,**kwargs):
        """Function to render the given data to the template specified via the
        ``@output`` decorator.
        """
        if args:
            assert len(args) == 1, \
                'Expected exactly one argument, but got %r' % (args,)
            template = loader.load(args[0])
        else:
            template = cherrypy.thread_data.template
        ctxt = Context(url=cherrypy.url)
        ctxt.push(kwargs)
        ctxt.push(self.functions)
        return template.generate(ctxt)

render = Renderer()


class httpServer(threading.Thread):
    """The cherrypy quickstart server in a seperate thread. You can kill the thread
    but not stop it.
    """
    def run(self):
        self.server = cherrypy.quickstart(root=self.root,config=self.config)
    def __init__(self,root,config=config,autoreload=False):
        cherrypy.config.update({"engine.autoreload_on":autoreload})
        super(httpServer,self).__init__()
        self.server=None
        self.root = root
        cherrypy.server.socket_host="0.0.0.0"
        self.config = config
        self.daemon = True
        self.start()

       

def conv(cls,s,default=None):
    try:
        return cls(s)
    except:
        return default



def start_server(root,autoreload=False, port=8080):
    cherrypy.config.update({"engine.autoreload_on":autoreload})
    cherrypy.config["tools.encode.encoding"] = "utf-8"
    cherrypy.config["tools.encode.on"] = True
    cherrypy.config["tools.encode.decode"] = True

    cherrypy.server.socket_host="0.0.0.0"
    cherrypy.server.socket_port=port
    cherrypy.quickstart(root=root,config=config)
      
         
