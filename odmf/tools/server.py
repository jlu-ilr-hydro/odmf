"""
Starts a cherrypy server
"""

from ..config import conf
import cherrypy
from logging import getLogger
import os
import sys
logger = getLogger(__name__)
server_config = {
    'tools.encode.encoding': 'utf-8',
    'tools.encode.on': True,
    'tools.encode.decode': True,
    'server.socket_host': '0.0.0.0',
    'log.access_file': './access.log',
    'log.error_file': './error.log',
}


def start(autoreload=False):
    """
    Creates the root object, compiles the server configuration and starts the server

    Parameters
    ----------
    autoreload: bool
        Set to True to enable autoreloading, that is the server starts again when files are changed

    """
    from ..webpage.root import Root
    root = Root()
    static_files = {
        '/favicon.ico': {"tools.staticfile.on": True,
                         "tools.staticfile.filename": str(conf.abspath("media/ilr-favicon.png"))
                         },
        '/html': {'tools.staticdir.on': True,
                  'tools.staticdir.dir': str(conf.abspath('templates')),
                  'tools.caching.on': False},
        '/media': {
            'tools.caching.on': True,
            'tools.caching.delay': 3600
        }
    }

    logger.info(f"autoreload = {autoreload}")
    cherrypy.config.update(server_config)
    cherrypy.config.update({
        'engine.autoreload.on': autoreload,
        'server.socket_port': conf.server_port,
    })

    logger.info(f'Starting server on http://127.0.0.1:{conf.server_port}')

    cherrypy.quickstart(root=root, config=static_files)


def prepare_workdir(workdir):
    """
    Starts a cherrypy server, with WORKDIR as the working directory (local ressources and configuration)
    """
    from glob import glob

    if sys.version_info[0] < 3:
        raise Exception("Must be using Python 3")

    # System checks !before project imports
    if conf:
        # Check for mandatory attributes
        logger.info("✔ Config is valid")
    else:
        logger.error("Error in config validation")
        exit(1)

    # Start with project imports
    lock_path = os.path.abspath('sessions')
    
    logger.debug('Ensure subdirectories')
    for d in ['media', 'sessions', 'preferences/plots']:
        os.makedirs(d, exist_ok=True)

    logger.debug(f"Kill session lock files in {lock_path}")
    for fn in glob(lock_path + '/*.lock'):
        logger.debug(f'Killing old session lock {fn}')
        os.remove(fn)
        
    

