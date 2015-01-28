'''
Created on 04.03.2013

@author: kraft-p

This module is a generic import tool for delimited text files, created from automatic loggers
The import is performed by the class TextImport, derived from ImportAdapter. 
The file format is described in the TextImportDescription, an saved in a config file.
'''
import db
from configparser import RawConfigParser
from glob import glob
import os
import os.path as op
import sys
from base import ImportAdapter, ImportStat
from datetime import datetime,timedelta
from traceback import format_exc as traceback
from cStringIO import StringIO
    
class TextImportColumn:
    """Describes the content of a column in a delimited text file"""
    def __init__(self,column,name,valuetype,factor=1.0,comment=None,
                 difference=None,minvalue=-1e308,maxvalue=+1e308,
                 append=None,level=None,access=None):
        """Creates a column description in a delimited text file.
        upon import, the column will be saved as a dataset in the database
        
        column: Position of the column in the file. Note: The first column is 0
        name: Name of the column and name of the dataset
        valuetype: Id of the value type stored in the column.
        factor: If the units of the column and the valuetype differ, use factor for conversion
        difference: If True, the stored values will be the difference to the value of the last row
        minvalue: This is the allowed lowest value (not converted). Lower values will not be imported
        maxvalue: This is the allowed highest value. Higher values will not be converted
        comment: The new dataset can be commented by this comment
        append: For automatic import, append to this datasetid 
        """
        self.column=int(column)
        self.name=name
        self.valuetype=int(valuetype)
        self.comment = comment
        self.factor=factor or 1.0
        self.difference = difference
        self.minvalue=minvalue
        self.maxvalue=maxvalue
        self.append=append
        self.level=level
        self.access = access
    def __str__(self):
        return "%s[%s]:column=%i" % ('d' if self.difference else '',self.name,self.column) 
    def to_config(self,config,section):
        "Writes the colummn description to a config file"
        config.set(section,'; 0 based column number')
        config.set(section,'column',self.column)
        config.set(section,'; name of the field, will become name of the dataset')
        config.set(section,'name',self.name)
        config.set(section,'; id of the valuetype in this field')
        config.set(section,'valuetype',self.valuetype)
        config.set(section,'; factor for unit conversion')
        config.set(section,'factor',self.factor)
        if self.comment:
            config.set(section,'comment',self.comment)
        if not self.difference is None:
            config.set(section,'; if Yes, the import will save the difference to the last value')
            config.set(section,'difference',self.difference)
        config.set(section,'; lowest allowed value, use this for NoData values')
        config.set(section,'minvalue',self.minvalue)
        config.set(section,'; highest allowed value, use this for NoData values')
        config.set(section,'maxvalue',self.maxvalue)
        if self.level:
            config.set(section,'; Level property of the dataset. Use this for Instruments measuring at one site in different depth')
            config.set(section,'level',self.level)
        if not self.access is None:
            config.set(section,'; Access property of the dataset. Default level is 1 (for loggers) but can set to 0 for public datasets or to a higher level for confidential datasets')
            config.set(section,'access',self.access)
            
            
        
    @classmethod
    def from_config(cls,config,section):
        "Get the column description from a config-file"
        def getvalue(option,type=str):
            if config.has_option(section,option):
                return type(config.get(section,option))
            else:
                return None
        return cls(column=config.getint(section,'column'),
                   name=config.get(section,'name'),
                   valuetype=config.getint(section,'valuetype'),
                   factor=config.getfloat(section,'factor'),
                   comment=getvalue('comment'),
                   difference = getvalue('difference'),
                   minvalue = getvalue('minvalue',float),
                   maxvalue=getvalue('maxvalue',float),
                   append=getvalue('append',int),
                   level=getvalue('level',float),
                   access=getvalue('access',int)
                   )
        

