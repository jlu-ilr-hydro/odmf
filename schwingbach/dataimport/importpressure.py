'''
Created on 24.07.2012

@author: philkraf
'''
from __future__ import division
import db
from datetime import datetime, timedelta
from collections import namedtuple
import sys
import os
from traceback import format_exc as traceback
PressureRecord = namedtuple("Record", 'id date T d') 
def removedataset(*args):
    "Removes the dataset ids"
    session=db.Session()
    datasets = [session.query(db.Dataset).get(int(a)) for a in args]
    for ds in datasets:
        name = str(ds)
        reccount=ds.records.delete()
        session.commit()
        session.delete(ds)
        session.commit()
        print "Deleted %s and %i records" % (name,reccount)
        
class PressureImport(object):
    "Base class for the import of raw data from Water level/ Temp. loggers"
    commitinterval=5000
    def loadvalues(self):
        raise NotImplemented('Use a derived class')
    def query(self,cls):
        return self.session.query(cls)
    def get(self,cls,id):
        return self.session.query(cls).get(id)
    def createdatasets(self,comment=''):
        if not self.result:
            raise ValueError("No results present, you need to execute loadvalues first")
        vtD = self.query(db.ValueType).get(1)
        vtT = self.query(db.ValueType).get(8)
        raw = self.query(db.Quality).get(0)
        idD = db.newid(db.Dataset,self.session)
        idT =idD+1
        dsD = db.Dataset(id=idD,measured_by=self.user,valuetype=vtD,site=self.site,
                         filename=self.filename,comment=comment,source=self.inst,quality=raw)
        dsD.name = self.name + '-d'
        dsD.comment = 'Contains the uncalibrated water level above the sensor. Please change the valuetype after calibration.'
        dsT = db.Dataset(id=idT,measured_by=self.user,valuetype=vtT,site=self.site,
                         filename=self.filename,comment=comment,source=self.inst,quality=raw)
        dsT.name = self.name + '-T'
        dsT.start = dsD.start = self.result[0].date
        dsT.end = dsD.end = self.result[-1].date
        self.datasets=[dsD,dsT]
    def submit(self,verbose=False):
        dsD,dsT = self.datasets
        for i,r in enumerate(self.result):
            if (not self.startdate) or r.date>self.startdate:
                Drec = db.Record(id=r.id,time=r.date,value=r.d,dataset=dsD)
                Trec = db.Record(id=r.id,time=r.date,value=r.T,dataset=dsT)
                self.session.add(Drec)
                self.session.add(Trec)
            if i % self.commitinterval == 0 and i:
                self.session.commit()
                if verbose:
                    print "commit records %6i -%6i" % (i-self.commitinterval,i)
                    sys.stdout.flush()
        self.session.close()


    def __call__(self,comment=''):
        print self.statistics()
        print "Load in session..."
        sys.stdout.flush()
        self.createdatasets(comment)
        print 'New Datasets:\n' + '\n'.join(['#%i - %s' % (ds.id,ds.name) for ds in self.datasets])
        sys.stdout.flush()
        self.submit(True)
    def statistics(self):
        n = len(self.result)
        if not n:
            return "n = 0"
        meanT = sum(r.T for r in self.result)/n
        meanD = sum(r.d for r in self.result)/n
        minT = min(r.T for r in self.result)
        maxT = max(r.T for r in self.result)
        minD = min(r.d for r in self.result)
        maxD = max(r.d for r in self.result)
        start = self.result[0].date.strftime('%d.%m.%Y')
        end = self.result[-1].date.strftime('%d.%m.%Y')
        return "n = %i\n%s - %s\nT:%g/%g/%g degC\nd:%g/%g/%g m" % (n,start,end,minT,meanT,maxT,minD,meanD,maxD)
    def __str__(self):
        str = "%s for site #%i from %s\n%s" % (type(self),self.site.id,self.filename,self.user)
        str +='\n%6i Errors\n%6i Records' % (len(self.errors),len(self.result))
        return str
        
    def __init__(self,filename,user,siteid,instrumentid=None,startdate=None):
        self.filename=filename
        self.name = os.path.basename(self.filename).replace('.csv','')
        self.session=db.Session()
        self.inst = self.get(db.Datasource,instrumentid)
        self.user=self.get(db.Person,user)
        self.site=self.get(db.Site,int(siteid))
        self.startdate = startdate
        self.result=[]
        self.errors=[]
        self.datasets=[]

