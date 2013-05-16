# -*- coding:utf-8 -*-
'''
Created on 13.07.2012

@author: philkraf
'''
import sqlalchemy as sql
import sqlalchemy.orm as orm
from base import Base,Session, newid
from sqlalchemy.schema import ForeignKey
from datetime import datetime,timedelta
from dbobjects import newid, Person, Datasource
from collections import deque
from math import sqrt
import pytz
tzberlin = pytz.timezone('Europe/Berlin')
tzwinter = pytz.FixedOffset(60)
tzutc = pytz.utc
import numpy as np
class Quality(Base):
    """Denotes the data quality of measurements, from raw to calibrated.
    id: numeric key to the dataquality
    name: Textual representation of the dataquality
    comment: Some additional description        
    """
    __tablename__= 'quality'
    id=sql.Column(sql.Integer,primary_key=True)
    name=sql.Column(sql.String)
    comment=sql.Column(sql.String)
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
    __tablename__= 'valuetype'
    id=sql.Column(sql.Integer,primary_key=True)
    name=sql.Column(sql.String)
    unit=sql.Column(sql.String)
    comment=sql.Column(sql.String)
    minvalue=sql.Column(sql.Float)
    maxvalue=sql.Column(sql.Float)
    def __str__(self):
        return "%s [%s]" % (self.name,self.unit)
    def __cmp__(self,other):
        
        return cmp(self.__str__().upper(),other.__str__().upper())
    def records(self):
        session= Session.object_session(self)
        return Record.query(session).filter(Dataset.valuetype==self)
    def __jdict__(self):
        return dict(id=self.id,
                    name=self.name,
                    unit=self.unit,
                    comment=self.comment)
    def inrange(self,value):
        return ((self.minvalue is None or value>=self.minvalue)
            and (self.maxvalue is None or value<=self.maxvalue))

       
    

