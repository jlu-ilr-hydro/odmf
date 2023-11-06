# -*- coding:utf-8 -*-
'''
Created on 13.07.2012

@author: philkraf
'''
import datetime

import sqlalchemy as sql
import sqlalchemy.orm as orm
import pytz
import pandas as pd

from .base import Base, Session
from ..config import conf
from typing import Optional
from logging import getLogger
logger = getLogger(__name__)

tzberlin = pytz.timezone('Europe/Berlin')
tzwinter = pytz.FixedOffset(60)
tzutc = pytz.utc


class Quality(Base):
    """Denotes the data quality of measurements, from raw to calibrated.
    id: numeric key to the dataquality
    name: Textual representation of the dataquality
    comment: Some additional description
    """
    __tablename__ = 'quality'
    id = sql.Column(sql.Integer, primary_key=True)
    name = sql.Column(sql.String)
    comment = sql.Column(sql.String)

    def __str__(self):
        return self.name

    def __jdict__(self):
        return dict(id=self.id,
                    name=self.name,
                    comment=self.comment)


class ValueType(Base):
    """The value type of datasets shows what is the measured value and unit,
    eg. temperature, Water depth, wind speed etc.
    """
    __tablename__ = 'valuetype'
    id = sql.Column(sql.Integer, primary_key=True)
    name = sql.Column(sql.String)
    unit = sql.Column(sql.String)
    comment = sql.Column(sql.String)
    minvalue = sql.Column(sql.Float)
    maxvalue = sql.Column(sql.Float)
    __mapper_args__ = {'order_by': name}

    def __str__(self):
        return f'{self.name} [{self.unit}] ({self.id})'

    def __eq__(self, other):
        return str(self.id).upper() == str(other).upper()

    def __lt__(self, other):
        return str(self.id).upper() < str(other.id).upper()

    def __hash__(self):
        return hash(str(self))

    def records(self):
        from .timeseries import Record
        session = Session.object_session(self)
        return Record.query(session).filter(Dataset.valuetype == self)

    def __jdict__(self):
        return dict(id=self.id,
                    name=self.name,
                    unit=self.unit,
                    comment=self.comment)

    def inrange(self, value):
        return ((self.minvalue is None or value >= self.minvalue) and
                (self.maxvalue is None or value <= self.maxvalue))


