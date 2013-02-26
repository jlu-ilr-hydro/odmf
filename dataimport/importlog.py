'''
Created on 19.02.2013

@author: kraft-p
'''
import xlrd
import db
from datetime import datetime, timedelta

class LogImportError(RuntimeError):
    def __init__(self,row,msg):
        RuntimeError.__init__(self,"Could not import row %i:%s" % (row+1,msg))
        self.row = row
        self.text = msg
class LogColumns:
    date=0
    time=1
    datetime=0,1
    site=2
    dataset=3
    value=4
    logtext=5
    msg=6
    job=7
class LogbookImport(object):
    """Imports from an defined xls file messages to the logbook and append values to datasets"""
    t0 = datetime(1899,12,30)

    def get_time(self,date,time):
        if not time:
            return self.t0 + timedelta(date)
        else:
            if time>1.000001:
                time=time-int(time)
            date=int(date)
        return self.t0 + timedelta(date+time)
    def get_obj(self,session,cls,row,col):
        id=None
        try:
            id = self.sheet.cell_value(row,col)
        except: pass
        try:
            if not id:
                return None, None
            obj = session.query(cls).get(int(id))
            if not obj:
                raise Exception('%s.get(%s) not found' % (id,cls))
            return obj,''
        except Exception as e:
            return None,'%s is not a valid %s id: %s' % (id,cls,e)
    def get_value(self,row,columns):
        try:
            return [self.sheet.cell_value(row,col) for col in columns] 
        except:
            return self.sheet.cell_value(row,columns)   
    def __init__(self,filename,user,sheetname=None):
        self.filename=filename
        self.workbook = xlrd.open_workbook(filename)
        session=db.Session()
        self.user=db.Person.get(session,user)
        session.close()
        if not self.user:
            raise RuntimeError('%s is not a valid user' % user)
        if sheetname:
            self.sheet = self.workbook.sheet_by_name(sheetname)
        else:
            self.sheet = self.workbook.sheet_by_index(0)
    def __call__(self,commit=False):
        session = db.Session()
        logs=[]
        errors={}
        try:
            for row in xrange(1,self.sheet.nrows):
                if self.sheet.cell_value(row,0):
                    try:
                        logs.append(dict(row=row,
                                         error=False,
                                         log=self.importrow(session, row)
                                         )
                                    )
                    except LogImportError as e:
                        errors[e.row]=e.text
                        logs.append(dict(row=row,
                                         error=True,
                                         log=e.text
                                         )
                                    )
            if commit and not errors:
                session.commit()
        finally:
            session.close()
        return logs, not errors
    def importrow(self,session,row):
        date, time = self.get_value(row,LogColumns.datetime)
        try:
            time = self.get_time(date, time)
        except:
            raise LogImportError(row,'Could not read date and time')
        
        site,err = self.get_obj(session,db.Site,row,LogColumns.site)
        if err: raise LogImportError(row,err)
        elif not site: raise LogImportError(row,'Missing site')
        ds,err = self.get_obj(session,db.Dataset,row,LogColumns.dataset)
        if err: raise LogImportError(row,err)
        if ds and (ds.source is None or ds.source.sourcetype!='manual'):
            raise LogImportError(row,'%s is not a manual measured dataset, if the dataset is correct please change the type of the datasource to manual' % ds)
        elif ds and ds.site!=site:
            raise LogImportError(row,'%s is not at site #%i' % (ds,site.id))
        v=None
        if self.sheet.cell_type(row,LogColumns.value) == 2: # Numeric field
            v = self.get_value(row,LogColumns.value)
        if v and ds is None:
            raise LogImportError(row,"A value is given, but no dataset")
        logtype,msg = self.get_value(row,(LogColumns.logtext,LogColumns.msg))
        job,err = self.get_obj(session, db.Job, row, LogColumns.job)
        if err: raise LogImportError(row,'%s in not a valid Job.id')
        if ds and v:
            if ds.start>time:
                ds.start=time
            if ds.end<time:
                ds.end=time
            ds.addrecord(value=v,time=time,comment=msg)
            logmsg = 'Measurement:%s=%g %s with %s' % (ds.valuetype.name,v,ds.valuetype.unit,ds.source.name)
            if msg: logmsg+=', ' + msg
            newlog = db.Log(id=db.newid(db.Log,session), 
                            user=self.user,
                            time=time,
                            message=logmsg,
                            type='measurement',
                            site=site)
            session.add(newlog)
            return u"Add value %g %s to %s (%s)" % (v,ds.valuetype.unit,ds,time)
        else:
            if not msg:
                raise LogImportError(row,'No message to log')
            newlog = db.Log(id=db.newid(db.Log,session), 
                            user=self.user,
                            time=time,
                            message=msg,
                            type=logtype,
                            site=site)
            session.add(newlog)
            return u"Log: %s" % newlog
        if job:
            job.make_done(self, time)