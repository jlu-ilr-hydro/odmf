# -*- coding:utf-8 -*-
'''
Created on 13.07.2012

@author: philkraf
'''
import sqlalchemy as sql
import sqlalchemy.orm as orm
from base import Base,Session
from sqlalchemy.schema import ForeignKey
from datetime import datetime,timedelta
from dbobjects import newid, Person, Datasource

class Quality(Base):
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
    __tablename__= 'valuetype'
    id=sql.Column(sql.Integer,primary_key=True)
    name=sql.Column(sql.String)
    unit=sql.Column(sql.String)
    comment=sql.Column(sql.String)
    def __str__(self):
        return "%s [%s]" % (self.name,self.unit)
    def records(self):
        session= Session.object_session(self)
        return Record.query(session).filter(Dataset.valuetype==self)
    def __jdict__(self):
        return dict(id=self.id,
                    name=self.name,
                    unit=self.unit,
                    comment=self.comment)

class DataGroup(Base):
    __tablename__ = 'datagroup'
    id = sql.Column(sql.Integer,primary_key=True)
    name = sql.Column(sql.String,unique=True)
    _valuetype=sql.Column("valuetype",sql.Integer,sql.ForeignKey('valuetype.id'))
    valuetype = orm.relationship("ValueType")
    _site=sql.Column("site",sql.Integer, sql.ForeignKey('site.id'))
    site = orm.relationship("Site")
    comment=sql.Column(sql.String)
    def append(self,dataset):
        if (dataset.valuetype is self.valuetype and
            dataset.site is self.site):
            dataset.group = self
    def __jdict__(self):
        return dict(id=self.id,
                    name=self.name,
                    valuetype=self.valuetype,
                    site=self.site,
                    comment=self.comment)
        
    

class Dataset(Base):
    __tablename__= 'dataset'
    id=sql.Column(sql.Integer,primary_key=True)
    name=sql.Column(sql.String, unique=True)
    filename=sql.Column(sql.String, nullable=True)
    start=sql.Column(sql.DateTime, nullable = True)
    end=sql.Column(sql.DateTime, nullable = True)
    #_source = sql.Column("source",sql.Integer, sql.ForeignKey('datasource.id'))
    #source = orm.relationship("DataSource")
    _site=sql.Column("site",sql.Integer, sql.ForeignKey('site.id'))
    site = orm.relationship("Site",backref='datasets')
    _valuetype=sql.Column("valuetype",sql.Integer,sql.ForeignKey('valuetype.id'))
    valuetype = orm.relationship("ValueType",backref='datasets')
    _measured_by=sql.Column("measured_by",sql.String,sql.ForeignKey('person.username'))
    measured_by = orm.relationship("Person",backref='datasets',
                                   primaryjoin="Person.username==Dataset._measured_by")
    _quality=sql.Column("quality",sql.Integer,sql.ForeignKey('quality.id'))
    quality = orm.relationship("Quality")
    _source = sql.Column("source",sql.Integer,sql.ForeignKey('datasource.id'),nullable=True)
    source = orm.relationship("Datasource",backref="datasets")
    _group = sql.Column("group",sql.Integer,sql.ForeignKey('datagroup.id'),nullable=True)
    group = orm.relationship("DataGroup",backref='datasets')
    calibration_offset = sql.Column(sql.Float,nullable=False,default=0.0)
    calibration_slope = sql.Column(sql.Float,nullable=False,default=1.0)
    comment=sql.Column(sql.String)
    def __str__(self):
        return str(self.name)
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
                    group=self.group,
                    comment=self.comment)
    def maxrecordid(self):
        session = self.session()
        return session.query(sql.func.max(Record.id)).select_from(Record).filter_by(dataset=self.id).scalar()
        
    def addrecord(self,Id=None,value=None,time=None):
        value=float(value)
        session = self.session()
        if Id is None:
            maxid = self.maxrecordid()
            Id=maxid+1
        if time is None:
            time = datetime.now()
        if not (self.start <= time <= self.end):
            raise RuntimeError('RECORD does not fit DATASET: You tried to insert a record for date %s ' +
                               'to dataset %s, which allows only records between %s and %s' 
                               % (time,self,self.start,self.end))
        result = Record(id=Id,time=time,value=value,dataset=self)
        session.add(result)
    def potential_groups(self,session):
        q = session.query(DataGroup)
        q=q.filter_by(valuetype = self.valuetype)
        q=q.filter_by(site = self.site)
        return q

            
            
        
            

class Record(Base):
    __tablename__= 'record'
    id=sql.Column(sql.Integer, primary_key=True)
    _dataset=sql.Column("dataset", sql.Integer, sql.ForeignKey('dataset.id'), primary_key=True)
    dataset=orm.relationship("Dataset", backref= orm.backref('records',lazy='dynamic'),lazy='joined')
    time=sql.Column(sql.DateTime)
    value=sql.Column(sql.Float)
    sample=sql.Column(sql.String)
    comment = sql.Column(sql.String)
        
    @property
    def calibrated(self):
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
