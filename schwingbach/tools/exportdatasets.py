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
from itertools import product as cartprod
def exportData(filename,datasetids,start=None,end=None,tolerance=60):
    """
    Exports multiple dataset as a csv file with multiple columns
    Note: Columns are determined by value type and site. Dataset, where site and value type is equal will be appended to each other
    Note: Only Timeseries are allowed as input, not transformed timeseries (up till now) 
    """
    session=db.Session()
    try:
        # Get datasets
        datasets = session.query(db.Timeseries).filter(db.Timeseries.id.in_(datasetids)).order_by(db.Timeseries.start)
        datasetdict = dict((ds.id,ds) for ds in datasets)
        # Get value types and sites
        vtdict = dict((ds.id,ds._valuetype) for ds in datasets)
        sitedict = dict((ds.id,ds._site) for ds in datasets)
        valuetypes = sorted(set(ds.valuetype for ds in datasets),key=lambda vt:vt.id)
        sites = sorted(set(ds.site for ds in datasets), key=lambda s:s.id)
        # Make cartesian product of sites and valuetypes
        vtsites = list(cartprod(valuetypes,sites))
        
        # Derive columns
        columns = dict((VS[0].id,VS[1].id,i+1) for i,VS in enumerate(vtsites))
        columnnames=['time'] + ['#%i - %s' % (s.id,vt) for s,vt in vtsites]
        
        # Query records
        records = session.query(db.Record).filter(db.Record._dataset.in_(sorted(datasetdict))).order_by(db.Record.time)
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
        
        fout.write(','.join(unicode(s).encode('utf-8') for s in columnnames) + '\n')
        i=0
        line = [acttime] + [None] * len(vtsites)
        old_ds = 0 
        for time,value,dsid in records.values('time','value','dataset'):
            dt = time - acttime
            vt = vtdict[dsid]
            site = sitedict[dsid]
            column = columns[(vt,site)]
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
    