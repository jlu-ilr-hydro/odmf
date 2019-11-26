"""
Tools to render html templates
"""


import cherrypy
import inspect
from datetime import timedelta


from kajiki import FileLoader
from kajiki.template import literal

from .. import auth
from ...config import conf

from . import render_tools


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
             resources=get_nav_entries(),
         ).render('html', encoding=None))


class Renderer(object):
    def __init__(self):
        self.loader = FileLoader(
            [str(p.absolute() / 'templates')
             for p in conf.static
             if (p / 'templates').exists()
             ]
        )
        self.root = None

    def __call__(self, template_file, **kwargs):
        """Function to render the given data to the template specified via the
        ``@output`` decorator.
        """
        template = self.loader.import_(template_file)
        # get all objects defined in render_tools
        context = {
            name: func
            for name, func in vars(render_tools).items()
            if name[0] != '_'
        }

        context.update(kwargs)
        context.update({'conf': conf, 'navigation': navigation})

        return template(context)


render = Renderer()
