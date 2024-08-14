import sqlalchemy as sql
import sqlalchemy.orm as orm
from sqlalchemy.schema import ForeignKey
from .base import Base, newid
from .dataset import Dataset
from .timeseries import Timeseries, Record, MemRecord

import numpy as np
import pandas as pd
from asteval import Interpreter

from logging import getLogger
logger = getLogger(__name__)


class TransformedTimeseries(Dataset):
    __tablename__ = 'transformed_timeseries'
    __mapper_args__ = dict(polymorphic_identity='transformed_timeseries')
    id = sql.Column(sql.Integer, sql.ForeignKey(
        'dataset.id'), primary_key=True)
    expression = sql.Column(sql.String)
    latex = sql.Column(sql.String)

    # An asteval interpreter with minimal functionality
    interpreter = Interpreter(minimal=True, max_statement_length=300)

    def sourceids(self):
        return [s.id for s in self.sources]

    def size(self):
        return self.session().query(Record).filter(Record._dataset.in_(self.sourceids())).count()

    def asseries(self, start=None, end=None):
        datasets = self.sources
        data = []
        if self.expression.startswith('plugin.transformation'):
            # This is a plugin transformation
            # import transformation module
            pass
        else:
            for src in datasets:
                v = src.asseries(start, end)
                v = self.transform(v)
                data.append(v)

            data = pd.concat(data).sort_index()
        return data

    def updatetime(self):
        self.start = min(ds.start for ds in self.sources)
        self.end = max(ds.end for ds in self.sources)

    def transform(self, x: pd.Series):
        self.interpreter.symtable['x'] = x.to_numpy()
        result = self.interpreter(self.expression.strip())
        return pd.Series(result, index=x.index, name=str(self))

    def iterrecords(self, witherrors=False, start=None, end=None):
        session = self.session()
        srcrecords = session.query(Record).filter(
            Record._dataset.in_(self.sourceids())).order_by(Record.time)
        if start:
            srcrecords = srcrecords.filter(Record.time >= start)
        if end:
            srcrecords = srcrecords.filter(Record.time <= end)
        if not witherrors:
            srcrecords = srcrecords.filter(~Record.is_error)
        i = 0
        for r in srcrecords:
            i += 1
            yield MemRecord(id=i, dataset=r.dataset, time=r.time,
                            value=self.transform(r.calibrated),
                            sample=r.sample, comment=r.comment,
                            is_error=r.is_error)

    def suitablesources(self):
        session = self.session()
        sourceids = self.sourceids()
        res = session.query(Timeseries).filter(Timeseries.site == self.site,
                                               ~Timeseries.id.in_(sourceids),
                                               )
        if len(self.sources):
            vt = self.sources[0].valuetype
            res = res.filter(Timeseries.valuetype == vt)
        return res

    def statistics(self):
        s = self.asseries()
        if len(s) == 0:
            return 0.0, 0.0, 0
        else:
            return np.mean(s), np.std(s), len(s)


transforms_table = sql.Table(
    'transforms', Base.metadata,
    sql.Column('target', sql.Integer, ForeignKey(
        'transformed_timeseries.id'), primary_key=True),
    sql.Column('source', sql.Integer, ForeignKey('dataset.id'), primary_key=True)
)

# Moved relationship out of class definition to ensure, that the transforms_table table after
# transformed_timeseries to allow the foreign key constrains to work
TransformedTimeseries.sources = orm.relationship(
        "Timeseries", secondary=transforms_table, order_by="Timeseries.start")
