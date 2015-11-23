'''
Created on 07.02.2013

@author: philkraf
'''
import db
import os
import sys
from datetime import datetime, timedelta

# AbstractImport
from traceback import format_exc as traceback

def findStartDate(siteid,instrumentid):
    session = db.Session()
    ds=session.query(db.Dataset).filter(db.Dataset._site==siteid,db.Dataset._source==instrumentid).order_by(db.Dataset.end.desc()).first()
    if ds:
        return ds.end
    else:
        return None

def finddateGaps(siteid,instrumentid,startdate=None,enddate=None):
    session = db.Session()
    dss = session.query(db.Dataset).filter(db.Dataset._site==siteid,db.Dataset._source==instrumentid
                                           ).order_by('"valuetype","start"')
    if startdate:
        dss=dss.filter(db.Dataset.end>startdate)
    if enddate:
        dss=dss.filter(db.Dataset.start<enddate)
    # Filter for the first occuring valuetype
    ds1 = dss.first()
    if ds1 is None: 
        return [(startdate,enddate)] if startdate and enddate else None
    dss = dss.filter(db.Dataset._valuetype==ds1._valuetype).all()
    # Make start and enddate if not present
    if not startdate:
        startdate=dss[0].start
    if not enddate:
        enddate=dss[-1].end
    if dss:
        res=[]
        # Is there space before the first dataset?
        if startdate<dss[0].start:
            res.append((startdate,dss[0].start))
        # Check for gaps>1 day between datasets 
        for ds1,ds2 in zip(dss[:-1],dss[1:]):
            # if there is a gap between
            if ds1.end - ds2.start >= timedelta(days=1):
                res.append((ds1.end,ds2.start))
        # Is there space after the last dataset
        if enddate>dss[-1].end:
            res.append((dss[-1].end,enddate))
        return res
            
    else:
        return [(startdate,enddate)] if startdate and enddate else None


class ImportStat(object):
    def __init__(self,sum=0.0,min=1e308,max=-1e308,n=0,start=datetime(2100,1,1),end=datetime(1900,1,1)):
        self.sum, self.min,self.max,self.n,self.start,self.end = sum,min,max,n,start,end

    @property
    def mean(self):
        return self.sum / float(self.n)

    def __str__(self):
        d = self.__dict__
        d.update({'mean': self.mean})
        return """Statistics:
        mean    = %(mean)g
        min/max = %(min)g/%(max)g
        n       = %(n)i
        start   = %(start)s
        end     = %(end)s
        """ % d

    def __repr__(self):
        d = self.__dict__
        d.update({'mean': self.mean})
        return repr(d)

    def __jsondict__(self):
        return dict(mean=self.mean,min=self.min,max=self.max,n=self.n,start=self.start,end=self.end)

