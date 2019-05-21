import cherrypy
from io import BytesIO
from pathlib import Path
import chardet
import datetime
from traceback import format_exc as traceback

from . import lib as web
from .auth import users, expose_for, group
from .. import db


datapath = web.abspath('datafiles')
home = web.abspath('.')

def write_to_file(dest, src):
    """
    Write data of src (file in) into location of dest (filename)

    :param dest:  filename on the server system
    :param src: file contents input buffer
    :return:
    """

    fout = open(dest, 'wb')
    while True:
        data = src.read(8192)
        if not data:
            break
        fout.write(data)
    fout.close()


def respond(status=200, message='OK'):
    cherrypy.response.status = status
    return message


class DatasetAPI:
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

    @expose_for(group.guest)
    @web.method.get
    def index(self, dsid=None):
        """
        Returns a json representation of a datasetid
        :param dsid: The Dataset id
        :return: json representation of the dataset metadata
        """
        if dsid is None:
            with db.session_scope() as session:
                return web.as_json(session.query(db.Dataset.id).all())
        try:
            dsid = int(dsid)
        except (TypeError, ValueError):
            raise cherrypy.HTTPError(400, f'"{dsid}" is not a valid dataset number')

        with db.session_scope() as session:
            ds = session.query(db.Dataset).get(dsid)
            if not ds:
                raise cherrypy.HTTPError(404, f'ds{dsid} does not exist')
            else:
                return web.as_json(ds)


    @expose_for(group.editor)
    @web.method.post_or_put
    @web.json_in()
    def new(self):
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
                        ds.start = datetime.strptime(
                            kwargs['start'], '%d.%m.%Y')
                    if kwargs.get('end'):
                        ds.end = datetime.strptime(kwargs['end'], '%d.%m.%Y')
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
                return respond(200, f'ds{ds.id}')

            except:

                # On error render the error message
                return respond(400, traceback())

    @expose_for(group.editor)
    @web.method.post_or_put
    def addrecord(self, dsid, value, time,
                       sample=None, comment=None):
        time = web.parsedate(time)
        with db.session_scope() as session:
            try:
                ds = session.query(db.Timeseries).get(int(dsid))
                if not ds:
                    return 'Timeseries ds:{} does not exist'.format(dsid)
                new_rec = ds.addrecord(Id=int(recid), time=time, value=value, comment=comment, sample=sample)
                return respond(200, new_rec.id)
            except:
                return respond(400, 'Could not add record, error:\n' + traceback())

    @expose_for()
    @web.method.get
    def statistics(self, id):
        """
        Returns a json file holding the statistics for the dataset (is loaded by page using ajax)
        """
        web.setmime(web.mime.json)
        with db.session_scope() as session:
            ds = session.query(db.Dataset).get(int(id))
            if ds:
                # Get statistics
                mean, std, n = ds.statistics()
                # Convert to json
                return respond(200, web.as_json(dict(mean=mean, std=std, n=n)))
            else:
                # Return empty dataset statistics
                return respond(404, f'ds{id} does not exist')



class API:

    exposed = True
    dataset = DatasetAPI()

    @expose_for()
    @web.method.post
    def login(self, username, password):
        web.setmime(web.mime.plain)
        error = users.login(username, password)
        if error:
            return respond(401, 'Username or password incorrect')
        else:
            return respond(200, 'OK')

    @expose_for(group.editor)
    @web.mime.put()
    def upload(self, uri, datafile, overwrite=False):
        errors = []
        fn = ''
        if datafile:
            path = Path(datapath) / uri
            if not path:
                path.make()
            fn = path + datafile.filename
            if not fn.is_legal:
                return respond(400, f"'{fn}' is not legal")
            if fn and not overwrite:
                return respond(400, f"'{fn}' exists already and overwrite is not allowed, set overwrite")

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
                    fn.setownergroup()
                    return respond(200, '\n'.join(errors))
                except:
                    return respond(400, traceback())