class Dataset(Base):
    """The data set is the central object of the database. It contains metadata and semantics
    for set of records. The data set connects the single observations / measurements with
    the other objects of the databas, like place (site), value type, user etc.
    
    Databse fields:
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
    __tablename__= 'dataset'
    id=sql.Column(sql.Integer,primary_key=True)
    name=sql.Column(sql.String, unique=True)
    filename=sql.Column(sql.String, nullable=True)
    start=sql.Column(sql.DateTime, nullable = True)
    end=sql.Column(sql.DateTime, nullable = True)
    _site=sql.Column("site",sql.Integer, sql.ForeignKey('site.id'))
    site = orm.relationship("Site",primaryjoin='Site.id==Dataset._site',
                            backref=orm.backref('datasets',lazy='dynamic',
                                                       #order_by="[Dataset.valuetype.name,sql.desc(Dataset.end)]"
                                                       ))
    _valuetype=sql.Column("valuetype",sql.Integer,sql.ForeignKey('valuetype.id'))
    valuetype = orm.relationship("ValueType",backref='datasets')
    _measured_by=sql.Column("measured_by",sql.String,sql.ForeignKey('person.username'))
    measured_by = orm.relationship("Person",backref='datasets',
                                   primaryjoin="Person.username==Dataset._measured_by")
    _quality=sql.Column("quality",sql.Integer,sql.ForeignKey('quality.id'),default=0)
    quality = orm.relationship("Quality")
    _source = sql.Column("source",sql.Integer,sql.ForeignKey('datasource.id'),nullable=True)
    source = orm.relationship("Datasource",backref="datasets")
    calibration_offset = sql.Column(sql.Float,nullable=False,default=0.0)
    calibration_slope = sql.Column(sql.Float,nullable=False,default=1.0)
    comment=sql.Column(sql.String)
    type=sql.Column(sql.String)
    uses_dst=sql.Column(sql.Boolean,default=False,nullable=False)
    __mapper_args__ = dict(polymorphic_identity=None,
                           polymorphic_on=type)

    def __str__(self):
        return (u'ds%(id)03i: %(valuetype)s at site #%(site)s with %(instrument)s (%(start)s-%(end)s)' % 
                dict(id=self.id,
                     start=self.start.strftime('%d.%m.%Y') if self.start else '?',
                     end=self.end.strftime('%d.%m.%Y') if self.end else '?',
                     site=self.site.id if self.site else '',
                     instrument=self.source if self.source else None,
                     valuetype=self.valuetype.name if self.valuetype else ''))
    
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
                    comment=self.comment,
                    label=self.__str__())

    def is_timeseries(self):
        return self.type=='timeseries'
    def is_transformed(self):
        return self.type=='transformed_timeseries'
    def is_geodataset(self):
        return self.type=='geodataset'
    @property
    def tzinfo(self):
        return tzberlin if self.uses_dst else tzwinter
    def copy(self,id):
        """Creates a new dataset without records with the same meta data as this dataset.
        Give a new (unused) id
        """
        return Dataset(id=id,
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
                        site=self.site)
    def asarray(self,start=None,end=None):
        raise NotImplementedError('%s - data set can not return values with "asarray". Is the type correct?' % self.type)    
    def size(self):
        return 0
    def statistics(self):
        """Calculates mean, stddev and number of records for this data set
        """
        t,v = self.asarray()
        return np.mean(v),np.std(v),len(v)

def removedataset(*args):
    """Removes a dataset and its records entirely from the database
    !!Handle with care, there will be no more checking!!"""
    session=Session()
    datasets = [session.query(Dataset).get(int(a)) for a in args]
    for ds in datasets:
        name = str(ds)
        if ds.is_timeseries():
            reccount=ds.records.delete()
            session.commit()
        else:
            reccount = 0
        session.delete(ds)
        session.commit()
        print "Deleted %s and %i records" % (name,reccount)

class MemRecord(object):
    def __init__(self,id,dataset,time,value,sample=None,comment=None,is_error=False):
        self.id=id
        self.dataset=dataset
        self.time=time
        self.value=value
        self.sample=sample
        self.comment=comment
        self.is_error=is_error
class Record(Base):
    """
    The record holds sinigle measured, quantitative values.
    
    Database fields:
    id: numeric identifier, new counting for each dataset
    dataset: the owning dataset
    time: the time of the measurement
    value: the value of the measurement
    sample: if the value is from a taken sample, this item can hold the label of the sample
    comment: any additional information
    is_error: if True, the record is marked as error and is not used for analysis
    """
    __tablename__= 'record'
    id=sql.Column(sql.Integer, primary_key=True)
    _dataset=sql.Column("dataset", sql.Integer, sql.ForeignKey('dataset.id'), primary_key=True)
    dataset=orm.relationship("Timeseries", backref= orm.backref('records',lazy='dynamic'),lazy='joined')
    time=sql.Column(sql.DateTime)
    value=sql.Column(sql.Float)
    sample=sql.Column(sql.String)
    comment = sql.Column(sql.String)
    is_error = sql.Column(sql.Boolean,nullable=False, default=False)    
    
    @property
    def calibrated(self):
        """Returns the calibrated value"""
        if not self.value is None:
            return self.dataset.calibration_slope * self.value + self.dataset.calibration_offset
        else:
            return None   
    def __str__(self):
        return "%s[%i] = %g %s" % (self.dataset.name,self.id,
                                   self.value,self.dataset.valuetype.unit)
    @classmethod
    def query(cls,session):
        return session.query(cls).select_from(Dataset).join(Dataset.records)
    def __jdict__(self):
        return dict(id=self.id,
                    dataset=self.dataset.id,
                    time=self.time,
                    value=self.value,
                    sample=self.sample,
                    comment=self.comment)

# TODO: Put foreign_key to timeseries
transforms_table = sql.Table('transforms',Base.metadata,
                             sql.Column('target',sql.Integer,ForeignKey('transformed_timeseries.id'),primary_key=True),
                             sql.Column('source',sql.Integer,ForeignKey('dataset.id'),primary_key=True))
class Timeseries(Dataset):    
    __mapper_args__ = dict(polymorphic_identity='timeseries')
    def split(self,time):
        """Creates a new dataset using copy and assignes all records after
        time to the new dataset. Useful """
        session = self.session()
        next = self.records.filter(Record.time>=time,Record.value != None).order_by(Record.time).first()
        last = self.records.filter(Record.time<=time,Record.value != None).order_by(sql.desc(Record.time)).first()
        if not next or not last:
            raise RuntimeError("Split time %s is not between two records of %s" % (t,self))
        
        self.comment+='Dataset is splitted at %s to allow for different calibration' % time
        dsnew = self.copy(id=newid(Dataset,session))
        self.end = last.time
        dsnew.start = next.time
        records = self.records.filter(Record.time>=next.time)
        records.update({'dataset':dsnew.id})
        session.commit()
        return self,dsnew
    def findjumps(self,threshold):
        """Returns an iterator to find all jumps greater than threshold
        
        To find "jumps", the records of the dataset are scanned for differences
        between records (ordered by time). If the difference is greater than threshold,
        the later record is returned as a jump
        """
        records = self.records.order_by(Record.time).filter(Record.value != None,~Record.is_error)
        last=None
        for rec in records:
            if not rec.value is None:
                if last and abs(rec.value-last.value)>threshold:
                    yield rec
                last=rec
    def findvalue(self,time):
        """Finds the linear interpolated value for the given time in the record"""
        next = self.records.filter(Record.time>=time,Record.value != None,~Record.is_error).order_by(Record.time).first()
        last = self.records.filter(Record.time<=time,Record.value != None,~Record.is_error).order_by(sql.desc(Record.time)).first()
        if next and last:
            dt_next = (next.time-time).total_seconds()
            dt_last = (time-last.time).total_seconds()
            dt = dt_next + dt_last
            if dt<0.1:
                return next.value,0.0
            else:
                return (1-dt_next/dt) * next.value + (1-dt_last/dt) * last.value,min(dt_last,dt_next)
        elif next:
            return next.value,(next.time-time).total_seconds()
        elif last:
            return last.value,(time-last.time).total_seconds()
        else:
            raise RuntimeError('%s has no records' % self)
    def calibratevalue(self,value):
        """Calibrates a value
        """
        return value * self.calibration_slope + self.calibration_offset
    def maxrecordid(self):
        """Finds the highest record id for this dataset"""
        session = self.session()
        q=session.query(sql.func.max(Record.id)).select_from(Record)
        q=q.filter_by(dataset=self).scalar()
        return q if not q is None else 1
    def addrecord(self,Id=None,value=None,time=None,comment=None,sample=None):
        """Adds a record to the dataset
        Id: id for the recordset, if None, a new id will be created
        value: value of the record
        time: time of the record
        comment: comments for this new record
        """
        value=float(value)
        session = self.session()
        if Id is None:
            maxid = self.maxrecordid()
            Id=maxid+1
        if time is None:
            time = datetime.now()
        if (not self.valuetype.inrange(value)):
            raise ValueError('RECORD does not fit VALUETYPE: %(v)g %(u)s is out of range for %(vt)s' 
                             % dict(v=value,u=self.valuetype.unit,vt=self.valuetype.name)) 
        if not (self.start <= time <= self.end):
            raise ValueError('RECORD does not fit DATASET: You tried to insert a record for date %s ' +
                               'to dataset %s, which allows only records between %s and %s' 
                               % (time,self,self.start,self.end))
        result = Record(id=Id,time=time,value=value,dataset=self,comment=comment,sample=sample)
        session.add(result)
        return result
    def asarray(self,start=None,end=None):
        session = self.session()    
        records = session.query(Record).filter(Record._dataset == self.id)
        records=records.order_by(Record.time).filter(~Record.is_error)
        if start:
            records=records.filter(Record.time>=start)
        if end:
            records=records.filter(Record.time<=end)
        t0 = datetime(1,1,1)
        date2num = lambda t: (t-t0).total_seconds()/86400 + 1.0
        def r2c(records):
            for r in records:
                if r[0] is None:
                    yield np.log(-1),date2num(r[1])
                else:
                    yield r[0],date2num(r[1])
        t = np.zeros(shape=records.count(),dtype=float)
        v = np.zeros(shape=records.count(),dtype=float)
        for i,r in enumerate(r2c(records.values('value','time'))):
            v[i],t[i] = r
        v*=self.calibration_slope 
        v+=self.calibration_offset  
        return t,v
    def size(self):
        return self.records.count()


class TransformedTimeseries(Dataset):
    __tablename__ = 'transformed_timeseries'
    __mapper_args__ = dict(polymorphic_identity='transformed_timeseries')
    id = sql.Column(sql.Integer,sql.ForeignKey('dataset.id'), primary_key=True)
    expression = sql.Column(sql.String)
    latex = sql.Column(sql.String)
    sources = orm.relationship("Timeseries", secondary=transforms_table,order_by="Timeseries.start")
    def sourceids(self):
        return [s.id for s in self.sources]
    def size(self):
        return self.session().query(Record).filter(Record._dataset.in_(self.sourceids())).count()
    def asarray(self,start=None,end=None):
        src_t=[]
        src_v=[]
        for src in self.sources:
            t,v = src.asarray(start,end)
            src_t = np.concatenate((src_t,t))
            src_v = np.concatenate((src_v,v))
        src_v = self.transform(src_v)
        return src_t, src_v
    def updatetime(self):
        self.start = min(ds.start for ds in self.sources)
        self.end = max(ds.end for ds in self.sources)
    def transform(self,x):
        return eval(self.expression,{'x':x},np.__dict__)
    def records(self, witherrors=False):
        session = self.session()
        srcrecords = session.query(Record).filter(Record._dataset.in_(self.sourceids())).order_by(Record.time)
        if not witherrors:
            srcrecords = srcrecords.filter(~Record.is_error)
        i=0
        for r in srcrecords:
            i+=1
            yield MemRecord(id=i,dataset=r.dataset,time=r.time,value=self.transform(r.calibrated),sample=r.sample,comment=r.comment)
    def suitablesources(self):
        session = self.session()
        sourceids = self.sourceids()
        res = session.query(Timeseries).filter(Timeseries.site==self.site,
                                               ~Timeseries.id.in_(sourceids),
                                               )
        if len(self.sources):
            vt = self.sources[0].valuetype
            res = res.filter(Timeseries.valuetype == vt)
        return res
                  
           
        
class DatasetGroup(object):
    def __init__(self,datasetids,start=None,end=None):
        self.datasetids = list(datasetids)
        self.start = start
        self.end = end
    def datasets(self,session):
        return session.query(Dataset).filter(Dataset.id.in_(self.datasetids)).order_by(Dataset.start).all()
    def asarray(self,session):
        datasets=self.datasets(session)
        src_t=[]
        src_v=[]
        for src in datasets:
            t,v = src.asarray(self.start,self.end)
            src_t = np.concatenate((src_t,t))
            src_v = np.concatenate((src_v,v))
        return src_t, src_v
    
        
        