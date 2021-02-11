import cherrypy
from io import BytesIO
import os
import chardet
import datetime
import inspect
from traceback import format_exc as traceback
from contextlib import contextmanager

from . import lib as web
from .auth import users, expose_for, group, has_level, HTTPAuthError
from .. import db
from ..config import conf


def get_help(obj, url, append_to: dict = None):
    append_to = append_to or {}

    def is_api_or_method(obj):
        return inspect.ismethod(obj) or isinstance(obj, BaseAPI) and hasattr(obj, 'exposed')

    if inspect.ismethod(obj):
        append_to[url] = url.split('/')[-1] + str(inspect.signature(obj)) + ': ' + str(inspect.getdoc(obj))
    else:
        append_to[url] = inspect.getdoc(obj)
    for name, member in inspect.getmembers(obj, is_api_or_method):
        if not name.startswith('_'):
            append_to = get_help(member, '/'.join([url, name]), append_to)
    return append_to


def write_to_file(dest, src):
    """
    Write data of src (file in) into location of dest (filename)

    :param dest:  filename on the server system
    :param src: file contents input buffer
    :return:
    """

    with open(os.open(dest, os.O_CREAT | os.O_WRONLY, 0o770), 'w') as fout:
        while True:
            data = src.read(8192)
            if not data:
                break
            fout.write(data)


class BaseAPI:
    ...


