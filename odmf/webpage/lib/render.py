"""
Tools to render html templates
"""


import cherrypy
import json
from datetime import datetime, timedelta

from genshi.template import Context, TemplateLoader
from genshi.core import Markup

from .. import auth
from ..markdown import MarkDown
from .conversion import *
from ...config import conf

markdown = MarkDown()

loader = TemplateLoader([str(p.absolute() / 'templates') for p in conf.static if (p / 'templates').exists()],
                        auto_reload=True)


def navigation(title=''):
    return Markup(render('navigation.html',
                         title=str(title),
                         background_image=conf.nav_background,
                         left_logo=conf.nav_left_logo,
                         ).render('html', encoding=None))


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
    return cherrypy.request.login


def not_external():
    return not ("external" in cherrypy.url())


class Renderer(object):
    def __init__(self):
        self.functions = {
            'attrcheck': attrcheck,
            'navigation': navigation,
            'markoption': markoption,
            'formatdate': formatdate,
            'formattime': formattime,
            'formatdatetime': formatdatetime,
            'formatfloat': formatfloat,
            'datetime': datetime,
            'timedelta': timedelta,
            'user': user,
            'users': auth.users,
            'is_member': auth.is_member,
            'bool2js': lambda b: str(b).lower(),
            'markdown': markdown,
            'as_json': as_json,
            'abbrtext': abbrtext,
            'not_external': not_external
        }

    def __call__(self, *args, **kwargs):
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

        # head base for all templates
        # see conf.py
        ctxt.push({'head_base': conf.head_base})
        return template.generate(ctxt)


render = Renderer()
