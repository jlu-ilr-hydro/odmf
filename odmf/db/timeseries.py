import sqlalchemy as sql
import sqlalchemy.orm as orm
from datetime import datetime, timedelta
import typing
import numpy as np
import pandas as pd
from dataclasses import dataclass
from .base import Base, newid
from .dataset import Dataset

from logging import getLogger

from .message import Topic

logger = getLogger(__name__)


class MemRecord(object):
    def __init__(self, id, dataset, time, value, sample=None, comment=None, is_error=False, rawvalue=None):
        self.id = id
        self.dataset = dataset
        self.time = time
        self.value = value
        self.sample = sample
        self.comment = comment
        self.is_error = is_error
        self.rawvalue = rawvalue


class Record(Base):
    """
    The record holds single measured, quantitative values.

    Database fields:
    id: numeric identifier, new counting for each dataset
    dataset: the owning dataset
    time: the time of the measurement
    value: the value of the measurement
    sample: if the value is from a taken sample, this item can hold the label of the sample
    comment: any additional information
    is_error: if True, the record is marked as error and is not used for analysis
    """
    __tablename__ = 'record'
    id = sql.Column(sql.Integer, primary_key=True)
    _dataset = sql.Column("dataset", sql.Integer,
                          sql.ForeignKey('dataset.id'), primary_key=True)
    dataset = orm.relationship("Timeseries", backref=orm.backref(
        'records', lazy='dynamic'), lazy='joined')
    time = sql.Column(sql.DateTime)
    value = sql.Column(sql.Float)
    sample = sql.Column(sql.String)
    comment = sql.Column(sql.String)
    is_error = sql.Column(sql.Boolean, nullable=False, default=False)

    # CensorCode is from the CUAHSI ODM 1.1 and describes values that are not precisly measured
    # see http://his.cuahsi.org/mastercvreg/cv11.aspx
    # nc is not censored
    censorcode = 'nc'

    __table_args__ = (
        sql.Index('record-dataset-time-index', 'dataset', 'time'),
        sql.Index('record-dataset-index', 'dataset')
    )

    @property
    def calibrated(self):
        """Returns the calibrated value"""
        if self.value is not None:
            return self.dataset.calibration_slope * self.value + self.dataset.calibration_offset
        else:
            return None

    def __str__(self):
        return f'{self.dataset.name}[{self.id}] = {self.value} {self.dataset.valuetype.unit}'

    @classmethod
    def query(cls, session):
        return session.query(cls).select_from(Timeseries).join(Timeseries.records)

    def __jdict__(self):
        return dict(id=self.id,
                    dataset=self.dataset.id,
                    time=self.time,
                    value=self.value,
                    sample=self.sample,
                    comment=self.comment)