@cherrypy.popargs('dsid')
class DatasetAPI(BaseAPI):
    """
    Provides an REST API to datasets

    Usages:

    :/api/dataset: Returns a list of existing dataset ids
    :/api/dataset/1: Returns the dataset metadata as json of ds1
    :/api/dataset/new: Creates a new dataset using POST or PUT data.
    :/api/dataset/addrecord: Adds a record to a dataset using PUT data
                             in the form ``{dsid: 1, value:2.0, time:2019-05-03T12:02}``

    """
    exposed = True
    url = conf.root_url + '/api/dataset'

    @staticmethod
    def parse_id(dsid: str) -> int:
        if dsid[:2] != 'ds':
            raise cherrypy.HTTPError(404, f'Dataset id does not start with ds. Got {dsid}')
        try:
            return int(dsid[2:])
        except (TypeError, ValueError):
            raise cherrypy.HTTPError(404, f'Last part of dataset id is not a number. Got {dsid}')

    @staticmethod
    @contextmanager
    def get_dataset(dsid: str, check_access=True) -> db.Dataset:
        dsid = DatasetAPI.parse_id(dsid)
        with db.session_scope() as session:
            ds = session.query(db.Dataset).get(dsid)
            if not ds:
                raise cherrypy.HTTPError(404, f'ds{dsid} does not exist')
            elif check_access and not has_level(ds.access):
                raise cherrypy.HTTPError(403, f'ds{dsid} is protected. Need a higher access level')
            else:
                yield ds


    @expose_for(group.guest)
    @web.method.get
    @web.mime.json
    def index(self, dsid=None):
        """
        Returns a json representation of a datasetid
        :param dsid: The Dataset id
        :return: json representation of the dataset metadata
        """

        if dsid is None:
            res = get_help(self, self.url)
            res[f'{self.url}/[n]'] = f"A dataset with the id [n]. See {self.url}/list method"
            return web.json_out(res)
        with self.get_dataset(dsid, False) as ds:
            return web.json_out(ds)

    @expose_for(group.guest)
    @web.mime.json
    def records(self, dsid, start=None, end=None):
        """
        :param dsid:
        :param start:
        :param end:
        :return:
        """
        with self.get_dataset(dsid, False) as ds:
            return web.json_out(ds.records.all())




    @expose_for()
    @web.method.get
    @web.mime.json
    def list(self):
        """
        Returns a JSON list of all available dataset url's
        """
        res = []
        with db.session_scope() as session:
            return web.json_out([
                f'{self.url}/ds{ds}'
                for ds, in sorted(session.query(db.Dataset.id))
            ])


    @expose_for(group.editor)
    @web.method.post_or_put
    @web.json_in()
    def new(self):
        """
        Creates a new dataset. Possible data fields:
        measured_by, valuetype, quality, site, source, filename,
        name, comment, project, timezone, level, etc.

        """

        kwargs = cherrypy.request.json
        with db.session_scope() as session:
            try:
                pers = session.query(db.Person).get(kwargs.get('measured_by'))
                vt = session.query(db.ValueType).get(kwargs.get('valuetype'))
                q = session.query(db.Quality).get(kwargs.get('quality'))
                s = session.query(db.Site).get(kwargs.get('site'))
                src = session.query(db.Datasource).get(kwargs.get('source'))

                ds = db.Timeseries()
                # Get properties from the keyword arguments kwargs
                ds.site = s
                ds.filename = kwargs.get('filename')
                ds.name = kwargs.get('name')
                ds.comment = kwargs.get('comment')
                ds.measured_by = pers
                ds.valuetype = vt
                ds.quality = q

                if kwargs.get('project') == '0':
                    ds.project = None
                else:
                    ds.project = kwargs.get('project')

                ds.timezone = kwargs.get('timezone')

                if src:
                    ds.source = src
                if 'level' in kwargs:
                    ds.level = web.conv(float, kwargs.get('level'))
                # Timeseries only arguments
                if ds.is_timeseries():
                    if kwargs.get('start'):
                        ds.start = datetime.datetime.strptime(
                            kwargs['start'], '%d.%m.%Y')
                    if kwargs.get('end'):
                        ds.end = datetime.datetime.strptime(kwargs['end'], '%d.%m.%Y')
                    ds.calibration_offset = web.conv(
                        float, kwargs.get('calibration_offset'), 0.0)
                    ds.calibration_slope = web.conv(
                        float, kwargs.get('calibration_slope'), 1.0)
                    ds.access = web.conv(int, kwargs.get('access'), 1)
                # Transformation only arguments
                if ds.is_transformed():
                    ds.expression = kwargs.get('expression')
                    ds.latex = kwargs.get('latex')
                # Save changes
                session.commit()
                return f'ds{ds.id}'

            except:
                # On error render the error message
                raise cherrypy.HTTPError(400, traceback())

    @expose_for(group.editor)
    @web.method.post_or_put
    def addrecord(self, dsid, value, time,
                       sample=None, comment=None, recid=None):
        """
        Adds a single record to a dataset

        JQuery usage: $.put('/api/dataset/addrecord', {dsid=1000, value=1.5, time='2019-02-01T17:00:00'}, ...);

        :param dsid: Dataset id
        :param value: Value to add
        :param time: Time of measurement
        :param sample: A link to a sample name (if present)
        :param comment: A comment about the measurement (if needed)
        :param recid: A record id (will be created if missing)
        :return: The id of the new record
        """
        time = web.parsedate(time)
        with db.session_scope() as session:
            try:
                dsid = self.parse_id(dsid)
                ds = session.query(db.Timeseries).get(dsid)
                if not ds:
                    return 'Timeseries ds:{} does not exist'.format(dsid)
                new_rec = ds.addrecord(Id=recid, time=time, value=value, comment=comment, sample=sample)
                return str(new_rec.id)
            except:
                raise cherrypy.HTTPError(400, 'Could not add record, error:\n' + traceback())

    @web.json_in()
    @expose_for(group.guest)
    @web.method.post_or_put
    def addrecords(self):
        """
        Adds a couple of records from a larger JSON list
        JQuery usage:
            $.put('/api/dataset/addrecord',
                  [{dsid=1000, value=1.5, time='2019-02-01T17:00:00'},
                   {dsid=1000, value=2.5, time='2019-02-01T17:00:05'},
                   ...
                  ], ...);
        :return:
        """
        data = cherrypy.request.json
        if not type(data) is list:
            data = [data]
        warnings = []
        with db.session_scope() as session:
            dataset = None
            for rec in data:
                dsid = rec.get('dsid') or rec.get('dataset') or rec.get('dataset_id')
                if not dsid:
                    warnings.append(f'{rec} does not reference a valid dataset '
                                    f'(allowed keywords are dsid, dataset and dataset_id)')
                if not dataset or dataset.id != dsid:
                    # load dataset from db
                    dataset = session.query(db.Dataset).get(dsid)
                else:
                    ...  # reuse last dataset
                if not dataset:
                    warnings.append(f'ds{dsid} does not exist')
                # get value, time, sample, comment and recid

    @expose_for()
    @web.method.get
    @web.mime.json
    def statistics(self, dsid):
        """
        Returns a json object holding the statistics for the dataset
        (is loaded by page using ajax)
        """
        with self.get_dataset(dsid, False) as ds:
            # Get statistics
            mean, std, n = ds.statistics()
            if not n:
                mean = 0.0
                std = 0.0
            # Convert to json
            return web.json_out(dict(mean=mean, std=std, n=n))


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
        Uploads a file to the file server
        :param path: The path of the directory, where this file should be stored
        :param datafile: the file to upload
        :param overwrite: If True, an existing file will be overwritten. Else an error is raised
        :return: 200 OK / 400 Traceback
        """
        errors = []
        fn = ''
        if datafile:
            path = conf.abspath('datafiles') / path
            if not path:
                path.make()
            fn = path + datafile.filename
            if not fn.islegal:
                raise cherrypy.HTTPError(400, f"'{fn}' is not legal")
            if fn and not overwrite:
                raise cherrypy.HTTPError(400, f"'{fn}' exists already and overwrite is not allowed, set overwrite")

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
                    return cherrypy.HTTPError(400, traceback())

    @expose_for()
    @web.method.get
    @web.mime.json
    def index(self):
        """
        Returns a JSON object containing the description of the API
        """
        return web.json_out(get_help(self, '/api'))