class AbstractImport(object):
    """ This class imports provides functionality for importing files to the
    database, using a config file. The config file describes the format and
    gives necessary meta data, as the instrument, and the value types of the
    columns. The conf file should be in the same directory as the text file or
    somewhere up the directory tree, but below the datafiles directory."""

    def __init__(self, filename, user, siteid, instrumentid, startdate,
                 enddate):
        self.filename = filename
        self.name = os.path.basename(self.filename)
        self.user = user
        self.siteid = siteid
        self.instrumentid = instrumentid
        self.startdate = startdate
        self.enddate = enddate
        self.errorstream = sys.stderr

    def submit(self):
        """
        Submits the data from the columns of the textfile (using loadvalues) to the database, using raw_commit
        """
        session = db.Session()
        # Get the dataset objects for the columns
        datasets={}
        for k in self.datasets:
            datasets[k] = db.Dataset.get(session,self.datasets[k])
        # A dict to hold the current record id for each column k
        newid = lambda k: (session.query(db.sql.func.max(db.Record.id)).filter(db.Record._dataset==datasets[k].id).scalar() or 0)+1
        recid=dict((k,newid(k)) for k in self.datasets)
        # A dict to cache the value entries for committing for each column k
        records=dict((k,[]) for k in self.datasets)
        try:
            # Loop through all values
            for i,d in enumerate(self.loadvalues()):
                # Get time of record
                t = d['d']

                # Loop through columns
                for col in self.descriptor.columns:
                    k = col.column
                    # If there is a value for column k
                    if not d[k] is None:
                        records[k].append(dict(dataset=datasets[k].id,id=recid[k],time=t,value=d[k]))
                        # Next id for column k
                        recid[k]+=1
                # To protected the memory, commit every 10000 items
                if (i+1) % self.commitinterval == 0:
                    records=self.raw_commit(records)
            # Commit remaining records
            records=self.raw_commit(records)
            # Update start and end of the datasets
            for k,ds in datasets.iteritems():
                ds.start = session.query(db.sql.func.min(db.Record.time)).filter_by(dataset=ds).scalar()
                ds.end = session.query(db.sql.func.max(db.Record.time)).filter_by(dataset=ds).scalar()
            # Commit changes to the session
            session.commit()

        except:
            # Something wrong? Write to error stream
            self.errorstream.write(traceback())
            session.rollback()
        finally:
            session.close()

    # Use sqlalchemy.core for better performance
    def raw_commit(self,records):
        "Commits the records to the Record table, and clears the records-lists"
        for k,rec in records.iteritems():
            if rec:
                db.engine.execute(db.Record.__table__.insert(),rec)
        # Return a dict like records, but with empty lists
        return dict((r,[]) for r in records)

    def createdatasets(self,comment='',verbose=False):
        """
        Creates the datasets according to the descriptor
        """
        session=db.Session()
        inst = session.query(db.Datasource).get(self.instrumentid)
        user=session.query(db.Person).get(self.user)
        site=session.query(db.Site).get(self.siteid)
        raw = session.query(db.Quality).get(0)
        for col in self.descriptor.columns:
            vt = session.query(db.ValueType).get(col.valuetype)
            id = db.newid(db.Dataset,session)
            ds = db.Timeseries(id=id,measured_by=user,valuetype=vt,site=site,name=col.name,
                            filename=self.filename,comment=col.comment,source=inst,quality=raw,
                            start=self.startdate,end=datetime.today(),level=col.level,
                            access=col.access if not col.access is None else 1, timezone=None, project=None)
            self.datasets[col.column] = ds.id
        session.commit()
        session.close()

    def parsedate(self,timestr):
        """
        Parses a datestring according to the format given in the description.
        The description should either be a valid python formatstring, like %Y/%m/%d %H:%M
        or "excel" to parse float values as in excel to a date.
        """
        if self.descriptor.dateformat.lower() == 'excel':
            t0 = datetime(1899,12,30)
            timestr=timestr.split()
            if len(timestr) == 1:
                timefloat = float(timestr[0])
                days = int(timefloat)
                seconds = round((timefloat % 1) * 86400)
                return t0 + timedelta(days=days,seconds=seconds)
            elif len(timestr) == 2:
                days = int(timestr[0])
                seconds = round((float(timestr[1]) % 1) * 86400)
                return t0 + timedelta(days=days,seconds=seconds)
        else:
            return datetime.strptime(timestr,self.descriptor.dateformat)

    def parsefloat(self,s):
        """
        parses a string to float, using the decimal point from the descriptor
        """
        s.replace(self.descriptor.decimalpoint,'.')
        return float(s)

    def get_statistic(self):
        """
        Returns a column name - ImportStat dictionary with the statistics for each import column
        """
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

    def loadvalues(self):
        raise NotImplementedError("Use an implementation class")

    @staticmethod
    def extension_fits_to(filename):
        """
        Here should be the implemenation for making a decision by a filename if
        a file can be processed by this class

        :param: filename
        :return: Returns if a file is applicable for an import class
        """
        raise NotImplementedError("Use an implementation class")

    @staticmethod
    def get_importdescriptor():
        """
        Return the prefered import descriptor class
        """
        raise NotImplementedError('Use an implementation class')

def savetoimports(filename,user,datasets=None):
    """
    Adds the filename to the import history file .import.hist
    """
    d = os.path.dirname(filename)
    f = file(os.path.join(d,'.import.hist'),'a')
    f.write(u'%s,%s,%s' % (os.path.basename(filename),user,datetime.now()))
    for ds in datasets:
        f.write(u',ds%s' % ds)
    f.write('\n')
    f.close()

def checkimport(filename):
    d = os.path.dirname(filename)
    fn = os.path.join(d,'.import.hist')
    if os.path.exists(fn):
        f = file(fn)
        b = os.path.basename(filename)
        for l in f:
            ls=l.split(',',3)
            if b in ls[0]:
                d=dict(fn=ls[0],dt=ls[2],u=ls[1],ds=ls[3])
                return "%(u)s has already imported %(fn)s at %(dt)s as %(ds)s" % d
    return ''
