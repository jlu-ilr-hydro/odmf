import io
import typing

import cherrypy
import datetime
from traceback import format_exc as traceback
from contextlib import contextmanager

import pandas as pd

from .. import lib as web
from ..auth import users, expose_for, group, has_level
from ... import db
from ...config import conf
from . import BaseAPI, get_help


"""
!!!!NOTE!!!!

Do not use mime decorators in the API, use web.mime.json.set() instead
"""


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
        try:
            return int(dsid)
        except ValueError:
            if dsid[:2] != 'ds':
                raise web.APIError(404, f'Dataset id does not start with ds. Got {dsid}')
            try:
                return int(dsid[2:])
            except (TypeError, ValueError):
                raise web.APIError(404, f'Last part of dataset id is not a number. Got {dsid}')

    @staticmethod
    @contextmanager
    def get_dataset(dsid: str, check_access=True) -> db.Dataset:
        dsid = DatasetAPI.parse_id(dsid)
        with db.session_scope() as session:
            ds = session.query(db.Dataset).get(dsid)
            if not ds:
                raise web.APIError(404, f'ds{dsid} does not exist')
            elif check_access and not has_level(ds.access):
                raise web.APIError(403, f'ds{dsid} is protected. Need a higher access level')
            else:
                yield ds


    @expose_for(group.guest)
    @web.method.get
    def index(self, dsid=None):
        """
        Returns a json representation of a datasetid
        :param dsid: The Dataset id
        :return: json representation of the dataset metadata
        """
        web.mime.json.set()
        if dsid is None:
            res = get_help(self, self.url)
            res[f'{self.url}/[n]'] = f"A dataset with the id [n]. See {self.url}/list method"
            return web.json_out(res)
        with self.get_dataset(dsid, False) as ds:
            return web.json_out(ds)

    @expose_for(group.guest)
    @web.mime.json
    def records(self, dsid):
        """
        Returns all records (uncalibrated) for a dataset as json
        """
        with self.get_dataset(dsid) as ds:
            return web.json_out(ds.records.all())

    @expose_for(group.guest)
    def values(self, dsid, start=None, end=None):
        """
        NOT TESTED! Returns the calibrated values for a dataset
        :param dsid: The dataset id
        :param start: A start time
        :param end: an end time
        :return: JSON list of time/value pairs
        """
        web.mime.json.set()
        start = web.parsedate(start, False)
        end = web.parsedate(end, False)
        with self.get_dataset(dsid) as ds:
            series = ds.asseries(start, end)
            return series.to_json().encode('utf-8')

    @expose_for(group.guest)
    @web.method.get
    def values_parquet(self, dsid, start=None, end=None):
        """
        Returns the calibrated values for a dataset
        :param dsid: The dataset id
        :param start: A start time to crop the data
        :param end: an end time to crop the data
        :return: parquet data stream, to be used by Python or R
        """
        web.mime.binary.set()
        start = web.parsedate(start, False)
        end = web.parsedate(end, False)
        with self.get_dataset(dsid) as ds:
            series: pd.Series = ds.asseries(start, end)
            df = pd.DataFrame({'value': series})
            df.reset_index(inplace=True)
            buf = io.BytesIO()
            df.to_parquet(buf)
            return buf.getvalue()


    @expose_for()
    @web.method.get
    def list(self):
        """
        Returns a JSON list of all available dataset url's
        """
        web.mime.json.set()
        with db.session_scope() as session:
            return web.json_out([
                f'{self.url}/ds{ds}'
                for ds, in sorted(session.query(db.Dataset.id))
            ])



    @expose_for(group.editor)
    @web.method.post_or_put
    def new(self, **kwargs):
        """
        Creates a new dataset. Possible data fields:
        measured_by, valuetype, quality, site, source, filename,
        name, comment, project, timezone, level, etc.

        """
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
                        ds.start = web.parsedate(
                            kwargs['start'])
                    if kwargs.get('end'):
                        ds.end =web.parsedate(kwargs['end'])
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
                cherrypy.response.status = 200
                return f'ds{ds.id}'.encode()

            except Exception as e:
                # On error render the error message
                raise web.APIError(400, 'Creating new timeseries failed') from e

    @expose_for(group.editor)
    @web.method.post_or_put
    def addrecord(self, dsid: int, value: float, time: str,
                       sample: str=None, comment: str=None, recid: int=None):
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
                return str(new_rec.id).encode('utf-8')
            except Exception as e:
                raise web.APIError(400, 'Could not add record') from e


    @expose_for(group.editor)
    @web.method.post_or_put
    def addrecords_parquet(self):
        """
        Expects a table in the apache arrow format to import records to existing datasets. Expected column names:
        dataset, id, time, value [,sample, comment, is_error]
        """
        web.mime.json.set()
        data = cherrypy.request.body.read()
        instream = io.BytesIO(data)
        # Load dataframe
        try:
            from ...tools.parquet_import import addrecords_parquet
            datasets, records = addrecords_parquet(instream)
        except Exception as e:
            raise web.APIError(400, 'Incoming data is not in the Apache Arrow format') from e

        return web.json_out(dict(status='success', datasets=list(datasets), records=records))


    @web.json_in()
    @expose_for(group.editor)
    @web.method.post_or_put
    def addrecords_json(self):
        """
        Adds a couple of records from a larger JSON list
        JQuery usage:
            $.put('/api/dataset/addrecord',
                  [{dsid=1000, value=1.5, time='2019-02-01T17:00:00'},
                   {dsid=1000, value=2.5, time='2019-02-01T17:00:05'},
                   ...
                  ], ...);
        """
        web.mime.json.set()
        data = cherrypy.request.json
        if not type(data) is list:
            data = [data]
        warnings = []
        datasets = set()
        records = 0
        with db.session_scope() as session:
            dataset: typing.Optional[db.Timeseries] = None
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
                value = web.conv(float, rec.get('value'))
                time = web.parsedate(rec.get('time'), False)
                if value is None:
                    warnings.append(f'{rec} has no valid value')
                if time is None:
                    warnings.append(f'{rec} has not a valid time')
                sample = rec.get('sample')
                comment = rec.get('comment')
                recid = rec.get('recid')
                if recid is None:
                    recid = dataset.maxrecordid() + 1
                record = db.Record(dataset=dataset, id=recid, value=value, time=time, sample=sample, comment=comment)
                session.add(record)
                records += 1
                datasets.add(dsid)
            if not warnings:
                session.commit()
                return web.json_out(dict(status='success', datasets=list(datasets), records=records))
            else:
                session.rollback()
                raise web.APIError(400, f'Cannot add records, got {len(warnings)} errors:\n\n' + '\n'.join(f'- {w}' for w in warnings))



    @expose_for()
    @web.method.get
    def statistics(self, dsid):
        """
        Returns a json object holding the statistics for the dataset
        (is loaded by page using ajax)
        """
        web.mime.json.set()
        with self.get_dataset(dsid, False) as ds:
            # Get statistics
            mean, std, n = ds.statistics()
            if not n:
                mean = 0.0
                std = 0.0
            # Convert to json
            return web.json_out(dict(mean=mean, std=std, n=n))

