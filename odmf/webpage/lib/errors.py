import datetime

from traceback import format_exc as traceback

import textwrap as tw
import cherrypy
from cherrypy import HTTPError as _HTTPError

from logging import getLogger
from ..markdown import MarkDown
from .renderer import render
from . import mime
from ..auth import users, Level, is_member

markdown = MarkDown()
logger = getLogger(__name__)


def format_traceback(tb: str) -> str:
    if users.current.is_member(Level.admin):
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


def to_html(error=None, success=None, info=None, text=None):
    cherrypy.response.headers['Content-Type'] = 'text/html'
    return render('empty.html', title='Error', error=error, success=success, info=info, content=text).render()


class HTTPError(_HTTPError):
    def __init__(self, status: int, message: str):
        super().__init__(status, str(message))
        self.traceback = traceback()
        self.message = message
        logger.warning(self.traceback)


class APIError(HTTPError):

    def __init__(self, status: int, message: str):
        super().__init__(status, str(message))


class ErrorHandler:
    def __ror__(self, other: dict):
        return other | {
            'error_page.default': self
        }

    def __call__(self, status=None, message=None, version=None, traceback=None):
        short_status = status[:3]
        f = getattr(self, 'status_' + short_status, self.status_default)
        return f(status, message, version, traceback)

    def status_default(self, status=None, message=None, version=None, traceback=None):
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        return (str(status) + '(' + str(message) + ')').encode('utf-8')


class HTMLErrorHandler(ErrorHandler):

    def status_default(self, status=None, message=None, version=None, traceback=None):
        req = cherrypy.request
        error = tw.dedent(f"""
        # Sorry {(req.login or 'guest').title()}, something went wrong 

        {datetime.datetime.now().isoformat()} 
        
        - url: {cherrypy.url()}
        - status: {status} 
        - message: {message}
        - request: `{req.request_line}`

        """).strip()
        if is_member(Level.admin):
            text = '\n```\n' + traceback + '\n```\n'
        else:
            text = ''
        return to_html(error=error, text=text)

    def status_500(self, status=None, message=None, version=None, traceback=None):
        req = cherrypy.request
        error = tw.dedent(f"""
        # Sorry {(req.login or 'guest').title()}, something went wrong 

        {datetime.datetime.now().isoformat()} 

        - url: {cherrypy.url()}
        - status: {status} 
        - message: {message}
        - request: `{req.request_line}`

        """).strip()
        if is_member(Level.admin):
            text = '\n```\n' + traceback + '\n```\n'
        else:
            text = '####' +  traceback.strip().split('\n')[-1]
        return to_html(error=error, text=text)

    def status_404(self, status=None, message=None, version=None, traceback=None):

        req = cherrypy.request
        error = tw.dedent(f"""
        # {message}
        
        {cherrypy.url()} 

        {datetime.datetime.now().isoformat()} 
        
        Status: {status} 
        
        {req.request_line}

        """).strip()
        return to_html(info=error)


class JSONErrorHandler(ErrorHandler):
    def status_default(self, status=None, message=None, version=None, traceback=None):
        from . import json_out
        req = cherrypy.request
        if is_member(Level.admin):
            return json_out(
                status=status,
                message=message,
                version=version,
                request=req.request_line,
                traceback=traceback
            )
        else:
            return json_out(
                status=status,
                message=message,
                version=version,
                request=req.request_line
            )


class errorhandler:
    json = JSONErrorHandler()
    html = HTMLErrorHandler()

