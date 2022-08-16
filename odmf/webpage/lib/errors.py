
from traceback import format_exc as traceback

import cherrypy
from cherrypy import HTTPError as _HTTPError

from logging import getLogger
from ..markdown import MarkDown
from .renderer import render
from . import as_json
from . import mime
from ..auth import users, group

markdown = MarkDown()
logger = getLogger(__name__)


def format_traceback(tb: str) -> str:
    if users.current.is_member(group.admin):
        return f'\n\n```\n{tb}\n```\n'
    else:
        return ''

# Add Errorhandling to the Cherrypy configuration - possibly different for the API
# than for the browser part:
# https://stackoverflow.com/questions/20395565/how-to-catch-all-exceptions-with-cherrypy

class AJAXError(_HTTPError):
    """
    To be raised from a method that is called with an AJAX method like
    XMLHTTPRequest or $.ajax, $.post, $.get.

    Example with jquery:
    $.post(
        uri, data
    ).success(data => ...
    ).fail(response => $('#error').html(response.responseText)
    )
    """
    def __init__(self, status: int, message: str):
        self.traceback = traceback()
        self.message = message
        logger.warning(self.traceback)
        super().__init__(status, str(message))

    def get_error_page(self, *args, **kwargs):
        mime.html.set()
        return markdown(self.message + format_traceback(self.traceback)).encode('utf-8')


def to_html(error=None, success=None, text=None):
    return render('empty.html', error=error, success=success, content=text).render()


class HTTPError(_HTTPError):
    def __init__(self, status: int, message: str):
        self.message = message
        self.traceback = traceback()
        logger.warning(self.traceback)
        super().__init__(status, str(message))

    def get_error_page(self, *args, **kwargs):
        cherrypy.response.headers['Content-Type'] = 'text/html'
        if users.current.level == group.admin:
            text = '\n```\n' + self.traceback + '\n```\n'
        else:
            text = None
        return to_html(error=self.message, text=text).encode('utf-8')


class APIError(_HTTPError):

    def __init__(self, status: int, message: str):
        self.message = message
        self.traceback = traceback()
        logger.warning(self.traceback)
        super().__init__(status, str(message))

    def get_error_page(self, *args, **kwargs):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        if users.current.level == group.admin:
            data = dict(status=self.status, text=self.message, traceback=self.traceback)
        else:
            data = dict(status=self.status, text=self.message)
        return as_json(data).encode('utf-8')
