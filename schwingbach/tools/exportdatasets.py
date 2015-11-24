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
from datetime import datetime,timedelta
t0 = datetime(1,1,1)

def num2date(t):
    return t0 + timedelta(days=t)

def exportLines(fout,lines,tolerance=60):
    """
    Exports multiple lines from a plot as a table with each line as a column
    To align the values in the rows a tolerance is chosen, by which measure times
    may differ, but should still be combined in the same row. 
    """
    # Make sure the tolerance is > 0
    tolerance = max(tolerance,0.01)

    # prepare the output file, Excel needs the BOM to recognize csv files with UTF-8
    fout.write(codecs.BOM_UTF8)
    
    # simplify fileoutput
    def writeline(line):
        fout.write(','.join((unicode(s).encode('utf-8') if s else '') for s in line) + '\n')
    
    # Write headers
    fout.write('time,')
    writeline(lines)
    fout.write('\n')
        
    # Load all time and value arrays for the lines. This is a huge memory consumer
    tvpairs = [l.load() for l in lines]
    # Create counters, holding the position of a line point
    counters = [0] * len(tvpairs)
    # Last time step
    told = 0.0
    # Hold the data of the current line
    linedata=[]
    # Loop on with the counters until all data is consumed
    while any(c < len(tv[0]) for c,tv in zip(counters,tvpairs)):
        # Get the current time step
        t = min(tv[0][c] for c,tv in zip(counters,tvpairs) if c<len(tv[0]))
        # If the current time step is past the tolerance time in seconds
        if t-told >= tolerance/86400.:
            # Get the datetime
            time = num2date(t)
            # Save the current linedata to the file
            if linedata:
                writeline(linedata)
            # Make a new linedata
            linedata = [time] + ([None] * len(lines))
            # Current t gets the old time
            told=t 
        
        # Populate the linedata for each line
        for i in range(len(lines)):
            # Check if there is data left and the current data is inside the tolerance time
            if (counters[i]<len(tvpairs[i][0]) 
                and tvpairs[i][0][counters[i]] - t < tolerance):
                # Get the value
                linedata[i+1] = tvpairs[i][1][counters[i]]
                # Move on with counter
                counters[i]+=1
            
                 

        
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
        records = session.query(db.Record).filter(db.Record._dataset.in_(sorted(datasetdict))).order_by(db.Record.time).filter(~db.Record.is_error)
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
    