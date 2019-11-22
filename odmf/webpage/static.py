"""
Serves static files
"""
import cherrypy
from .lib import expose, mime
from ..config import conf
from pathlib import Path
from markdown import markdown


def filelist2html(files):
    text = '\n'.join(f'- [{f.name}]({f.name})' for f in files)
    return markdown(text)


@expose
class StaticServer:
    """
    Serves static files, either from the user directory or the library directory
    """
    def __init__(self, home_dir: str, listdir=False):
        """
        Create a static page

        Parameters
        ----------
        home_dir
            The directory to start, should be a relative path
        listdir
            Indicates if this static page should list its content
        """
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
        """
        Serves the static content from the relative path
        """
        p = self.get_path(path)

        if p is None:
            raise cherrypy.HTTPError(404)
        elif p.is_file():
            mime.set(p.suffix)
            return p.read_bytes()
        elif self.listdir and p.is_dir():
            mime.html.set()
            return filelist2html(p.iterdir())
        else:
            raise cherrypy.HTTPError(404)





