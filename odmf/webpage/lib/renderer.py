"""
Tools to render html templates
"""

import inspect
import kajiki
import kajiki.entities
from kajiki.template import literal
from pathlib import Path

from .. import auth
from ...config import conf
from . import render_tools
from . import conversion


def escape(text, quotes=True):
    """Create a Markup string from a string and escape special characters
    it may contain (<, >, & and \").

    >>> escape('"1 < 2"')
    <Markup '&#34;1 &lt; 2&#34;'>

    If the `quotes` parameter is set to `False`, the \" character is left
    as is. Escaping quotes is generally only required for strings that are
    to be used in attribute values.

    >>> escape('"1 < 2"', quotes=False)
    <Markup '"1 &lt; 2"'>

    :param text: the text to escape
    :param quotes: if ``True``, double quote characters are escaped in
                   addition to the other special characters
    :return: the escaped `Markup` string
    """
    if not text:
        return ''
    text = text.replace('&', '&amp;') \
        .replace('<', '&lt;') \
        .replace('>', '&gt;')
    if quotes:
        text = text.replace('"', '&#34;')
    return literal(text)

_alias = {

    'index': 'home'
}

def alias(name):
    return _alias.get(name, name)


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

    p_vars = dict(vars(type(obj)))
    p_vars.update(vars(obj))
    p_vars = {
        k: v for k, v
        in p_vars.items()
        if not k.startswith('_') and navigatable(v)
    }
    if recursive:
        res = {
            alias(k): resource_walker(v, only_navigatable)
            for k, v in p_vars.items()
            if navigatable(v)
        }
    else:
        res = {
            alias(k): getdoc(v)
            for k, v in p_vars.items()
            if navigatable(v)
        }

    return res or getdoc(obj)


def get_nav_entries():
    return resource_walker(
        render.root,
        only_navigatable=True,
        recursive=False,
        for_level=auth.users.current.level
    )


def navigation(title=''):

    return literal(
        render(
            'navigation.html',
             title=str(title),
             background_image=conf.nav_background,
             left_logo=conf.nav_left_logo,
             resources=get_nav_entries().items(),
         ).render())


def context(**kwargs):
    def context_from_module(module):
        return {
            name: func
            for name, func in vars(module).items()
            if name[0] != '_'
    }
    context = context_from_module(render_tools)
    context.update(context_from_module(conversion))

    context.update(kwargs)
    context.update({'conf': conf, 'navigation': navigation})
    return context


class Renderer(object):
    def __init__(self):
        self.loader = kajiki.FileLoader(
            [str(Path(p).absolute() / 'templates')
             for p in conf.static
             if (Path(p) / 'templates').exists()
             ]
        )
        self.root = None

    def set_root(self, root):
        self.root = root

    def __call__(self, template_file, **kwargs):
        """Function to render the given data to the template specified via the
        ``@output`` decorator.
        """
        template = self.loader.import_(template_file)
        # get all objects defined in render_tools

        return template(context(**kwargs))


render = Renderer()
