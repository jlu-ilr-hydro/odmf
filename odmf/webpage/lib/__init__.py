#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = [
    'render', 'markdown', 'literal', 'user',
    'cherrypy', 'method', 'mime', 'escape',
    'expose', 'json_in', 'HTTPRedirect', 'HTTPError', 'resource_walker'
]

import cherrypy
from functools import wraps

from .renderer import render, resource_walker, literal, escape
from .render_tools import markdown, user

from .conversion import *

from . import method
from .mime import mime

expose = cherrypy.expose

json_in = cherrypy.tools.json_in

HTTPRedirect = cherrypy.HTTPRedirect
HTTPError = cherrypy.HTTPError


def json_out(obj):
    """
    Decorator for exposed functions to convert the output into utf-8 encoded json
    """
    return json.dumps(
        obj,
        sort_keys=True,
        indent=4,
        default=jsonhandler
    ).encode('utf-8')


def show_in_nav_for(level=0):
    """
    Use as a class / method decorator to flag an exposed object in the site navigation

    @show_in_nav_for(users.guest)
    @expose
    class SubPage:
        ...
    """
    def decorate(f):
        f.show_in_nav = level
        f.exposed = True
        return f
    return decorate