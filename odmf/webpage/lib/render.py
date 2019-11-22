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

from ...config import conf

markdown = MarkDown()

loader = TemplateLoader([str(p.absolute() / 'templates') for p in conf.static if (p / 'templates').exists()],
                        auto_reload=True)

def as_json(obj):
    """
    Builds a JSON string representation of the given object using __jdict__ methods
    of the objects or of owned objects
    Parameters
    ----------
    obj
        The object to stringify

    Returns
    -------
    A JSON string
    """
    def jsonhandler(obj):
        if hasattr(obj, '__jdict__'):
            return obj.__jdict__()
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        else:
            return obj

    return json.dumps(obj, sort_keys=True, indent=4, default=jsonhandler).encode('utf-8')


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


def formatdate(t=None):
    if not t:
        return datetime.today().strftime('%d.%m.%Y')
    try:
        return t.strftime('%d.%m.%Y')
    except (TypeError, ValueError):
        return None


def formattime(t, showseconds=True):
    try:
        return t.strftime('%H:%M:%S' if showseconds else '%H:%M')
    except (TypeError, ValueError):
        return None


def formatdatetime(t=None, fmt='%d.%m.%Y %H:%M:%S'):
    if not t:
        t = datetime.now()
    try:
        return t.strftime(fmt)
    except (TypeError, ValueError):
        return None


def formatfloat(v, style='%g'):
    try:
        return style % v
    except (TypeError, ValueError):
        return 'N/A'


def parsedate(s, raiseerror=True):
    res = None
    formats = ('%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M', '%d.%m.%Y',
               '%Y/%m/%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S')
    for fmt in formats:
        try:
            res = datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            pass
    if not res and raiseerror:
        raise ValueError('%s is not a valid date/time format' % s)
    else:
        return res


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
