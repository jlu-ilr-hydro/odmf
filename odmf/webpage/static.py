"""
Serves static files
"""
import cherrypy
from .lib import expose, setmime, mime
from ..config import conf
from pathlib import Path
import json
import sys
from logging import getLogger
logger = getLogger(__name__)
from markdown import markdown

def static_location():
    candidates = Path(sys.prefix), Path(__file__).parents[2], Path(conf.static)

    for c in candidates:
        p = c / 'odmf.static'
        if p.exists():
            if all((p / d).exists() for d in ('templates', 'datafiles', 'media')):
                logger.info(f'odmf.static at {p}/[templates|datafiles|media]')
                return p
            else:
                logger.info(f'{p}, found but not all of templates|datafiles|media exist, searching further\n')
        else:
            logger.info(f'{p} - does not exist\n')

    raise FileNotFoundError('Did not find the odmf.static directory in the installation or local')


def filelist2html(files):
    text = '\n'.join(f'- [{f.name}]({f.name})' for f in files)
    return markdown(text)



class StaticServer:
    exposed = True

    def __init__(self, home: Path, listdir=False):
        self.home = Path(home).absolute()
        self.listdir = listdir

    def _cp_dispatch(self, vpath):
        p = Path('.')
        while vpath:
            p /= vpath.pop(0)
        cherrypy.request.params['path'] = p.as_posix()
        return self

    @expose
    def index(self, path='.'):
        p = self.home / path
        if p.is_file():
            del cherrypy.response.headers['Content-Type']
            return p.read_bytes()
        elif self.listdir and p.is_dir():
            setmime(mime.html)
            return filelist2html(p.iterdir())
        else:
            raise cherrypy.HTTPError(404, 'Unknown ressource')



