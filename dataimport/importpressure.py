'''
Created on 24.07.2012

@TODO: Check dependencies and delete this module 
@deprecated: 
@author: philkraf
'''
from __future__ import division
import db
from datetime import datetime, timedelta
from collections import namedtuple
import sys
import os
from base import ImportAdapter, ImportStat
from traceback import format_exc as traceback
PressureRecord = namedtuple("Record", 'id date T d datechanged') 

            
class PressureImport(ImportAdapter):
    "Base class for the import of raw data from Water level/ Temp. loggers"
    commitinterval=10000
    def loadvalues(self):
        raise NotImplemented('Use a derived class')
    def get(self,cls,id):
        return self.session.query(cls).get(id)
    def createdatasets(self,comment='',verbose=False):
        session=db.Session()
        name = os.path.basename(self.filename).replace('.csv','')
        inst = session.query(db.Datasource).get(self.instrumentid)
        user=session.query(db.Person).get(self.user)
        site=session.query(db.Site).get(self.siteid)
        
        vtD = session.query(db.ValueType).get(1)
        vtT = session.query(db.ValueType).get(8)
        raw = session.query(db.Quality).get(0)
        idD = db.newid(db.Dataset,session)
        idT =idD+1
        dsD = db.Timeseries(id=idD,measured_by=user,valuetype=vtD,site=site,
                         filename=self.filename,comment=comment,source=inst,quality=raw)
        dsD.name = name + '-d'
        dsD.comment = 'Contains the uncalibrated water level above the sensor. Please change the valuetype after calibration.'
        dsT = db.Timeseries(id=idT,measured_by=user,valuetype=vtT,site=site,
                         filename=self.filename,comment=comment,source=inst,quality=raw)
        dsT.name = name + '-T'
        dsT.comment = 'Contains the uncalibrated water temperature at the sensor.'
        dsT.start = dsD.start = self.startdate
        dsT.end = dsD.end = datetime.today()
        self.datasets=dict(depth=dsD.id,Temperature=dsT.id)
        if verbose:
            print 'New Datasets:\n' + '\n'.join(['#%i - %s' % (ds.id,ds.name) for ds in (dsD,dsT)])

        session.commit()
        session.close()
    def raw_commit(self,Drec,Trec):
        db.engine.execute(db.Record.__table__.insert(),Drec)
        db.engine.execute(db.Record.__table__.insert(),Trec)
        return [],[]
    def submit(self):
        session = db.Session()
        dsD,dsT = [db.Dataset.get(session,dsid) for dsid in (self.datasets['depth'],self.datasets['Temperature'])] 
        errors = []
        i=1
        Drec=[]
        Trec=[]
        for r,error in self.loadvalues():
            if error:
                errors.append(error)
            elif (((not self.startdate) or r.date>=self.startdate)
                  and (not self.enddate) or r.date<=self.enddate):
                if not dsD.valuetype.outofrange(r.d):
                    Drec.append(dict(id=r.id,time=r.date,value=r.d,dataset=dsD.id))
                if not dsT.valuetype.outofrange(r.T):
                    Trec.append(dict(id=r.id,time=r.date,value=r.T,dataset=dsT.id))
                i+=1
            if i % self.commitinterval == 0 and i:
                Drec,Trec=self.raw_commit(Drec,Trec)
        Drec,Trec=self.raw_commit(Drec,Trec)
        for ds in (dsD,dsT):
            ds.start = session.query(db.sql.func.min(db.Record.time)).filter_by(dataset=ds).scalar()
            ds.end = session.query(db.sql.func.max(db.Record.time)).filter_by(dataset=ds).scalar()
        session.commit()
        session.close()


    def get_statistic(self):
        n = 0
        datechange = 0
        meanT = meanD = 0.0 
        minT = minD = 9999
        maxT = maxD = -9999
        start = datetime(2100,1,1)
        end = datetime(2000,1,1)
        errors = []
        for rec,error in self.loadvalues():
            if rec:
                n+=1
                meanT += rec.T
                meanD += rec.d
                minT = min(minT,rec.T)
                minD = min(minD,rec.d)
                maxT = max(maxT,rec.T)
                maxD = max(maxD,rec.d)
                start = min(start,rec.date)
                end = max(end,rec.date)
                datechange += int(rec.datechanged)
            elif error:
                errors.append(error)
        if errors:
            print '\n'.join(errors)
        else:
            meanT/=n
            meanD/=n
        return dict(T    = ImportStat(meanT,minT,maxT,n,start,end),
                    depth= ImportStat(meanD,minD,maxD,n,start,end))
    def __str__(self):
        str = "%s for site #%i from %s\n%s" % (type(self),self.site.id,self.filename,self.user)
        str +='\n%6i Errors\n%6i Records' % (len(self.errors),len(self.result))
        return str
        
    def __init__(self,filename,user,siteid,instrumentid=None,startdate=None,enddate=None):
        ImportAdapter.__init__(self,filename,user,siteid,instrumentid,startdate,enddate)
        self.datasets=[]

