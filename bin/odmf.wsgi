

import os
import sys
import cherrypy
import logging

import odmf
odmf.prefix = os.path.dirname(os.path.abspath(__file__))
sys.stderr.write(odmf.prefix + '\n')
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
from odmf.tools import server
server.prepare_workdir()
from odmf import webpage
root = webpage.Root()
application = cherrypy.Application(root, config=server.configure_app())

