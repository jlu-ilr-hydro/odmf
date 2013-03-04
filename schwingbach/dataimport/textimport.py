'''
Created on 04.03.2013

@author: kraft-p
'''
import db
from ConfigParser import RawConfigParser
from glob import glob
import os
import sys
from base import ImportAdapter, ImportStat
from datetime import datetime,timedelta
from traceback import format_exc as traceback
    
class TextImportColumn:
    def __init__(self,column,name,valuetype,factor=1.0,comment=None):
        self.column=int(column)
        self.name=name
        self.valuetype=int(valuetype)
        self.comment = comment
        self.factor=factor
    def to_config(self,config,section):
        config.set(section,'column',self.column)
        config.set(section,'name',self.name)
        config.set(section,'valuetype',self.valuetype)
        config.set(section,'valuetype',self.valuetype)
        config.set(section,'factor',self.factor)
        if self.comment:
            config.set(section,'comment',self.comment)
    @classmethod
    def from_config(cls,config,section):
        return cls(column=config.getint(section,'column'),
                   name=config.get(section,'name'),
                   valuetype=config.getint(section,'valuetype'),
                   factor=config.getfloat(section,'factor'),
                   comment=config.get(section,'comment') if config.has_option(section,'comment') else None
                   )

class TextImportDescription:
    def __init__(self,instrument,skiplines=0,delimiter=',',decimalpoint='.',dateformat='%d/%m/%Y %H:%M:%S',datecolumns=(0,1)):
        self.instrument=int(instrument)
        self.skiplines=skiplines
        self.delimiter=delimiter
        self.decimalpoint=decimalpoint
        self.dateformat=dateformat
        try:
            self.datecolumns=tuple(datecolumns)
        except:
            self.datecolumns=datecolumns, 
        self.columns=[]
    def to_config(self):
        config = RawConfigParser()
        session=db.Session()
        inst = session.query(db.Datasource).get(self.instrument)
        if not inst:
            raise ValueError('Error in import description: %s is not a valid instrument id')
        session.close()
        section = 'general'
        config.add_section(section)
        config.set(section,'; instrument', str(inst))
        config.set(section,'instrument',self.instrument)
        config.set(section,'skiplines',self.skiplines)
        config.set(section,'delimiter',self.delimiter)
        config.set(section,'decimalpoint',self.decimalpoint)
        config.set(section,'dateformat',self.dateformat)
        config.set(section,'datecolumns',str(self.datecolumns).strip('(), '))
        for col in self.columns:
            section = col.name
            config.add_section(section)
            col.to_config(config,section)
        return config
    @classmethod
    def from_config(cls,config):
        section='general'
        # Create a new TextImportDescriptor from config file
        tid = cls(instrument=config.getint(section,'instrument'),
                  skiplines=config.getint(section,'skiplines'),
                  delimiter=config.get(section,'delimiter'),
                  decimalpoint=config.get(section,'decimalpoint'),
                  dateformat=config.get(section,'dateformat'),
                  datecolumns=eval(config.get(section,'datecolumns'))
                  )
        for section in config.sections():
            if section!='general':
                tid.columns.append(TextImportColumn.from_config(config,section))
        return tid
                
        
    
class TextImport(ImportAdapter):
    def __init__(self,filename,user,siteid,instrumentid=None,startdate=None,enddate=None):
        ImportAdapter.__init__(self,filename,user,siteid,instrumentid,startdate,enddate)
        config = RawConfigParser()
        config.read(glob(os.path.join(os.path.dirname(filename),'*.conf')))
        self.descriptor = TextImportDescription.from_config(config)
        self.instrumentid = self.descriptor.instrument
        self.commitinterval = 10000
        self.datasets={}
    def parsedate(self,timestr):
        if self.descriptor.dateformat.lower() == 'excel':
            t0 = datetime(1899,12,30)
            timestr=timestr.split()
            if len(timestr) == 1:
                timefloat = float(timestr)
                days = int(timefloat)
                seconds = round((timefloat % 1) * 86400)
                return t0 + timedelta(days=days,seconds=seconds)
            elif len(timestr) == 2:
                days = int(timestr[0])
                seconds = round((float(timestr[1]) % 1) * 86400)
                return t0 + timedelta(days=days,seconds=seconds)
        else:
            return datetime.strptime(timestr,self.descriptor.dateformat)

    def createdatasets(self,comment='',verbose=False):
        session=db.Session()
        inst = session.query(db.Datasource).get(self.instrumentid)
        user=session.query(db.Person).get(self.user)
        site=session.query(db.Site).get(self.siteid)
        raw = session.query(db.Quality).get(0)
        for col in self.descriptor.columns:
            vt = session.query(db.ValueType).get(col.valuetype)
            id = db.newid(db.Dataset,session)
            ds = db.Dataset(id=id,measured_by=user,valuetype=vt,site=site,name=col.name,
                            filename=self.filename,comment=col.comment,source=inst,quality=raw,
                            start=self.startdate,end=datetime.today())
            self.datasets[col.column] = ds.id
        session.commit()
        session.close()
    def loadvalues(self):
        fin = file(self.filename)
        for i in range(self.descriptor.skiplines):
            fin.readline()
        for line in fin:
            ls=line.split(self.descriptor.delimiter)
            d=self.parsedate(' '.join())
            if  (
                    (not self.startdate) or d>=self.startdate 
                ) and (
                   (not self.enddate) or d<=self.enddate
                ):
                res = dict(d=d)
                hasval=False
                for col in self.descriptor.columns:
                    k=col.column
                    try:
                        res[k] = float(ls[k])
                        if res[k]<-999:
                            res[k]=None
                        else:
                            res[k]*= col.factor
                            hasval=True
                    except:
                        res[k] = None
                if hasval: yield res
    def get_statistic(self):
        stats=dict((col.column,ImportStat()) for col in self.descriptor.columns)
        for d in self.loadvalues():
            for col in self.descriptor.columns:
                k=col.column
                if not d[k] is None:
                    stats[k].sum += d[k]
                    stats[k].max = max(stats[k].max,d[k])
                    stats[k].min = min(stats[k].min,d[k])
                    stats[k].n += 1
                    stats[k].start = min(d['d'],stats[k].start)
                    stats[k].end = max(d['d'],stats[k].end)
        return dict((col.name,stats[col.column]) for col in self.descriptor.columns)
    def raw_commit(self,records):
        "Use sqlalchemy.core for better performance"
        for k,rec in records.iteritems():
            db.engine.execute(db.Record.__table__.insert(),rec)
        return dict((r,[]) for r in records)
             
    def submit(self):     
        session = db.Session()
        datasets={}
        for k in self.datasets:
            datasets[k] = db.Dataset.get(session,self.datasets[k])
        id=dict((k,0) for k in self.vtcoldict)
        records=dict((k,[]) for k in self.datasets)
        try:
            i=0
            for d in self.loadvalues():
                i+=1
                t = d['d']
                for k in self.vtcoldict:
                    if not d[k] is None:
                        records[k].append(dict(dataset=datasets[k].id,id=id[k],time=t,value=d[k]))
                    id[k]+=1
                if i % 10000 == 0:
                    records=self.raw_commit(records)
            records=self.raw_commit(records)
            for k,ds in datasets.iteritems():
                ds.start = session.query(db.sql.func.min(db.Record.time)).filter_by(dataset=ds).scalar()
                ds.end = session.query(db.sql.func.max(db.Record.time)).filter_by(dataset=ds).scalar()
            session.commit()

        except:
            sys.stderr.write(traceback())
            session.rollback()
        finally:
            session.close()
