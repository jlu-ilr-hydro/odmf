from odmf import webpage
from odmf.tools import server
import os
import sys
import cherrypy
import logging

PREFIX = os.path.dirname(os.path.abspath(__file__))

sys.stderr.write(PREFIX + '\n')
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
server.prepare_workdir()
root = webpage.Root()
application = cherrypy.Application(root, config=server.configure_app())

