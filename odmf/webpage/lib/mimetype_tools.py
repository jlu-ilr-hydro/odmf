"""
Tools to handle mimetypes
"""

import cherrypy


class mime:
    """
    Maps mimetypes from their typical file extension to the official mimetype

    Possible usage:
    >>>setmime(mime.jpeg)
    """
    json = 'application/json'
    css = 'text/css'
    plain = 'text/plain'
    xml = 'text/xml'
    html = 'text/html'
    jpg = 'image/jpeg'
    jpeg = 'image/jpeg'
    png = 'image/png'
    csv = 'text/comma-separated-values'
    pdf = 'application/pdf'
    xls = 'application/msexcel'
    xlsx = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    svg = 'image/svg+xml'
    tif = 'image/tiff'


def mimetype(content_type: str):
    """
    Decorator to set the mime type of the cherrypy response
    """
    def decorate(func):
        def wrapper(*args, **kwargs):
            cherrypy.response.headers['Content-Type'] = content_type
            return func(*args, **kwargs)

        return wrapper

    return decorate

def setmime(mime_type: str):
    cherrypy.response.headers['Content-Type'] = mime_type
