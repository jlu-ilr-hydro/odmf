"""
Helper functions and data to use in templates

All objects defined here will be available inside of the templates
"""

import cherrypy as __cp


from ..markdown import MarkDown as __MarkDown
__md = __MarkDown()


def markdown(s):
    from kajiki.template import literal
    return literal(__md(s))

# The imports are needed implicitly during rendering
from ..auth import users, is_member, has_level, Level
from datetime import datetime, timedelta


def prop(**kwargs):
    return {
        kw: (kw if value else None) for kw, value in kwargs.items()
    }


def markoption(condition):
    return prop(selected=condition)


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

