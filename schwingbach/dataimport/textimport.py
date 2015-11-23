'''
Created on 04.03.2013

@author: kraft-p

This module is a generic import tool for delimited text files, created from automatic loggers
The import is performed by the class TextImport, derived from ImportAdapter. 
The file format is described in the TextImportDescription, an saved in a config file.
'''
import db
from glob import glob
import os
import os.path as op
from configparser import RawConfigParser
from cStringIO import StringIO

from base import AbstractImport
import conf

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
    def __init__(self, instrument, skiplines=0, delimiter=',', decimalpoint='.',
                 dateformat='%d/%m/%Y %H:%M:%S', datecolumns=(0, 1),
                 timezone=conf.CFG_DATETIME_DEFAULT_TIMEZONE, project=None):
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
        # Replace space and tab keywords
        if self.delimiter.upper()=='TAB':
            self.delimiter='\t'
        elif self.delimiter.upper()=='SPACE':
            self.delimiter = ' '
        self.decimalpoint=decimalpoint
        self.dateformat=dateformat
        self.filename=''
        try:
            self.datecolumns=tuple(datecolumns)
        except:
            self.datecolumns=datecolumns, 
        self.columns=[]

        # New added for feature
        self.timezone = timezone  # Timezone for the dataset
        self.project = project  # Project for the dataset

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
        # Replace space and tab by keywords
        config.set(section,'delimiter',{' ':'SPACE','\t':'TAB'}.get(self.delimiter,self.delimiter))
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
       
    
class TextImport(AbstractImport):
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
        AbstractImport.__init__(self,filename,user,siteid,instrumentid,startdate,enddate)
        self.descriptor = TextImportDescription.from_file(self.filename)
        self.instrumentid = self.descriptor.instrument
        self.commitinterval = 10000
        self.datasets={}

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
                            # get raw value of column using the parsefloat function
                            raw[k] = self.parsefloat(ls[k])
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

                # After a reported bug #1025
                # For the line with errorstream.write raising IOError
                # Few researches shows that only the stream.write can raise such
                # an error
                # https://docs.python.org/2/library/io.html#io.IOBase.writable

                # But isn't really a final solution
                if self.errorstream.writable():
                    self.errorstream.write('%s:%i: %s\n' % (os.path.basename(self.filename),lineno + self.descriptor.skiplines,e))
                else:
                    print '%s:%i: %s\n' % (os.path.basename(self.filename),lineno + self.descriptor.skiplines,e)

    @staticmethod
    def extension_fits_to(filename):
        return True

    @staticmethod
    def get_importdescriptor():
        return TextImportDescription


# Just for debugging
if __name__=='__main__':
    ti = TextImport(filename='../webpage/datafiles/odypress/GW_001_001.csv', user='philipp', siteid=1)
    for k,v in ti.get_statistic().iteritems():
        print k,v
    