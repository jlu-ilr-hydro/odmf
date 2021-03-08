
from traceback import format_exc as traceback
from cherrypy import HTTPError as _HTTPError

from logging import getLogger
from ..markdown import MarkDown
from .renderer import render

markdown = MarkDown()
logger = getLogger(__name__)



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
        self.message = message
        logger.warning(traceback())
        super().__init__(status, str(message))

    def get_error_page(self, *args, **kwargs):
        return markdown(self.message).encode('utf-8')


class HTTPError(_HTTPError):
    def __init__(self, status: int, message: str):
        self.message = message
        logger.warning(traceback())
        super().__init__(status, str(message))

    def get_error_page(self, *args, **kwargs):
        return render('empty.html', )