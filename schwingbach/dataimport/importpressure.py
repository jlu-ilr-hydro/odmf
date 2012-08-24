'''
Created on 24.07.2012

@author: philkraf
'''
from __future__ import division
import db
from datetime import datetime
from collections import namedtuple
import sys
import os
PressureRecord = namedtuple("Record", 'id date T d') 

class PressureImport(object):

    def loadvalues(self):
        raise NotImplemented('Use a derived class')
    def query(self,cls):
        return self.session.query(cls)
    def get(self,cls,id):
        return self.session.query(cls).get(id)
    def createdatasets(self,comment=''):
        vtD = self.valuetype
        vtT = self.query(db.ValueType).get(8)
        idD = db.newid(db.Dataset,self.session)
        idT =idD+1
        dsD = db.Dataset(id=idD,measured_by=self.user,valuetype=vtD,site=self.site,
                         filename=self.filename,comment=comment,source=self.inst)
        dsD.name = self.name + '-d'
        dsT = db.Dataset(id=idT,measured_by=self.user,valuetype=vtT,site=self.site,
                         filename=self.filename,comment=comment,source=self.inst)
        dsT.name = self.name + '-T'
        dsT.start = dsD.start = self.result[0].date
        dsT.end = dsD.end = self.result[-1].date
        
        for r in self.result:
            Drec = db.Record(id=r.id,time=r.date,value=r.d,dataset=dsD)
            Trec = db.Record(id=r.id,time=r.date,value=r.T,dataset=dsT)
            self.session.add(Drec)
            self.session.add(Trec)
    
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
    def commit(self):
        self.session.commit()
        self.session.close()
        
    def __init__(self,filename,user,siteid,valuetypeid):
        self.filename=filename
        self.name = os.path.basename(self.filename).replace('.csv','')
        self.session=db.Session()
        self.inst = self.get(db.Datasource,1)
        self.user=self.get(db.Person,user)
        self.site=self.get(db.Site,int(siteid))
        self.valuetype = self.get(db.ValueType,valuetypeid)
        self.result=[]
        self.errors=[]

class OdysseeImport(PressureImport):
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
    
    def __init__(self,filename,user,siteid,valuetypeid=2):
        PressureImport.__init__(self, filename, user, siteid, valuetypeid=valuetypeid)
        self.result,self.errors = self.loadvalues()
class DiverImport(PressureImport):
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
    def __init__(self,filename,user,siteid,valuetypeid=5):
        PressureImport.__init__(self, filename, user, siteid, valuetypeid=valuetypeid)
        self.result,self.errors = self.loadvalues()
        
    
if __name__=='__main__':
    if len(sys.argv)<4:
        sys.stderr.write('Usage: importpressure.py <file> <user> <siteid>')
        exit()
    imp = OdysseeImport(*sys.argv[1:])
    print imp
    print imp.statistics()
    if len(imp.errors)>0:
        sys.stderr.write('\n--------------------\n'.join(imp.errors[:10]))
     
    
