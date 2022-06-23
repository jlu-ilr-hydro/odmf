"""
Tools to handle mimetypes
"""
import cherrypy
import mimetypes


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
    jpeg = jpg = jpe = MimeType('image/jpeg')
    png = MimeType('image/png')
    csv = MimeType('text/comma-separated-values')
    tsv = MimeType('text/tab-separated-values')
    pdf = MimeType('application/pdf')
    xls = MimeType('application/msexcel')
    xlsx = MimeType('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    svg = MimeType('image/svg+xml')
    tif = MimeType('image/tiff')
    kml = MimeType('application/vnd.google-earth.kml+xml')
    binary = MimeType('application/octet-stream')
    featherstream = MimeType('application/vnd.apache.arrow.stream')

    def __getitem__(self, item):
        if item[0] == '.':
            item = item[1:]
        try:
            return getattr(self, item)
        except AttributeError:
            t, e = mimetypes.guess_type('bla.' + item)
            if t:
                return MimeType(t)
            else:
                raise KeyError(f'mimetype "{item}" not found')

    def get(self, item, default=None):
        if item in self:
            return self[item]
        else:
            return default

    def __getattr__(self, item):
        t, e = mimetypes.guess_type('bla.' + item)
        if t:
            return MimeType(t)
        else:
            raise AttributeError(f'mimetype "{item}" not found')

    def __dir__(self):
        return [t[1:] for t in mimetypes.types_map]

    def __contains__(self, item):
        return hasattr(self, item)

    def set(self, item):
        try:
            mt =self[item]
            mt.set()
        except KeyError:
            del cherrypy.response.headers['Content-Type']


mime = Mime()

