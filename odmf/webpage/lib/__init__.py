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


def show_in_nav():
    """
    Use as a class / method decorator to flag an exposed object in the site navigation

    @show_in_nav
    @expose
    class SubPage:
        ...
    """
    def decorate(f):
        f.show_in_nav = True
        return f
    return decorate