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
def exportData(fout,datasetids,start=None,end=None,tolerance=60):
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
        leveldict = dict((ds.id,ds.level) for ds in datasets)
        # Make cartesian product of sites and valuetypes
        columnset = sorted(set((ds.valuetype.id, ds.site.id, ds.level) for ds in datasets))
        vtnames = dict((ds.valuetype.id,ds.valuetype) for ds in datasets)
        
        # Derive columns
        columns = dict((c,i+1) for i,c in enumerate(columnset))
        columnnames=['time'] + ['%s at #%i%s' % (vtnames[c[0]],c[1],'(%gm)' % c[2] if not c[2] is None else '') for c in columnset]
        
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
        # Output file
        fout.write(codecs.BOM_UTF8) # needed for Excel to interpret utf-8 encoded csv files
        # Write headers
        fout.write(','.join(unicode(s).encode('utf-8') for s in columnnames) + '\n')
        i=0
        # create an empty line to start
        line = [acttime] + [None] * len(columnset)
        old_ds = 0 
        def writeline(fout,line):
            fout.write(','.join((unicode(s).encode('utf-8') if s else '') for s in line) + '\n')
        for time,value,dsid in records.values('time','value','dataset'):
            ds = datasetdict[dsid]
            column = columns[(ds.valuetype.id,ds.site.id,ds.level)]
            dt = time - acttime
            calibvalue = ds.calibratevalue(value)
            # If time is moving on...
            if (dt.total_seconds()>tolerance):
                # Save the current line
                writeline(fout,line)
                if i % 100==0:
                    fout.flush()
                # Count the lines
                i+=1
                # Set the new time
                acttime = time
                # Create a new line
                line = [acttime] + [None] * len(columnset)
            # Set the actual value in the line
            line[column] = calibvalue
        writeline(fout,line)
        print "%i lines written" % i
    except:
        sys.stderr.write(traceback())        
    finally:
        session.close()
if __name__=='__main__':
    from datetime import datetime, timedelta
    exportData('export.csv', 71, 19)
    