class Dataset(Base):
    """The data set is the central object of the database. It contains metadata and semantics
    for set of records. The data set connects the single observations / measurements with
    the other objects of the databas, like place (site), value type, user etc.

    Dataset is the parent class for other types of datasets, namely Timeseries and TransformedTimeseries,
    possibly more in the future.

    It uses SQLAlchemy's single table inheritance mechanism
    https://docs.sqlalchemy.org/en/14/orm/inheritance.html#single-table-inheritance
    to extend the functionality or the joined table inheritance
     https://docs.sqlalchemy.org/en/14/orm/inheritance.html#joined-table-inheritance

    Datbase fields:
    id: numerical key to the dataset
    name: a short description of the content
    filename: a reference to an existing file in the download area
    start: The first date of the records in the dataset
    end: the date of the last record, or the expected end of the dataset
    site: the location of the dataset in space
    valuetype: the value type of the data set, eg. temperature, water depth etc.
    measured_by: responsible user for this dataset
    quality: the dat quality of the records, eg. raw, checked, calibrated
    source: The data source of the records, an instrument or an external data provider
    calibration_offset, calibration_slope: Values to apply an linear transformation of the records
    comment: Some more details for the dataset


    Backwards references:
    records: A query for records
    """
    __tablename__ = 'dataset'
    id = sql.Column(sql.Integer, primary_key=True)
    name = sql.Column(sql.String, nullable=True)
    filename = sql.Column(sql.String, nullable=True)
    start = sql.Column(sql.DateTime, nullable=True)
    end = sql.Column(sql.DateTime, nullable=True)
    _site = sql.Column("site", sql.Integer, sql.ForeignKey('site.id'))
    site = orm.relationship(
        "Site", primaryjoin='Site.id==Dataset._site', order_by='Site.id',
        backref=orm.backref('datasets', lazy='dynamic')
    )
    _valuetype = sql.Column("valuetype", sql.Integer, sql.ForeignKey('valuetype.id'))
    valuetype = orm.relationship("ValueType", backref='datasets')
    _measured_by = sql.Column(
        "measured_by", sql.String, sql.ForeignKey('person.username'))
    measured_by = orm.relationship("Person", backref='datasets', order_by='Person.username',
                                   primaryjoin="Person.username==Dataset._measured_by")
    _quality = sql.Column("quality", sql.Integer,
                          sql.ForeignKey('quality.id'), default=0)
    quality = orm.relationship("Quality")
    _source = sql.Column("source", sql.Integer, sql.ForeignKey(
        'datasource.id'), nullable=True)
    source = orm.relationship("Datasource", backref="datasets")
    calibration_offset = sql.Column(sql.Float, nullable=False, default=0.0)
    calibration_slope = sql.Column(sql.Float, nullable=False, default=1.0)
    comment = sql.Column(sql.String)
    type = sql.Column(sql.String)
    level = sql.Column(sql.Float)
    # TODO: Remove uses_dst
    uses_dst = sql.Column(sql.Boolean, default=False, nullable=False)
    __mapper_args__ = dict(polymorphic_identity=None,
                           polymorphic_on=type)
    access = sql.Column(sql.Integer, default=1, nullable=False)

    timezone = sql.Column(sql.String,
                          default=conf.datetime_default_timezone)
    project = sql.Column(sql.Integer, sql.ForeignKey('project.id'),
                         nullable=True)

    def __str__(self):
        site = self.site.id if self.site else ''
        level = f'{self.level:g} m offset' if self.level is not None else ''
        return (f'ds{self.id or -999:04d}: {self.valuetype} at #{site} {level} with {self.source} '
                f'({self.start or "?"} - {self.end or "?"})').replace("'", r"\'")

    def __jdict__(self):
        return dict(id=self.id,
                    name=self.name,
                    filename=self.filename,
                    start=self.start,
                    end=self.end,
                    site=self.site,
                    valuetype=self.valuetype,
                    measured_by=self.measured_by,
                    quality=self.quality,
                    level=self.level,
                    comment=self.comment,
                    label=self.__str__(),
                    access=self.access)

    def is_timeseries(self):
        return self.type == 'timeseries'

    def is_transformed(self):
        return self.type == 'transformed_timeseries'

    def is_geodataset(self):
        return self.type == 'geodataset'

    @property
    def tzinfo(self):
        if False:
            if self.timezone in pytz.common_timezones:
                return pytz.timezone(self.timezone)
            elif self.timezone.startswith('Fixed/'):
                return pytz.FixedOffset(int(self.timezone.split('/')[1]))
            else:
                return pytz.utc
        else:
            return tzberlin if self.uses_dst else tzwinter

    def localizetime(self, time):
        return self.tzinfo.localize(time)

    def copy(self, id: int):
        """Creates a new dataset without records with the same meta data as this dataset.
        Give a new (unused) id
        """
        cls = type(self)
        return cls(id=id,
                   name=self.name,
                   filename=self.filename,
                   valuetype=self.valuetype,
                   measured_by=self.measured_by,
                   quality=self.quality,
                   source=self.source,
                   calibration_offset=self.calibration_offset,
                   calibration_slope=self.calibration_slope,
                   comment=self.comment,
                   start=self.start,
                   end=self.end,
                   site=self.site,
                   level=self.level,
                   type=self.type,
                   access=self.access,
                   project=self.project,
                   timezone=self.timezone)

    def size(self):
        return 0

    def statistics(self):
        """Calculates mean, stddev and number of records for this data set
        """
        return 0.0, 0.0, 0

    def iterrecords(self, witherrors=False):
        raise NotImplementedError(
            f'{self}(type={self.type}) - data set has no records to iterate. Is the type correct?'
        )

    @property
    def path(self):
        from ..tools import Path as OPath
        if self.filename:
            p = OPath(self.filename)
            if p.exists():
                return p
        return None

    @classmethod
    def filter(
            cls, session,
            valuetype: Optional[int]=None,
            user: Optional[str]=None,
            site: Optional[int]=None,
            date: Optional[datetime.datetime]=None,
            instrument: Optional[int]=None,
            type: Optional[str]=None,
            level: Optional[float]=None
    ) -> orm.Query:
        """
        Filters datasets for fitting properties
        """
        datasets: orm.Query = session.query(cls)
        if user:
            datasets = datasets.filter_by(_measured_by=user)
        if site and site != 'NaN':
            datasets = datasets.filter_by(_site=site)
        if date:
            datasets = datasets.filter(
                Dataset.start <= date,
                Dataset.end >= date
            )
        if valuetype:
            datasets = datasets.filter_by(_valuetype=valuetype)
        if instrument:
            datasets = datasets.filter_by(_source=instrument)
        if type:
            datasets = datasets.filter_by(type=type)
        if level is not None:
            datasets = datasets.filter_by(level=level)
        return datasets


def removedataset(*args):
    """Removes a dataset and its records entirely from the database
    !!Handle with care, there will be no more checking!!"""
    session = Session()
    datasets = [session.query(Dataset).get(int(a)) for a in args]
    for ds in datasets:
        dsid = ds.id
        if ds.is_timeseries():
            reccount = ds.records.delete()
            session.commit()
        else:
            reccount = 0
        session.delete(ds)
        session.commit()
        logger.info(f"Deleted ds{dsid:04i} and {reccount} records")


class DatasetGroup(object):
    def __init__(self, datasetids, start=None, end=None):
        self.datasetids = list(datasetids)
        self.start = start
        self.end = end

    def datasets(self, session):
        return session.query(Dataset).filter(Dataset.id.in_(self.datasetids)).order_by(Dataset.start).all()

    def asseries(self, session, name=None):
        datasets = self.datasets(session)
        data = pd.concat([
            src.asseries(self.start, self.end)
            for src in datasets
        ])
        data.name = name
        return data.sort_index()

    def iterrecords(self, session, witherrors):
        datasets = self.datasets(session)
        for ds in datasets:
            for r in ds.iterrecords(witherrors):
                yield r

