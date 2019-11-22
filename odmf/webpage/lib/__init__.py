#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Web interface for ICON-machine, based on cherrypy

Author: Philipp Kraft
"""


import cherrypy
from datetime import datetime

from .render import render, markdown, as_json, user
from .mimetype_tools import mime, mimetype, setmime
from . import method

from ...config import conf


expose = cherrypy.expose


json_in = cherrypy.tools.json_in

HTTPRedirect = cherrypy.HTTPRedirect


def conv(cls, s, default=None):
    """
    Convert string s to class cls
    Parameters
    ----------
    cls
        A class to convert to (eg. float, int, datetime)
    s
        A string to convert
    default
        A default answer, if the conversion fails. Else return None

    Returns
    -------
    cls(s)

    """
    if cls is datetime:
        return parsedate(s)
    try:
        return cls(s)
    except (TypeError, ValueError):
        return default




def is_selected(a1, a2):
    """
    Helper function to compare two access_levels and return "selected" if true
    :param a1: access_level 1
    :param a2: access_level 2
    :return: String "selected" if a1 and a2 are equal
    """

    if a1 == a2:
        return {'selected': 'isSelected'}
    return ""
