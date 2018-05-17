'''
Created on 04.03.2013

@author: kraft-p

This module is a generic import tool for delimited text files, created from automatic loggers
The import is performed by the class TextImport, derived from ImportAdapter. 
The file format is described in the ImportDescription, an saved in a config file.
'''
import os

from .base import AbstractImport, ImportDescription
from math import isnan


class TextImport(AbstractImport):
    """
    This class imports tabular text files (eg. CSV) to the database, using a config file. The config file 
    describes the format and gives necessary meta data, as the instrument, and the value types of the columns.
    The conf file should be in the same directory as the text file or somewhere up the directory tree, but
    below the datafiles directory.
    """

    def __init__(self, filename, user, siteid, instrumentid=None, startdate=None, enddate=None):
        """
        filename: Absolute path to the text file for import
        user: the user name of the data owner
        siteid: id of the site for the dataset
        instrumentid: Can be omitted and is read from the conf file. Exists for compatibility
                      with ImportAdapter
        startdate: Beginning of the import period
        enddate:   End of the import period
        """
        AbstractImport.__init__(self, filename, user,
                                siteid, instrumentid, startdate, enddate)
        self.descriptor = ImportDescription.from_file(self.filename)
        self.instrumentid = self.descriptor.instrument
        self.commitinterval = 10000
        self.datasets = {}

    def loadvalues(self):
        """
        Generator function, yields the values from the file as 
        a dictionary for each import column
        """

        if (not self.descriptor.decimalpoint) or (not self.descriptor.delimiter):
            raise RuntimeError(
                '.conf file for text import needs to have a decimal point and delimiter defined')

        def intime(time):
            """Checks if time is between startdate and enddate"""
            return (
                (not self.startdate) or d >= self.startdate
            ) and (
                (not self.enddate) or d <= self.enddate
            )

        def outofrange(col, v):
            """Tests if the value is inside the boundaries given by the column description"""
            return ((col.minvalue is not None and v < col.minvalue) or
                    (col.maxvalue is not None and v > col.maxvalue))
        fin = open(self.filename, 'r', errors='replace')
        for i in range(self.descriptor.skiplines):
            fin.readline()
        # Contains the last valid values. This is needed for difference columns (eg. Tipping buckets)
        lastraw = {}
        for lineno, line in enumerate(fin):
            ls = line.split(self.descriptor.delimiter)
            try:
                d = self.parsedate(' '.join(ls[int(i)].strip(
                    '" ') for i in self.descriptor.datecolumns))
                if intime(d):
                    # Result dictionary, contains the date at key d, and for each column number the factored and checked value
                    res = dict(d=d)
                    # Dictionary to hold the raw (unfactored, undifferenced) values. NoData is purged anyway
                    raw = {}
                    # Variable to check if the whole line contains any data
                    hasval = False
                    # Loop through all relevant columns
                    for col in self.descriptor.columns:
                        # Shortcut to column number
                        k = col.column
                        try:
                            # check for nodata values
                            if ls[k] in self.descriptor.nodata:
                                #raise ValueError("R%i:C%i is %s and therefore nodata" % (lineno, col.column, ls[k]))
                                raw[k] = None
                                res[k] = None
                            else:
                                # get raw value of column using the parsefloat function
                                raw[k] = self.parsefloat(ls[k])

                                if isnan(raw[k]):
                                    #self.errorstream.write("WARNING:{}:{} Nan value present\n".format(lineno, k))
                                    print("WARNING:{}:{} Nan value present\n".format(lineno, k))
                            # check if raw value is out of bounds
                            if outofrange(col, raw[k]):
                                raw[k] = None
                                res[k] = None
                            # if the value is the difference to the last value (eg. for Tipping Bucket data)
                            # make the difference to the last raw value
                            elif col.difference and lastraw.get(k):
                                res[k] = (raw[k] - lastraw[k]) * col.factor
                                hasval = True
                            # Just get and convert the value
                            else:
                                res[k] = raw[k] * col.factor
                                hasval = True
                        except Exception as e:
                            # On error, ignore the whole line
                            self.errorstream.write('%s:%i:%i: %s\n' % (os.path.basename(
                                self.filename), lineno + self.descriptor.skiplines, col.column, e))
                            res[k] = None
                    if hasval:
                        # If there is anything written, update lastraw to the actual values, for the next round
                        lastraw.update(dict((k, v)
                                            for k, v in raw.items() if v is not None))
                        yield res
            except Exception as e:
                # Write to StringIO Errorstream
                self.errorstream.write('%s:%i: %s\n' % (os.path.basename(
                    self.filename), lineno + self.descriptor.skiplines, e))

    @staticmethod
    def extension_fits_to(filename):
        return True


# Just for debugging
if __name__ == '__main__':
    ti = TextImport(
        filename='../webpage/datafiles/odypress/GW_001_001.csv', user='philipp', siteid=1)
    for k, v in ti.get_statistic().items():
        print(k, v)
