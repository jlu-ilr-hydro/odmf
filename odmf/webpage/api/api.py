import cherrypy
from io import BytesIO
import os
import chardet
import inspect
from traceback import format_exc as traceback

from .. import lib as web
from ..auth import users, expose_for, group, has_level, HTTPAuthError
from ...config import conf
from . import BaseAPI, get_help, write_to_file
from .dataset_api import DatasetAPI


class API(BaseAPI):
    """
    A RESTful API for machine to machine communication using json
    """

    exposed = True
    dataset = DatasetAPI()

    @expose_for()
    @web.method.post
    @web.mime.plain
    def login(self, **data):
        """
        Login for the web app (including API)

        Usage with JQuery: $.post('/api/login',{username:'user', password:'secret'}, ...)
        Usage with python / requests: See tools/post_new_record.py

        returns Status 200 on success
        """
        if not data:
            req = cherrypy.request
            cl = req.headers['Content-Length']
            body = req.body.read(int(cl))
            data = dict(item.split('=') for item in body.decode('utf-8').split('&'))

        error = users.login(data['username'], data['password'])
        if error:
            cherrypy.response.status = 401
            return 'Username or password wrong'.encode('utf-8')
        else:
            cherrypy.response.status = 200
            return 'OK'.encode('utf-8')

    @expose_for(group.editor)
    @web.method.put
    def upload(self, path, datafile, overwrite=False):
        """
        !WARNING NOT TESTED, DO NOT USE! Uploads a file to the file server

        :param path: The path of the directory, where this file should be stored
        :param datafile: the file to upload
        :param overwrite: If True, an existing file will be overwritten. Else an error is raised
        :return: 200 OK / 400 Traceback
        """
        errors = []
        if datafile:
            path = conf.abspath('datafiles') / path
            if not path:
                path.make()
            fn = path + datafile.filename
            if not fn.islegal:
                raise web.APIError(400, f"'{fn}' is not legal")
            if fn and not overwrite:
                raise web.APIError(400, f"'{fn}' exists already and overwrite is not allowed, set overwrite")

            # Buffer file for first check encoding and secondly upload file
            with BytesIO(datafile.file.read()) as filebuffer:
                # determine file encodings
                result = chardet.detect(filebuffer.read())

                # Reset file buffer
                filebuffer.seek(0)

                # if chardet can determine file encoding, check it and warn respectively
                # otherwise state not detecting
                # TODO: chardet cannot determine sufficent amount of encodings, such as utf-16-le
                if result['encoding']:
                    file_encoding = result['encoding'].lower()
                    # TODO: outsource valid encodings
                    if not (file_encoding in ['utf-8', 'ascii'] or 'utf-8' in file_encoding):
                        errors.append("WARNING: encoding of file {} is {}".format(datafile.filename, file_encoding))
                else:
                    errors.append(f"WARNING: encoding of file {datafile.filename} is not detectable")
                try:
                    write_to_file(fn.absolute, filebuffer)
                    return ('\n'.join(errors)).encode('utf-8')
                except:
                    return web.APIError(400, traceback())

    @expose_for()
    @web.method.get
    @web.mime.json
    def index(self):
        """
        Returns a JSON object containing the description of the API
        """
        return web.json_out(get_help(self, '/api'))