class OdysseyImport(PressureImport):
    """Imports Pressure/Temperature data from an Odyssey logger in the CSV format including 12 lines of metadata.
        
    Instanciation:
        >>> oci = OdysseyCSVImport(filename='data.prn',user='philipp',siteid=1,startdate=datetime(2012,5,25))
    Creates an instance of the importer, but does not load data. A new db.Session is created, site and 
    user are fetched from the database and loads the values from the file into the memory. With startdate
    records can be filtered to exclude older records.
    
    Checking errors:
        >>> print '------------------\n'.join(opi.errors)
    Checking values:
        >>> print oci.statistics()
        
    Saving values to the database:
        >>> oci.createdatasets()
    This creates two new datasets for water level and temperature with (more or less appropriate) metadata and 
    creates new records for each value 
    
    """

    def parsedate(self,d,t):
        return datetime.strptime(d.strip()+' '+t.strip(),'%d/%m/%Y %H:%M:%S')
    t0 = datetime(1899,12,30)

    def float2date(self,date):
        days = int(date)
        seconds = round((date % 1) * 86400)
        return self.t0 + timedelta(days=days,seconds=seconds)

    def loadvaluesprn(self):
        fin = file(self.filename)
        thisyear = datetime.now().year
        id=0
        for i,line in enumerate(fin):
            changedate=False
            try:
                columns = line.split(',')
                date = self.float2date(float(columns[0]))
                if date.year<2000:
                    date=date.replace(year=thisyear)
                    if date>datetime.now():
                        date=date.replace(year=thisyear-1)
                    changedate=True
                if  (
                        (not self.startdate) or date>=self.startdate 
                    ) and (
                       (not self.enddate) or date<=self.enddate
                    ):
                    id+=1
                    rec = PressureRecord(id=id,
                                 date=date,
                                 T=float(columns[2]),
                                 d=float(columns[4])*1e-3,
                                 datechanged=changedate,                                 
                                )
                    if rec.d>0:
                        yield rec, None
            except Exception as e:
                yield None, '%s:%i - Error\n' % (traceback(),i)

    def loadvaluescsv(self):
        fin = file(self.filename)
        thisyear = datetime.now().year
        id=0
        for i in xrange(12):
            fin.readline()
        for i,line in enumerate(fin):
            changedate=False
            try:
                columns = line.split(',')
                date=self.parsedate(columns[1], columns[2])
                if date.year<2000:
                    date=date.replace(year=thisyear)
                    if date>datetime.now():
                        date=date.replace(year=thisyear-1)
                    changedate=True
                if  (
                        (not self.startdate) or date>=self.startdate 
                    ) and (
                       (not self.enddate) or date<=self.enddate
                    ):
                    id+=1
                    rec = PressureRecord(id=id,
                                 date=date,
                                 T=float(columns[4]),
                                 d=float(columns[6])*1e-3,
                                 datechanged=changedate,                                 
                                )
                    if rec.d>0:
                        yield rec, None
            except Exception as e:
                yield None,'%i:%s - Error\n' % (i,e.message)
    def loadvalues(self):
        if self.filename.lower().endswith('.prn'):
            return self.loadvaluesprn()
        else:
            return self.loadvaluescsv()

    
    def __init__(self,filename,user,siteid,instrumentid=None,startdate=None,enddate=None):
        """Creates a new importer for Odyssey CSV files
        filename: Path to the CSV file
        user: user name of the data owner
        siteid: id of the site of the installation
        startdate: If given, values before the startdate are not imported
        """
        PressureImport.__init__(self, filename, user, siteid, 1,startdate,enddate)



class DiverImport(PressureImport):
    """Imports Pressure/Temperature data from a Diver logger in the raw CSV (csv-like) format.
    
    Instanciation:
        >>> di = DiverImport(filename='data.prn',user='philipp',siteid=1,startdate=datetime(2012,5,25))
    Creates an instance of the importer, but does not load data. A new db.Session is created, site and 
    user are fetched from the database and loads the values from the file into the memory. With startdate
    records can be filtered to exclude older records.
    
    Checking errors:
        >>> print '------------------\n'.join(di.errors)
    Checking values:
        >>> print di.statistics()
        
    Saving values to the database:
        >>> di.createdatasets()
    This creates two new datasets for water level and temperature with (more or less appropriate) metadata and 
    creates new records for each value 
    
    """

    def parsedate(self,s):
        return datetime.strptime(s.strip(),'%Y/%m/%d %H:%M:%S')
    def parsefloat(self,s,decpoint='.'):
        if decpoint==',':
            s=s.replace(',','.')
        return float(s)

    def loadvalues(self):
        fin = file(self.filename)
        for i in xrange(54):
            fin.readline()
        for i,line in enumerate(fin):
            seperator = ';' if ';' in line else ','
            decpoint = ',' if ';' in line else '.'
            try:
                columns = line.split(seperator)
                date=self.parsedate(columns[0])
                if  (
                        (not self.startdate) or date>=self.startdate 
                    ) and (
                       (not self.enddate) or date<=self.enddate
                    ):

                    rec = PressureRecord(id=i+1,
                                 date=date,
                                 T=self.parsefloat(columns[2],decpoint),
                                 d=self.parsefloat(columns[1],decpoint)*1e-2,
                                 datechanged=False,
                                )
                    yield rec,None
            except Exception as e:
                yield None, '%s:%s - Error\n%s' % (os.path.basename(self.filename),i,e.message)
    def __init__(self,filename, user, siteid, instrumentid, startdate,enddate):
        """Creates a new importer for Diver CSV files
        filename: Path to the CSV file
        user: user name of the data owner
        siteid: id of the site of the installation
        startdate: If given, values before the startdate are not imported
        """
        PressureImport.__init__(self, filename, user, siteid, 2,startdate,enddate)
        
    
     
    
