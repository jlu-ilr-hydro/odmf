"""
Serves static files
"""
import cherrypy
from .lib import expose, setmime, mime
from ..config import conf
from pathlib import Path
from markdown import markdown


def filelist2html(files):
    text = '\n'.join(f'- [{f.name}]({f.name})' for f in files)
    return markdown(text)




@expose
class StaticServer:

    def __init__(self, home_dir: str, listdir=False):
        self.homes = [
            (Path(static_home) / home_dir).absolute()
            for static_home in conf.static
            if (Path(static_home) / home_dir).exists()
        ]
        self.listdir = listdir

    def _cp_dispatch(self, vpath):
        p = Path('.')
        while vpath:
            p /= vpath.pop(0)
        cherrypy.request.params['path'] = p.as_posix()
        return self

    def get_path(self, path):
        for home in reversed(self.homes):
            if (home / path).exists():
                return home / path
        return None


    @expose
    def index(self, path='.'):
        p = self.get_path(path)

        if p is None:
            raise cherrypy.HTTPError(404)
        elif p.is_file():
            del cherrypy.response.headers['Content-Type']
            return p.read_bytes()
        elif self.listdir and p.is_dir():
            setmime(mime.html)
            return filelist2html(p.iterdir())
        else:
            raise cherrypy.HTTPError(404)





