from odmf import webpage
from odmf.tools import server
import os
import cherrypy

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server.prepare_workdir()
    root = webpage.Root()
    application = cherrypy.Application(root, config=server.configure_app())

