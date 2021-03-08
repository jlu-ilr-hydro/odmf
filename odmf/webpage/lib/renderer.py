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


class Resource:

    def __init__(self, name, obj, parent=None):
        super().__init__()
        self.name = name
        self.parent = parent
        self.obj = obj
        self.__children = []

    @property
    def icon(self):
        return self.get_attr('icon')

    @property
    def doc(self):
        """Returns inspect.getdoc if available, else checks for an index method and returns the getdoc of that"""
        return inspect.getdoc(self.obj) or \
               (getattr(self.obj, 'index', None) and inspect.getdoc(self.obj.index)) or \
               (getattr(self.obj, 'default', None) and inspect.getdoc(self.obj.default))

    @property
    def methods(self):
        cp_config: dict = self.get_attr('_cp_config')
        if cp_config:
            return cp_config.get('tools.allow.methods')
        else:
            return None

    @property
    def uri(self):
        if self.parent:
            return self.parent.uri + self.name + '/'
        else:
            return conf.root_url + '/'

    def has_attr(self, attr: str) -> bool:
        return hasattr(self.obj, attr) or hasattr(type(self.obj), attr)

    def get_attr(self, attr: str) -> bool:
        return (
            getattr(self.obj, attr, None) or
            getattr(type(self.obj), attr, None)
        )

    def is_exposed(self):
        return self.has_attr('exposed') and self.obj.exposed

    @property
    def level(self):
        return self.get_attr('level')

    def is_nav(self, for_level: int):
        return self.is_exposed() and self.has_attr('show_in_nav') and self.obj.show_in_nav <= for_level

    def __repr__(self):
        return self.uri

    def __iter__(self):
        return iter(self.__children)

    def __len__(self):
        return len(self.__children)

    def extend(self, by):
        self.__children.extend(by)

    def __getitem__(self, item):
        try:
            self.__children[item]
        except TypeError:
            index = [c.name for c in self.__children].index(item)
            return self.__children[index]

    def __getattr__(self, item):
        try:
            index = [c.name for c in self.__children].index(item)
            return self.__children[index]
        except (TypeError, ValueError):
            raise AttributeError(f'{self} has no method {item}')

    def __dir__(self):
        return sorted(dir(super()) + list(vars(self).keys()) + list(vars(type(self)).keys()) + [c.name for c in self.__children])

    def create_tree(self, navigatable_for=None, recursive=True):

        obj = self.obj
        p_vars = dict(vars(type(obj)))
        p_vars.update(vars(obj))
        children = [Resource(alias(k), v, self) for k, v in p_vars.items() if k[0] != '_']

        # filter for only the exposed / navigatable selfs
        if navigatable_for is not None:
            self.extend(c for c in children if c.is_nav(navigatable_for))
        else:
            self.extend(c for c in children if c.is_exposed())

        if recursive:
            for c in self:
                c.create_tree(navigatable_for, recursive)

        return self

    def walk(self):
        res = [self]
        for c in self:
            res.extend(c.walk())
        return res


def get_nav_entries():

    root = Resource('/', render.root).create_tree(
        navigatable_for=auth.users.current.level, recursive=False
    )
    return root


def navigation(title=''):

    return literal(
        render(
            'navigation.html',
             title=str(title),
             background_image=conf.nav_background,
             left_logo=conf.nav_left_logo,
             resources=[(r.name, r.doc) for r in get_nav_entries()],
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
    context['nav_items'] = get_nav_entries()
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
        """Functn data to the template specified via the
        ``@output`` decorator.ion to render the give
        """
        template = self.loader.import_(template_file)
        # get all objects defined in render_tools
        kwargs.setdefault('title', template_file.split('.')[0])

        return template(context(**kwargs))


render = Renderer()
