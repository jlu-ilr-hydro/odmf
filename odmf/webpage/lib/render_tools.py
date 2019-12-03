"""
Helper functions and data to use in templates

All objects defined here will be available inside of the templates
"""

import cherrypy as __cp


from ..markdown import MarkDown as __md

markdown = __md()

from ..auth import users

def attrcheck(kw, condition):
    if condition:
        return {kw: kw}
    else:
        return {kw: None}


def markoption(condition):
    return attrcheck('selected', condition)


def abbrtext(s, maxlen=50):
    if s:
        s = str(s).replace('\n', ' ')
        if len(s) > maxlen:
            idx = s.rfind(' ', 0, maxlen - 4)
            s = s[:idx] + ' ...'
        return s
    else:
        return ''


def user():
    return __cp.request.login


def not_external():
    return not ("external" in __cp.url())


def bool2js(b: bool) -> str:
    return str(b).lower()

