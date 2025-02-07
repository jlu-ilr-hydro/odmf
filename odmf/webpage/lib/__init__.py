#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = [
    'render', 'markdown', 'literal', 'user',
    'cherrypy', 'method', 'mime', 'escape',
    'expose', 'json_in', 'HTTPRedirect', 'HTTPError', 'Resource', 'AJAXError'
]

import cherrypy
from urllib.parse import urlencode

from .renderer import render, Resource, literal, escape
from .render_tools import markdown, user

from .conversion import *

from . import method
from .mime import mime

from .errors import AJAXError, HTTPError, APIError

expose = cherrypy.expose

json_in = cherrypy.tools.json_in

HTTPRedirect = cherrypy.HTTPRedirect


def redirect(url, **kwargs):
    """
    Raises cherrypy.InternalRedirect with the keyword arguments as query string

    eg.

    .. code::

       redirect('/xyz', a=2, b='Hallo')

    redirects to /xyz?a=2&b=Hallo
    """
    cherrypy.session['error'] = kwargs.pop('error', None)
    cherrypy.session['success'] = kwargs.pop('success', None)
    cherrypy.session['info'] = kwargs.pop('info', None)

    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    qs = urlencode(kwargs)
    if qs:
        url += '?' + qs
    return cherrypy.HTTPRedirect(url)


def json_out(obj=None, **kwargs):
    """
    Decorator for exposed functions to convert the output into utf-8 encoded json
    """
    mime.json.set()
    if obj is None:
        obj = kwargs
    return json.dumps(
        obj,
        sort_keys=True,
        indent=4,
        default=jsonhandler
    ).encode('utf-8')


def show_in_nav_for(level=0, icon=None):
    """
    Use as a class / method decorator to flag an exposed object in the site navigation

    @show_in_nav_for(users.guest)
    @expose
    class SubPage:
        ...
    """
    def decorate(f):
        f.show_in_nav = level
        f.icon = icon
        f.exposed = True
        return f
    return decorate
