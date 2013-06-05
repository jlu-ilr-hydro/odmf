'''
Exports the climate datasets as one table with multiple columns

Created on 05.06.2013

@author: kraft-p
'''
import db
from cStringIO import StringIO
import codecs
from traceback import format_exc as traceback
import sys
def exportData(filename,datasetids,start=None,end=None,tolerance=60):
    session=db.Session()
    try:
        datasets = session.query(db.Timeseries).filter(db.Timeseries.id.in_(datasetids)).order_by(db.Timeseries.start)
        datasetdict = dict((ds.id,ds) for ds in datasets)
        vtdict = dict((ds.id,ds._valuetype) for ds in datasets)
        valuetypes = sorted(set(ds.valuetype for ds in datasets),key=lambda vt:vt.id)
        columns = dict((vt.id,i+1) for i,vt in enumerate(valuetypes))
        records = session.query(db.Record).filter(db.Record._dataset.in_(sorted(datasetdict))).order_by(db.Record.time)
        if start:
            records = records.filter(db.Record.time>=start)
        if end:
            records = records.filter(db.Record.time<=end)    
    except:
        sys.stderr.write(traceback())
        session.close()
        return
    try:
        reccount = records.count()
        print "Start processing %i records" % reccount
        acttime = records.first().time
        fout = file(filename,'w')
        fout.write(codecs.BOM_UTF8)
        
        fout.write('time,' + ','.join(unicode(vt).encode('utf-8') for vt in valuetypes) + '\n')
        i=0
        line = [acttime] + [None] * len(valuetypes)
        line[0] = acttime
        old_ds = 0 
        for time,value,dsid in records.values('time','value','dataset'):
            dt = time - acttime
            vt = vtdict[dsid]
            column = columns[vt]
            if dsid!=old_ds:
                old_ds = dsid
                ds = datasetdict[dsid]
            calibvalue = ds.calibratevalue(value)
            if (dt.total_seconds()>tolerance):
                i+=1
                acttime = time
                fout.write(','.join(unicode(s).encode('utf-8') for s in line) + '\n')
                line = [acttime] + [None] * len(valuetypes)
                if i % 100==0:
                    print i,"lines exported"
                    fout.flush()
            line[column] = calibvalue
    except:
        sys.stderr.write(traceback())        
    finally:
        fout.close()
        session.close()
if __name__=='__main__':
    from datetime import datetime,timedelta
    exportData('export.csv', 71, 19)
    