"""
Serves static files
"""
import cherrypy

from cherrypy.lib.static import serve_file

from . import lib as web
from .auth import users
from ..config import conf
from pathlib import Path
from markdown import markdown
from .filemanager.file_auth import AccessFile


def filelist2html(files):
    text = '\n'.join(f'- [{f.name}]({f.name})' for f in files)
    return markdown(text)


@web.expose
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
        if home_dir.startswith('/'):
            self.homes = [Path(home_dir)]
        else:
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

    def get_path(self, rel_uri:str) -> Path:
        """
        Get pathlib Path object for URL
        Parameters
        ----------
        rel_uri
            Uri to find the mentioned path

        Returns
        -------
        Absolute pathlib.Path to the requested resources

        Raises
        ------
        HTTPError(403) on .. attacks and HTTPError(404) if the file does not exist
        """
        for home in [h.resolve() for h in reversed(self.homes)]:
            abs_path = (home / rel_uri).resolve()
            if abs_path.exists():
                # Check for .. attacks
                parents = list(abs_path.parents)
                if abs_path == home or home in parents:
                    return abs_path
                else:
                    raise web.HTTPError(403, 'Illegal path')
        raise web.HTTPError(404, 'Path not found')

    @web.expose
    @web.method.get
    def index(self, path='.', _=None):
        """
        Serves the static content from the relative path
        """
        p = self.get_path(path)
        f_acc = AccessFile(p)
        if not f_acc.check(users.current):
            raise web.HTTPError(403, f'Forbidden access to resource {p} for {users.current.name}')

        if p.is_file():
            return serve_file(str(p), name=p.name)

        elif self.listdir and p.is_dir():
            web.mime.html.set()
            return filelist2html(p.iterdir())
        else:
            raise web.HTTPError(404)

