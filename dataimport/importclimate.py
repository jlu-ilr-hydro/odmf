#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Jun 28, 2012
@author: Philipp Kraft
"""

from __future__ import division
import sys
import openpyxl
import db
from datetime import datetime,timedelta
from traceback import format_exc as traceback
import base
        
def get_vtcoldict(instrumentid):
    if instrumentid==19: # CR800 at lower flume VK
        return { 3:(9,288.,'Rainfall'), # rainfall
                 4:(8,1.,'Temperature'), # Temperature
                 8:(10,1.,'Humidity'), # Humidity
                 11:(11,1.,'Solar radiation'), # solar radiation
                 16:(12,1.,'Wind speed'), # Wind speed
                }
    else:
        raise RuntimeError('Not a valid instrument id for a climate station')  
class ClimateImporterDat(base.ImportAdapter):
    dateformat='%Y-%m-%d %H:%M:%S'
    #          col:(vt,factor,name)
    def parsedate(self,d):
        return datetime.strptime(d.strip('" '),self.dateformat)

    def loadvalues(self):
        fin = file(self.filename)
        for i in range(self.skiprows):
            fin.readline()
        for line in fin:
            ls=line.split(',')
            d=self.parsedate(ls[0])
            if  (
                    (not self.startdate) or d>=self.startdate 
                ) and (
                   (not self.enddate) or d<=self.enddate
                ):
                res = dict(d=d)
                hasval=False
                for k in self.vtcoldict:
                    try:
                        res[k] = float(ls[k])
                        if res[k]<-999:
                            res[k]=None
                        else:
                            res[k]*= self.vtcoldict[k][1]
                            hasval=True
                    except:
                        res[k] = None
                if hasval: yield res
    def createdatasets(self, comment=''):
        session = db.Session()
        try:
            user = session.query(db.Person).get(self.user)
            site = session.query(db.Site).get(self.siteid)
            for column in self.vtcoldict:
                vt_id,factor,colname = self.vtcoldict[column]
                valuetype = session.query(db.ValueType).get(vt_id)
                dsid = db.newid(db.Dataset, session)
                ds = db.Timeseries(id=dsid,site=site,measured_by=user,valuetype=valuetype,_source=self.instrumentid,
                            start=self.startdate,end=datetime.today(),name=colname)
                session.add(ds)
                self.datasets[column] = ds.id
            session.commit()
        except:
            sys.stderr.write(traceback())
            session.rollback()
        finally:
            session.close()
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
       

    def __init__(self,filename, user, siteid, instrumentid, startdate=None,enddate=None):
        base.ImportAdapter.__init__(self, filename, user, siteid, instrumentid, startdate,enddate)
        self.skiprows = 4
        self.vtcoldict = get_vtcoldict(instrumentid)
        self.datasets={}
    def get_statistic(self):
        stats=dict((k,base.ImportStat()) for k in self.vtcoldict)
        for d in self.loadvalues():
            for k in self.vtcoldict:
                if not d[k] is None:
                    stats[k].sum += d[k]
                    stats[k].max = max(stats[k].max,d[k])
                    stats[k].min = min(stats[k].min,d[k])
                    stats[k].n += 1
                    stats[k].start = min(d['d'],stats[k].start)
                    stats[k].end = max(d['d'],stats[k].end)
        return dict((self.vtcoldict[k][2],stats[k]) for k in self.vtcoldict)
            
        
        

        
                
             
                
        
        
        