class OdysseyCSVImport(PressureImport):
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
    def loadvalues(self):
        fin = file(self.filename)
        result=[]
        errors=[]
        for i in xrange(12):
            fin.readline()
        for i,line in enumerate(fin):
            try:
                columns = line.split(',')
                rec = PressureRecord(id=int(columns[0]),
                             date=self.parsedate(columns[1], columns[2]),
                             T=float(columns[4]),
                             d=float(columns[6])*1e-3
                            )
                result.append(rec)
            except Exception as e:
                errors.append('%s:%i - Error\n' % (i,e.message))
        return result,errors
    
    def __init__(self,filename,user,siteid,startdate=None):
        """Creates a new importer for Odyssey CSV files
        filename: Path to the CSV file
        user: user name of the data owner
        siteid: id of the site of the installation
        startdate: If given, values before the startdate are not imported
        """

        PressureImport.__init__(self, filename, user, siteid, 1,startdate)
        self.result,self.errors = self.loadvalues()


class OdysseyPRNImport(PressureImport):
    """Imports Pressure/Temperature data from an Odyssey logger in the raw PRN (csv-like) format.
    
    Instanciation:
        >>> opi = OdysseyPRNImport(filename='data.prn',user='philipp',siteid=1,startdate=datetime(2012,5,25))
    Creates an instance of the importer, but does not load data. A new db.Session is created, site and 
    user are fetched from the database and loads the values from the file into the memory. With startdate
    records can be filtered to exclude older records.
    
    Checking errors:
        >>> print '------------------\n'.join(opi.errors)
    Checking values:
        >>> print opi.statistics()
        
    Saving values to the database:
        >>> opi.createdatasets()
    This creates two new datasets for water level and temperature with (more or less appropriate) metadata and 
    creates new records for each value 
    
    """
    
    
    t0 = datetime(1899,12,30)

    def float2date(self,date):
        return OdysseyPRNImport.t0 + timedelta(date)

    def loadvalues(self):
        fin = file(self.filename)
        result=[]
        errors=[]
        changedatecount = 0
        thisyear = datetime.now().year
        for i,line in enumerate(fin):
            try:
                columns = line.split(',')
                date = self.float2date(float(columns[0]))
                if date.year<2000:
                    date=date.replace(year=thisyear)
                    changedatecount+=1
                rec = PressureRecord(id=i+1,
                             date=date,
                             T=float(columns[2]),
                             d=float(columns[4])*1e-3
                            )
                if rec.d>0:
                    result.append(rec)
            except Exception as e:
                errors.append('%s:%i - Error\n' % (traceback(),i))
        if changedatecount:
            errors.insert(0,'Changed year to this year for %i records' % changedatecount)
        return result,errors

    def __init__(self,filename,user,siteid,startdate=None):
        """Creates a new importer for Odyssey PRN files
            filename: Path to the PRN file
            user: user name of the data owner
            siteid: id of the site of the installation
            startdate: If given, values before the startdate are not imported
        """
        PressureImport.__init__(self, filename, user, siteid, 1,startdate)
        self.result,self.errors = self.loadvalues()

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
        return datetime.strptime(s,'%Y/%m/%d %H:%M:%S')
    def loadvalues(self):
        Record = namedtuple("Record", 'id date T d') 
        fin = file(self.filename)
        result=[]
        errors=[]
        for i in xrange(54):
            fin.readline()
        for i,line in enumerate(fin):
            try:
                columns = line.split(';')
                rec = Record(id=i+1,
                             date=self.parsedate(columns[0]),
                             T=float(columns[2].replace(',','.')),
                             d=float(columns[1].replace(',','.'))*1e-2
                            )
                result.append(rec)
            except Exception as e:
                errors.append('%s:%s - Error\n%s' % (os.path.basename(self.filename),i,e.message))
        return result,errors
    def __init__(self,filename,user,siteid,startdate=None):
        """Creates a new importer for Diver CSV files
        filename: Path to the CSV file
        user: user name of the data owner
        siteid: id of the site of the installation
        startdate: If given, values before the startdate are not imported
        """
        PressureImport.__init__(self, filename, user, siteid, 2,startdate)
        self.result,self.errors = self.loadvalues()
        
    
if __name__=='__main__':
    if len(sys.argv)<4:
        sys.stderr.write('Usage: importpressure.py <file> <user> <siteid>')
        exit()
    imp = OdysseyPRNImport(*sys.argv[1:])
    print imp
    print imp.statistics()
    if len(imp.errors)>0:
        sys.stderr.write('\n--------------------\n'.join(imp.errors[:10]))
     
    