class TextImportDescription:
    """
    Describes the file format and content of a delimited text file for
    import to the database.
    """
    def __init__(self,instrument,skiplines=0,delimiter=',',decimalpoint='.',dateformat='%d/%m/%Y %H:%M:%S',datecolumns=(0,1)):
        """
        instrument: the database id of the instrument that produced this file
        skiplines: The number of lines prepending the actual data
        delimiter: The delimiter sign of the columns. Use TAB for tab-delimited columns, otherwise ',' or ';'               
        """
        self.name=''
        self.fileextension=''
        self.instrument=int(instrument)
        self.skiplines=skiplines
        self.delimiter=delimiter
        if self.delimiter.upper()=='TAB':
            self.delimiter='\t'
        self.decimalpoint=decimalpoint
        self.dateformat=dateformat
        self.filename=''
        try:
            self.datecolumns=tuple(datecolumns)
        except:
            self.datecolumns=datecolumns, 
        self.columns=[]
    def __str__(self):
        io=StringIO()
        self.to_config().write(io)
        return io.getvalue()
    def addcolumn(self,column,name,valuetype,factor=1.0,comment=None,difference=None,minvalue=-1e308,maxvalue=1e308):
        """
        Adds the description of a column to the file format description
        """
        self.columns.append(TextImportColumn(column,name,valuetype,factor,comment,difference))
        return self.columns[-1]
    def to_config(self):
        """
        Returns a ConfigParser.RawConfigParser with the data of this description
        """
        config = RawConfigParser(allow_no_value=True)
        session=db.Session()
        inst = session.query(db.Datasource).get(self.instrument)
        if not inst:
            raise ValueError('Error in import description: %s is not a valid instrument id')
        session.close()
        section = unicode(inst)
        config.add_section(section)
        config.set(section,'instrument',self.instrument)
        config.set(section,'skiplines',self.skiplines)
        config.set(section,'delimiter','TAB' if self.delimiter=='\t' else self.delimiter)
        config.set(section,'decimalpoint',self.decimalpoint)
        config.set(section,'dateformat',self.dateformat)
        config.set(section,'datecolumns',str(self.datecolumns).strip('(), '))
        if self.fileextension:
            config.set(section,'fileextension',self.fileextension)
        for col in self.columns:
            section = col.name
            config.add_section(section)
            col.to_config(config,section)
        return config
    @classmethod
    def from_config(cls,config):
        """
        Creates a TextImportDescriptor from a ConfigParser.RawConfigParser
        by parsing its content
        """
        sections=config.sections()
        if not sections:
            raise IOError('Empty config file')
        # Create a new TextImportDescriptor from config file
        tid = cls(instrument=config.getint(sections[0],'instrument'),
                  skiplines=config.getint(sections[0],'skiplines'),
                  delimiter=config.get(sections[0],'delimiter'),
                  decimalpoint=config.get(sections[0],'decimalpoint'),
                  dateformat=config.get(sections[0],'dateformat'),
                  datecolumns=eval(config.get(sections[0],'datecolumns'))
                  )
        tid.name = sections[0]
        for section in sections[1:]:
            tid.columns.append(TextImportColumn.from_config(config,section))
        return tid
    
    @classmethod
    def from_file(cls,path,stoppath='datafiles',pattern='*.conf'):
        """
        Searches in the parent directories of the given path for .conf file
        until the stoppath is reached.
        """
        # As long as no *.conf file is in the path 
        while not glob(op.join(path,pattern)):
            # Go to the parent directory
            path = op.dirname(path) 
            # if stoppath is found raise an error
            if op.basename(path)==stoppath:
                raise IOError('Could not find .conf file for file description')
        # Use the first .conf file in the directory
        path = glob(op.join(path,pattern))[0]
        # Create a config
        config = RawConfigParser()
        # Load from the file
        config.readfp(file(path))
        # Return the descriptor
        descr = cls.from_config(config)
        descr.filename=path
        return descr
       
    