class Timeseries(Dataset):
    __mapper_args__ = dict(polymorphic_identity='timeseries')
    # records: orm.Query

    def split(self, time):
        """Creates a new dataset using copy and assignes all records after
        time to the new dataset. Useful """
        session = self.session()
        next = self.records.filter(
            Record.time >= time, Record.value.isnot(None)).order_by(Record.time).first()
        last = self.records.filter(Record.time <= time, Record.value.isnot(None)).order_by(
            sql.desc(Record.time)).first()
        if not next or not last:
            raise RuntimeError(
                f'Split time {time} is not between two records of {self}')
        self.comment = f'{self.comment} Dataset is splitted at {time} to allow for different calibration'
        dsnew = self.copy(id=newid(Dataset, session))
        self.comment += f'. Other part of the dataset is ds{dsnew.id}\n'
        dsnew.comment += f'. Other part of the dataset is ds{self.id}\n'
        self.end = last.time
        dsnew.start = next.time
        records = self.records.filter(Record.time >= next.time)

        # updates records with orm reference
        for record in records:
            record.dataset = dsnew

        session.commit()
        return self, dsnew


    def statistics(self):
        """
        Return simple statistical description of the timeseries
        :return: mean, stddev, n
        """
        try:  # Try to use sql functions
            f = sql.sql.func
            rv = Record.value
            q = self.session().query(
                f.avg(rv), f.stddev_samp(rv), f.count(rv)
            ).filter_by(_dataset=self.id)
            avg, std, n = q.first()
            avg = avg or 0.0
            std = std or 0.0
            return (
                avg * self.calibration_slope + self.calibration_offset,
                std * self.calibration_slope,
                n
            )

        except (sql.exc.ProgrammingError, sql.exc.OperationalError):
            s = self.asseries()
            if len(s) == 0:
                return 0.0, 0.0, 0
            else:
                return np.mean(s), np.std(s), len(s)

    def findjumps(self, threshold, start=None, end=None):
        """Returns an iterator to find all jumps greater than threshold

        To find "jumps", the records of the dataset are scanned for differences
        between records (ordered by time). If the difference is greater than threshold,
        the later record is returned as a jump
        """
        records = self.records.order_by(Record.time).filter(Record.value.isnot(None), ~Record.is_error).filter(
            Record.time >= (start or self.start)).filter(Record.time <= (end or self.end))
        last = None
        for rec in records:
            if rec.value is not None:
                if threshold == 0.0 or (last and abs(rec.value - last.value) > threshold):
                    yield rec
                last = rec

    def findvalue(self, time):
        """Finds the linear interpolated value for the given time in the record"""
        next = self.records.filter(
            Record.time >= time, Record.value.isnot(None), ~Record.is_error).order_by(Record.time).first()
        last = self.records.filter(
            Record.time <= time, Record.value.isnot(None), ~Record.is_error).order_by(sql.desc(Record.time)).first()
        if next and last:
            dt_next = (next.time - time).total_seconds()
            dt_last = (time - last.time).total_seconds()
            dt = dt_next + dt_last
            if dt < 0.1:
                return next.value, 0.0
            else:
                return (1 - dt_next / dt) * next.value + (1 - dt_last / dt) * last.value, min(dt_last, dt_next)
        elif next:
            return next.value, (next.time - time).total_seconds()
        elif last:
            return last.value, (time - last.time).total_seconds()
        else:
            raise RuntimeError(f'{self} has no records')

    def calibratevalue(self, value):
        """Calibrates a value
        """
        try:
            return value * self.calibration_slope + self.calibration_offset
        except TypeError:
            return None

    def maxrecordid(self):
        """Finds the highest record id for this dataset"""

        # Heavily optimized code for large record tables and an asc-Index of id for the record table
        # See issue #99
        #
        size = self.size()
        sess = self.session()

        # query = self.records.order_by(Record.id).offset(size - 1)
        if size:
            query = sess.query(Record.id).filter_by(_dataset=self.id).order_by(Record.id).offset(size - 1)
            max_id = query.scalar()
            return max_id or 0
        else:
            return 0

    def addrecord(self, Id=None, value=None, time=None, comment=None, sample=None, out_of_timescope_ok=False):
        """Adds a record to the dataset
        Id: id for the recordset, if None, a new id will be created
        value: value of the record
        time: time of the record
        comment: comments for this new record
        """
        value = float(value)
        session = self.session()

        if time is None:
            time = datetime.now()
        Id = Id or self.maxrecordid() + 1

        if (not self.valuetype.inrange(value)):
            raise ValueError(f'RECORD does not fit VALUETYPE: {value:g} {self.valuetype.unit} is out of '
                             f'range for {self.valuetype.name}')

        # Check and adjust the timescope of the dataset
        if out_of_timescope_ok or None in (self.start, self.end):

            self.start = min(self.start or time, time)
            self.end = max(self.end or time, time)

        elif not(self.start <= time <= self.end):
            raise ValueError(
                f'RECORD does not fit DATASET: You tried to insert a record for date {time} '
                f'to dataset {self}, which allows only records between {self.start} and {self.end}'
            )

        result = Record(id=Id, time=time, value=value, dataset=self,
                        comment=comment, sample=sample)
        session.add(result)
        return result

    def adjusttimespan(self):
        """
        Adjusts the start and end properties to match the timespan of the records
        """
        Q = self.session().query
        self.start = min(Q(sql.func.min(Record.time)).filter_by(_dataset=self.id).scalar(), self.start)
        self.end = max(Q(sql.func.max(Record.time)).filter_by(_dataset=self.id).scalar(), self.end)

    def size(self):
        return self.records.count()

    def iterrecords(self, witherrors=False, start=None, end=None):
        session = self.session()
        records = session.query(Record).filter(
            Record._dataset == self.id).order_by(Record.time)
        if start:
            records = records.filter(Record.time >= start)
        if end:
            records = records.filter(Record.time <= end)
        records = records.order_by(Record.time)
        if not witherrors:
            records = records.filter(~Record.is_error)
        for r in records:
            yield MemRecord(id=r.id, dataset=r.dataset,
                            time=r.time, value=r.calibrated,
                            sample=r.sample, comment=r.comment,
                            rawvalue=r.value, is_error=r.is_error)

    def asseries(self, start: typing.Optional[datetime] = None, end: typing.Optional[datetime] = None, with_errors=False)->pd.Series:
        """
        Returns a pandas series of the calibrated non-error
        :param start: A start time for the series
        :param end: An end time for the series
        """
        query = self.session().query
        records = query(Record.time, Record.value).filter_by(_dataset=self.id)
        if not with_errors:
            records = records.filter(~Record.is_error)
        if start:
            records = records.filter(Record.time >= start)
        if end:
            records = records.filter(Record.time <= end)

        # Load data from database into dataframe and get the value-Series
        values = pd.read_sql(records.statement, self.session().bind, index_col='time')['value']

        # If no data is present, ensure the right dtype for the empty series
        if values.empty:
            return pd.Series([], index=pd.to_datetime([]), dtype=float)

        # Sort by time ascending
        values.sort_index(inplace=True)
        # Do calibration
        values *= self.calibration_slope
        values += self.calibration_offset
        return values



