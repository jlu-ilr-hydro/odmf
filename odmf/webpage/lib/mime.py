"""
Tools to handle mimetypes
"""
import cherrypy

class MimeType:
    """
    Wraps a mimetype with functionality to decorate exposed methods
    or set the output mimetype in the code

    Usage as decorator
    ::
        @expose
        @mime.css
        def index(self, ...):
            ...

    Usage as string:
    ::
        print(mime.css)  # text/css

    Usage for file extension inside of an exposed method
    ::
        @expose
        def serve_file(filename):
            ext = filename.split('.')[-1]
            mime[ext].set()
    """
    def __init__(self, mimetype):
        self.mimetype = mimetype

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            cherrypy.response.headers['Content-Type'] = self.mimetype
            return func(*args, **kwargs)
        return wrapper

    def set(self):
        cherrypy.response.headers['Content-Type'] = self.mimetype

    def __repr__(self):
        return self.mimetype


class Mime:

    json = MimeType('application/json')
    css = MimeType('text/css')
    plain = MimeType('text/plain')
    xml = MimeType('text/xml')
    html = MimeType('text/html')
    jpg = MimeType('image/jpeg')
    jpeg = MimeType('image/jpeg')
    png = MimeType('image/png')
    csv = MimeType('text/comma-separated-values')
    pdf = MimeType('application/pdf')
    xls = MimeType('application/msexcel')
    xlsx = MimeType('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    svg = MimeType('image/svg+xml')
    tif = MimeType('image/tiff')
    kml = MimeType('application/vnd.google-earth.kml+xml')

    def __getitem__(self, item):
        if item[0] == '.':
            item = item[1:]
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(f'mimetype "{item}" not found')

    def __contains__(self, item):
        return hasattr(self, item)

    def set(self, item):
        try:
            mt =self[item]
            mt.set()
        except KeyError:
            del cherrypy.response.headers['Content-Type']


mime = Mime()