class TextImport(ImportAdapter):
    """
    This class imports tabular text files (eg. CSV) to the database, using a config file. The config file 
    describes the format and gives necessary meta data, as the instrument, and the value types of the columns.
    The conf file should be in the same directory as the text file or somewhere up the directory tree, but
    below the datafiles directory.
    """
    def __init__(self,filename,user,siteid,instrumentid=None,startdate=None,enddate=None):
        """
        filename: Absolute path to the text file for import
        user: the user name of the data owner
        siteid: id of the site for the dataset
        instrumentid: Can be omitted and is read from the conf file. Exists for compatibility
                      with ImportAdapter
        startdate: Beginning of the import period
        enddate:   End of the import period
        """
        ImportAdapter.__init__(self,filename,user,siteid,instrumentid,startdate,enddate)
        self.descriptor = TextImportDescription.from_file(self.filename)
        self.instrumentid = self.descriptor.instrument
        self.commitinterval = 10000
        self.datasets={}
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
                            start=self.startdate,end=datetime.today(),level=self.descriptor.level,
                            access=self.descriptor.access if not self.descriptor.access is None else 1)
            self.datasets[col.column] = ds.id
        session.commit()
        session.close()
    def loadvalues(self):
        """
        Generator function, yields the values from the file as 
        a dictionary for each import column
        """    
        def intime(time):
            "Checks if time is between startdate and enddate"
            return (
                    (not self.startdate) or d>=self.startdate 
                ) and (
                   (not self.enddate) or d<=self.enddate
                ) 
        def outofrange(col,v):
            "Tests if the value is inside the boundaries given by the column description"
            return ((not col.minvalue is None and v<col.minvalue) or 
                    (not col.maxvalue is None and v>col.maxvalue))
        fin = file(self.filename)
        for i in range(self.descriptor.skiplines):
            fin.readline()
        # Contains the last valid values. This is needed for difference columns (eg. Tipping buckets)
        lastraw={}
        for lineno,line in enumerate(fin):
            ls=line.split(self.descriptor.delimiter)
            try:
                d=self.parsedate(' '.join(ls[int(i)].strip('" ') for i in self.descriptor.datecolumns))
                if  intime(d):
                    # Result dictionary, contains the date at key d, and for each column number the factored and checked value 
                    res = dict(d=d)
                    # Dictionary to hold the raw (unfactored, undifferenced) values. NoData is purged anyway
                    raw = {}
                    # Variable to check if the whole line contains any data
                    hasval=False
                    # Loop through all relevant columns
                    for col in self.descriptor.columns:
                        # Shortcut to column number
                        k=col.column
                        try:
                            # get raw value of column
                            raw[k] = float(ls[k])
                            # check if raw value is out of bounds
                            if outofrange(col,raw[k]):
                                raw[k]=None
                                res[k]=None
                            # if the value is the difference to the last value (eg. for Tipping Bucket data)
                            # make the difference to the last raw value
                            elif col.difference and lastraw.get(k):
                                res[k] = (raw[k] - lastraw[k]) * col.factor
                                hasval=True
                            # Just get and convert the value
                            else:
                                res[k] = raw[k] * col.factor
                                hasval=True
                        except Exception as e:
                            # On error, ignore the whole line
                            self.errorstream.write('%s:%i: %s\n' % (os.path.basename(self.filename),lineno + self.descriptor.skiplines,e))
                            res[k] = None
                    if hasval:
                        # If there is anything written, update lastraw to the actual values, for the next round
                        lastraw.update(dict((k,v) for k,v in raw.iteritems() if not v is None))
                        yield res
            except Exception as e:
                # Write the error message to the errorstream and go to the next line
                self.errorstream.write('%s:%i: %s\n' % (os.path.basename(self.filename),lineno + self.descriptor.skiplines,e))

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
    # Use sqlalchemy.core for better performance
    def raw_commit(self,records):
        "Commits the records to the Record table, and clears the records-lists"
        for k,rec in records.iteritems():
            if rec:
                db.engine.execute(db.Record.__table__.insert(),rec)
        # Return a dict like records, but with empty lists
        return dict((r,[]) for r in records)
             
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

# Just for debugging
if __name__=='__main__':
    ti = TextImport(filename='../webpage/datafiles/odypress/GW_001_001.csv', user='philipp', siteid=1)
    for k,v in ti.get_statistic().iteritems():
        print k,v
    