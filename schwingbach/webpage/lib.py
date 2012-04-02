#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Web interface for ICON-machine, based on cherrypy

Author: Philipp Kraft
"""
from __future__ import division


from os import path as op

import cherrypy

import threading

from datetime import datetime

from genshi.core import Stream
from genshi.output import encode, get_serializer
from genshi.template import Context, TemplateLoader
from genshi.core import Markup


#import webpage


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
                       'tools.staticdir.dir': 'media'
                       },
           '/datafiles' : {
                       'tools.staticdir.on': True,
                       'tools.staticdir.dir': 'datafiles'
                       },
           }
def mimetype(type):
    def decorate(func):
        def wrapper(*args, **kwargs):
            cherrypy.response.headers['Content-Type'] = type
            return func(*args, **kwargs)
        return wrapper
    return decorate

    
loader = TemplateLoader(abspath('templates'),
                            auto_reload=True)


def output(filename, method='xhtml', encoding='utf-8', **options):
    """Decorator for exposed methods to specify what template they should use
    for rendering, and which serialization method and options should be
    applied.
    """
    def decorate(func):
        def wrapper(*args, **kwargs):
            cherrypy.thread_data.template = loader.load(filename)
            opt = options.copy()
            if method == 'html':
                opt.setdefault('doctype', 'html')
            serializer = get_serializer(method, **opt)
            stream = func(*args, **kwargs)
            if not isinstance(stream, Stream):
                return stream
            return encode(serializer(stream), method=serializer,
                          encoding=encoding)
        return wrapper
    return decorate

expose = cherrypy.expose
HTTPRedirect = cherrypy.HTTPRedirect
def navigation():
    return Markup('''
        <!--<img src="/media/icon.jpg" style="float: right"/>-->
        <div class="navigate" >
         | <a href="/map">map</a> 
         | <a href="/site">sites</a>
         | <a href="/valuetype">value types</a> 
         | <a href="/dataset">data sets</a> 
         | <a href="/user">users</a>
         | <a href="/download">download</a>
         | login: %s 
    </div>''' % user())
def attrcheck(kw,condition):
    if condition:
        return {kw:kw}
    else:
        return {kw:None}
def markoption(condition):
    return attrcheck('selected',condition)

def formatdate(t):
    try:
        return t.strftime('%d.%m.%Y')
    except:
        return None
def formattime(t):
    try:
        return t.strftime('%H:%M:%S')
    except:
        return None
def parsedate(s):
    return datetime.strptime(s,'%d.%m.%Y') 

def user():
    return cherrypy.request.login
 
    
class Renderer(object):
    def __init__(self):
        self.functions = {'attrcheck' : attrcheck,
                          'navigation' : navigation,
                          'markoption' : markoption,
                          'formatdate' : formatdate,
                          'formattime' : formattime,
                          'user' : user
                          
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

def user():
    return cherrypy.request.login

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
      
         
