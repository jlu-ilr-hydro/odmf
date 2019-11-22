#!/usr/bin/env python
# -*- coding: utf-8 -*-


import cherrypy

from .render import render, markdown, as_json, user, conv
from . import method
from .mime import mime

expose = cherrypy.expose

json_in = cherrypy.tools.json_in

HTTPRedirect = cherrypy.HTTPRedirect
HTTPError = cherrypy.HTTPError


def mimetype(content_type: str):
    def deco(func):
        def wrapper(*args, **kwargs):
            cherrypy.response.headers['Content-Type'] = str(content_type)
            return func(*args, **kwargs)
        return wrapper
    return deco


def setmime(mime_type):
    cherrypy.response.headers['Content-Type'] = str(mime_type)
