import cherrypy
from io import BytesIO

from .. import lib as web
from ..auth import users, expose_for, Level
from ...tools import Path as OPath
from ..lib.errors import errorhandler
from ...config import conf
from . import BaseAPI, get_help, write_to_file
from .dataset_api import DatasetAPI
from .site_api import SiteAPI


class API(BaseAPI):
    """
    A RESTful API for machine to machine communication using json
    """
    _cp_config = {} | errorhandler.json
    exposed = True
    dataset = DatasetAPI()
    site = SiteAPI()

    @expose_for()
    @web.method.post
    @web.mime.plain
    def login(self, **data):
        """
        Login for the web app (including API)

        Usage with JQuery: $.post('/api/login',{username:'user', password:'secret'}, ...)
        Usage with python / requests: See tools/apiclient.py

        returns Status 200 on success
        """
        if not data:
            req = cherrypy.request
            cl = req.headers['Content-Length']
            body = req.body.read(int(cl))
            data = dict(item.split('=') for item in body.decode('utf-8').split('&'))

        error = users.login(data['username'], data['password'])
        if error:
            web.mime.plain.set()
            cherrypy.response.status = 401
            return 'Username or password wrong'.encode('utf-8')
        else:
            cherrypy.response.status = 200
            web.mime.plain.set()
            return 'OK'.encode('utf-8')

    @expose_for()
    @web.method.post
    @web.mime.plain
    def logout(self):
        users.logout()
        return 'OK'.encode('utf-8')

    @expose_for(Level.editor)
    @web.method.put
    def upload(self, targetpath: str, overwrite: bool = False, append: bool = False):
        """
        Usage:
        >>>with odmfclient.login('https://localhost', 'admin', 'admin'):
        ...    api.upload(b'Some binary data...', '/path/to/file', overwrite=False, append=False)

        :param targetpath: The path of the directory, where this file should be stored
        :param datafile: the file to upload
        :param overwrite: If True, an existing file will be overwritten. Else an error is raised
        :param append: If True and targetpath exist, append to it
        :return: 200 OK / 400 Traceback
        """
        web.mime.plain.set()
        fn = OPath(targetpath)
        if not fn.islegal:
            raise web.APIError(400, f"'{fn}' is not legal")
        elif fn.exists() and not (overwrite or append):
            raise web.APIError(400, f"'{fn}' exists already and overwrite is not allowed, set overwrite")
        from pathlib import Path as PyPath
        data = cherrypy.request.body.read()
        if append and fn.exists():
            with fn.to_pythonpath().open('ab') as f:
                f.write(data)
        else:
            with fn.to_pythonpath().open('wb') as f:
                f.write(data)

        return 'OK'.encode('utf-8')


    @expose_for()
    @web.method.get
    @web.mime.json
    def index(self):
        """
        Returns a JSON object containing the description of the API
        """
        return web.json_out(dict([get_help(self, '/api')]))

