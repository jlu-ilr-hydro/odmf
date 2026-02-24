"""
Helper functions and data to use in templates

All objects defined here will be available inside of the templates
"""
import typing

import cherrypy as __cp


from ..markdown import MarkDown as __MarkDown
__md = __MarkDown()


def markdown(s):
    from kajiki.template import literal
    return literal(__md(s))


def dict_to_html(key='', value=None):
    if value is None:
        value = key
        key = ''
    def header(key):
        if key:
            return f'''
                <a class="list-group-action" data-bs-toggle="collapse" href="#c-{key}-list">{key}<i class="fas fa-caret-down ms-2"></i></a>
                <div class="collapse list-group" id="c-{key}-list">
            '''
        else:
            return f'<div class="list-group" id="{key}-list">'

    if isinstance(value, typing.Mapping):
        body = '\n'.join(
            f'<div class="list-group-item">{dict_to_html(k, v)}</div>'
            for k, v in value.items()
        )
        return header(key) + body + '\n</div>'

    elif isinstance(value, str):
        if key:
            return f'<span class="font-weight-bold">{key}</span>: {value}'
        else:
            return str(value)

    elif isinstance(value, typing.Sequence):
        body = '\n'.join(
            f'<div class="list-group-item">{dict_to_html(value=item)}</div>'
            for item in value
        )
        return header(key) + body + '\n</div>'
    elif not key:
        return str(value)
    else:
        return f'<span class="font-weight-bold">{key}</span>: {value}'


# The imports are needed implicitly during rendering
from ..auth import users, is_member, has_level, Level
from datetime import datetime, timedelta


def prop(**kwargs):
    return {
        kw: (kw if value else None) for kw, value in kwargs.items()
    }

def disabled(condition):
    return prop(disabled=condition)

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


def bool2js(b: bool) -> str:
    return str(b).lower()

def class_if(condition, class_name, else_class=''):
    if condition:
        return class_name
    else:
        return else_class

def dnone_if(condition):
    return class_if(condition, 'd-none')

def firstline(text):
    if text:
        return str(text).split('\n', 1)[0]
    else:
        return ''

