"""
Tools to render html templates
"""


import cherrypy
import inspect
from datetime import timedelta

from genshi.template import Context, TemplateLoader
from genshi.core import Markup

from .. import auth
from ..markdown import MarkDown
from .conversion import *
from ...config import conf


markdown = MarkDown()

loader = TemplateLoader([str(p.absolute() / 'templates') for p in conf.static if (p / 'templates').exists()],
                        auto_reload=True)


def resource_walker(obj, only_navigatable=False, recursive=True, for_level=0) -> dict:
    """
    Builds a recursive tree of exposed cherrypy endpoints

    How to call for a tree of the complete app:
    ::
        resource_tree = resource_walker(root)

    How to call for a branch in the app (eg. the site page)
    ::
        resource_subtree = resource_walker(root, site)

    :param obj: The cherrypy object (type or function) to investigate
    :return: A dictionary containing either a dictionary for the next deeper address level or a
            docstring of an endpoint
    """
    def has_attr(obj, attr: str) -> bool:
        return hasattr(obj, attr) or hasattr(type(obj), attr)

    def navigatable(obj):
        try:
            return has_attr(obj, 'exposed') and obj.exposed and (
                    (not only_navigatable) or has_attr(obj, 'show_in_nav') and obj.show_in_nav <= for_level
            )
        except TypeError:
            raise

    def getdoc(obj):
        """Returns inspect.getdoc if available, else checks for an index method and returns the getdoc of that"""
        return inspect.getdoc(obj) or \
               (getattr(obj, 'index', None) and inspect.getdoc(obj.index)) or \
               (getattr(obj, 'default', None) and inspect.getdoc(obj.default))

    p_vars = dict((k, getattr(obj, k)) for k in dir(obj))
    p_vars = {k: v for k, v in p_vars.items() if not k.startswith('_') and navigatable(v)}
    if recursive:
        res = {
            k: resource_walker(v, only_navigatable)
            for k, v in p_vars.items()
            if navigatable(v)
        }
    else:
        res = {
            k: getdoc(v)
            for k, v in p_vars.items()
            if navigatable(v)
        }

    return res or getdoc(obj)


def navigation(title=''):
    return Markup(render('navigation.html',
                         title=str(title),
                         background_image=conf.nav_background,
                         left_logo=conf.nav_left_logo,
                         resources=resource_walker(render.functions['root'], True, False, auth.users.current.level)
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
            'not_external': not_external,
            'conf': conf,
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