class DatasetAlarm(Base):
    """
    A dataset alarm is triggered if the aggregate values of a datasets are above or below a threshold.

    Allowed aggregation funcions: count, mean, max, min, std, sum  (see https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.agg.html)

    Examples:
    Check if dataset 1 receives at least 5 values in the last hour, repeat this message daily:

        DatasetAlarm(dsid=1, aggregation_time=1/24, aggregation_function='count', threshold_below=5, message_repeat_time=1, topic='ds:1')

    Check for frost in dataset 2 hourly, repeat daily

        DatasetAlarm(dsid=2, aggregation_time=1/24, aggregation_function='min', threshold_below=0, message_repeat_time=1, topic='ds:2')

    Check for overheat (mean over 30 degC in 3 hours) in dataset 2, repeat weekly

        DatasetAlarm(dsid=2, aggregation_time=3/24, aggregation_function='mean', threshold_above=30, message_repeat_time=7, topic='ds:2')

    Parameters:
    - dsid: id of timeseries
    - dataset: the dataset
    - active: Flag to activate alarm
    - aggregation_time: time span of aggregation in days
    - aggregation_function: aggregation function, one of count, mean, max, min, std, sum
    - threshold_below: raise alarm if aggregated value is below this threshold
    - threshold_above: raise alarm if aggregated value is above this threshold
    - message_repeat_time: number of days between messages
    - topic: topic of alarm
    - use_now: Flag if the aggregetion time ends at time of the calling or at the end of the dataset (default=True)

    """
    __tablename__ = 'datasetalarm'
    id: orm.Mapped[int] = sql.Column(sql.Integer, primary_key=True)
    dsid: orm.Mapped[int] = sql.Column(sql.ForeignKey('dataset.id'))
    dataset: orm.Mapped[Dataset] = orm.relationship('Dataset')
    active: orm.Mapped[bool] = sql.Column(sql.Boolean, default=True)
    aggregation_time: orm.Mapped[float] = sql.Column(sql.Float, default=1.0)
    aggregation_function: orm.Mapped[str] = sql.Column(sql.String, default='count')
    threshold_below: orm.Mapped[typing.Optional[float]]
    threshold_above: orm.Mapped[typing.Optional[float]]
    _topic: orm.Mapped[int] = sql.Column(sql.Integer, sql.ForeignKey('topic.id'))
    topic: orm.Mapped[Topic] = orm.relationship('Topic')
    message_repeat_time: orm.Mapped[float] = sql.Column(sql.Float, default=1.0)
    use_now: orm.Mapped[bool] = sql.Column(sql.Boolean, default=True)

    def msg_source(self):
        return f'ds:{self.dsid}'

    def to_string(self, value=None):
        agg_time = timedelta(days=self.aggregation_time)
        msg = f'{self.aggregation_function}(ds:{self.dsid} last {agg_time}h)'
        if value is not None:
            msg += f' = {value:0.4g} {self.dataset.valuetype.unit}'
        if self.threshold_below is not None:
            msg += f'< {self.threshold_below} {self.dataset.valuetype.unit}'
        if self.threshold_above is not None:
            msg += f'> {self.threshold_above} {self.dataset.valuetype.unit}'
        return msg + ' ==> ' + str(self.topic)

    def __str__(self):
        return self.to_string()

    def check(self) -> typing.Optional[str]:
        """
        Check if the conditions aggregation_time days before endtime (default=now) until endtime are above or below
        the thresholds. Uses the aggregation_function
        :return:
        """
        if not self.active:
            return None
        if self.use_now:
            now = datetime.now()
        else:
            now = self.dataset.end
        start = now - timedelta(days=self.aggregation_time)
        value = float(self.dataset.asseries(start, now).agg(self.aggregation_function))
        msg = f'{self.aggregation_function}(ds:{self.dsid} last {self.aggregation_time:0.3g} days)'

        if value is None:
            return None
        elif self.threshold_below is not None and value < self.threshold_below:
            return msg + f'< {self.threshold_below} {self.dataset.valuetype.unit}'
        elif self.threshold_above is not None and value > self.threshold_above:
            return msg + f'> {self.threshold_above} {self.dataset.valuetype.unit}'
        else:
            return None
