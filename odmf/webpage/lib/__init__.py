#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = [
    'render', 'markdown', 'Markup', 'user',
    'cherrypy', 'method', 'mime',
    'expose', 'json_in', 'HTTPRedirect', 'HTTPError'
]

import cherrypy

from .render import render, markdown, Markup, user

from .conversion import *

from . import method
from .mime import mime

expose = cherrypy.expose

json_in = cherrypy.tools.json_in

HTTPRedirect = cherrypy.HTTPRedirect
HTTPError = cherrypy.HTTPError


def setmime(mime_type):
    cherrypy.response.headers['Content-Type'] = str(mime_type)
