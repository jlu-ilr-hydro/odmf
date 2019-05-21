'''
Created on 07.02.2013

@author: philkraf
'''
import sys
from datetime import datetime, timedelta
from .. import db
from glob import glob
import os.path as op
import os
from configparser import RawConfigParser
from io import StringIO
from math import isnan

import chardet

import ast

from .. import conf
# AbstractImport
from traceback import format_exc as traceback
from pytz import common_timezones_set
from sqlalchemy import func

from ..dataimport.importlog import LogColumns


def findStartDate(siteid, instrumentid):
    session = db.Session()
    ds = session.query(db.Dataset).filter(db.Dataset._site == siteid,
                                          db.Dataset._source == instrumentid)\
        .order_by(db.Dataset.end.desc()).first()
    if ds:
        return ds.end
    else:
        return None


def finddateGaps(siteid, instrumentid, valuetype, startdate=None, enddate=None):
    """

    Find gaps in with given params

    :param siteid:
    :param instrumentid:
    :param valuetype:
    :param startdate:
    :param enddate:
    :return:
    """
    print("[LOG] - finddateGaps - START")
    print("[LOG] - finddateGaps - valutype(s) list=%s" % valuetype)

    with db.session_scope() as session:

        dss = session.query(db.Dataset) \
            .filter(db.Dataset._site == siteid,
                    db.Dataset._source == instrumentid,
                    db.Dataset._valuetype.in_(valuetype)) \
            .order_by(db.Dataset._valuetype, db.Dataset.start)

        print("[LOG] - finddateGaps - %d rows after query" % dss.count())

        if dss.count() != 0:
            # Filter for datasets which are in our period
            if startdate:
                dss = dss.filter(db.Dataset.end > startdate)
                print("[LOG] - finddateGaps - %d rows after startdatefilter %s" %
                      (dss.count(), startdate))
            else:
                print("[LOG] - finddateGaps - No startdate")
            if enddate:
                dss = dss.filter(db.Dataset.start < enddate)
                print("[LOG] - finddateGaps - %d rows after enddatefilter %s" %
                      (dss.count(), enddate))
            else:
                print("[LOG] - finddateGaps - No enddate")

        # Check if their are datasets in our period
        if dss is None or dss.count() == 0:
            # There is no data. Allow full upload
            if startdate and enddate:
                print("[LOG] - finddateGaps - Full upload allowed / ",
                      startdate, " ", enddate, " /")
                return [(startdate, enddate)]
            else:
                print("[LOG] - finddateGaps - No datasets")
                return None

        # Make start and enddate if not present
        if not startdate:
            print("[LOG] - finddateGaps - Create startdate at ", dss[0].start)
            startdate = dss[0].start
        if not enddate:
            print("[LOG] - finddateGaps - Create enddate at ", dss[-1].end)
            enddate = dss[-1].end

        # Start search
        res = []

        # Is there space before the first dataset?
        if startdate < dss[0].start:
            print("[LOG] - finddateGaps - Append %s - %s - v:%s" %
                  (startdate, dss[0].start, dss[0].valuetype))
            res.append((startdate, dss[0].start))

        # Check for gaps>1 day between datasets
        for ds1, ds2 in zip(dss[:-1], dss[1:]):
            # if there is a gap between
            if ds2.start - ds1.end >= timedelta(days=1):
                print("[LOG] - finddateGaps - Append %s - %s - v:%s - v:%s" %
                      (ds1.end, ds2.start, ds1.valuetype, ds2.valuetype))
                res.append((ds1.end, ds2.start))

        # Is there space after the last dataset
        if enddate > dss[-1].end:
            print("[LOG] - finddateGaps - Append %s - %s - v:%s" %
                  (dss[-1].end, enddate, dss[-1].valuetype))
            res.append((dss[-1].end, enddate))

        print("[LOG] - finddateGaps - Returning %d gap(s)" % len(res))
        return res

class ImportColumn:
    """
    Describes the content of a column in a delimited text file
    """

    def __init__(self, column, name, valuetype, factor=1.0, comment=None,
                 difference=None, minvalue=-1e308, maxvalue=+1e308, append=None,
                 level=None, access=None, ds_column=None):
        """
        Creates a column description in a delimited text file.
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
        level: Level property of the dataset. Use this for Instruments measuring at one site in different depth
        access: Access property of the dataset
        ds_column: explicit dataset for uploading column @see: mm.py
        """
        self.column = int(column)
        self.name = name
        self.valuetype = int(valuetype)
        self.comment = comment
        self.factor = factor or 1.0
        self.difference = difference
        self.minvalue = minvalue
        self.maxvalue = maxvalue
        self.append = append
        self.level = level
        self.access = access
        self.ds_column = ds_column

    def __str__(self):
        return "%s[%s]:column=%i" % ('d' if self.difference else '', self.name,
                                     self.column)

    def to_config(self, config, section):
        """
        Writes the colummn description to a config file
        """
        config.set(section, '; 0 based column number')
        config.set(section, 'column', self.column)
        config.set(
            section, '; name of the field, will become name of the dataset')
        config.set(section, 'name', self.name)
        config.set(section, '; id of the valuetype in this field')
        config.set(section, 'valuetype', self.valuetype)
        config.set(section, '; factor for unit conversion')
        config.set(section, 'factor', self.factor)

        if self.comment:
            config.set(section, 'comment', self.comment)

        if self.difference is not None:
            config.set(
                section, '; if Yes, the import will save the difference to the last value')
            config.set(section, 'difference', self.difference)
        config.set(section, '; lowest allowed value, use this for NoData values')
        config.set(section, 'minvalue', self.minvalue)
        config.set(section, '; highest allowed value, use this for NoData values')
        config.set(section, 'maxvalue', self.maxvalue)
        if self.level:
            config.set(
                section, '; Level property of the dataset. Use this for Instruments measuring at one site in different depth')
            config.set(section, 'level', self.level)
        if self.access is not None:
            config.set(section, '; Access property of the dataset. Default level is 1 (for loggers) but can set to 0 for public datasets or to a higher level for confidential datasets')
            config.set(section, 'access', self.access)
        if self.ds_column is not None:
            config.set(section, '; Explicit dataset id for column to upload to')
            config.set(section, 'ds_column', self.ds_column)

    @classmethod
    def from_config(cls, config, section):
        "Get the column description from a config-file"
        def getvalue(option, type=str):
            if config.has_option(section, option):
                return type(config.get(section, option))
            else:
                return None
        return cls(column=config.getint(section, 'column'),
                   name=config.get(section, 'name'),
                   valuetype=config.getint(section, 'valuetype'),
                   factor=config.getfloat(section, 'factor'),
                   comment=getvalue('comment'),
                   difference=getvalue('difference'),
                   minvalue=getvalue('minvalue', float),
                   maxvalue=getvalue('maxvalue', float),
                   append=getvalue('append', int),
                   level=getvalue('level', float),
                   access=getvalue('access', int),

                   # Added as lab import (mm.py) feature
                   ds_column=getvalue('ds_column', int)
                   )


def config_getdict(config, section, option):
    """
    Helper method to parse map values in .conf files

    :param config:
    :param section:
    :param option:
    :return:
    """
    try:
        if config.has_option(section, option):
            return ast.literal_eval(config.get(section, option))
        else:
            return {}
    except ValueError:
        raise ValueError('Config file attribute {} is no valid dict type'.format(option))


class ImportDescription(object):
    """
    Describes the file format and content of a delimited text file for
    import to the database.
    """

    def __init__(self, instrument, skiplines=0, delimiter=',', decimalpoint='.',
                 dateformat='%d/%m/%Y %H:%M:%S', datecolumns=(0, 1),
                 timezone=conf.CFG_DATETIME_DEFAULT_TIMEZONE, project=None,
                 nodata=[], worksheet=1, sample_mapping=None):
        """
        instrument: the database id of the instrument that produced this file
        skiplines: The number of lines prepending the actual data
        delimiter: The delimiter sign of the columns. Use TAB for tab-delimited columns, otherwise ',' or ';'
        decimalpoint: Symbol used to separate decimal place
        dateformat: ...
        datecolumns: ...
        timezone: str in pytz format
        project: str project for the dataset to link to. Optional.
        nodata: list of values that don't represent valid data. E.g. ['NaN']. Is optional and default is empty list.
        worksheet: The position of the worksheet of an excel file. Optional and default is the first (1)
        sample_mapping: Mapping of labcodes to site ids. Is Optional and default is None
        """
        self.name = ''
        self.fileextension = ''
        self.instrument = int(instrument)
        self.skiplines = skiplines
        self.delimiter = delimiter
        # Replace space and tab keywords
        if self.delimiter and self.delimiter.upper() == 'TAB':
            self.delimiter = '\t'
        elif self.delimiter and self.delimiter.upper() == 'SPACE':
            self.delimiter = None
        self.decimalpoint = decimalpoint
        self.dateformat = dateformat
        self.filename = ''
        try:
            self.datecolumns = tuple(datecolumns)
        except:
            self.datecolumns = datecolumns,
        self.columns = []

        # New added for feature
        self.timezone = timezone  # Timezone for the dataset
        self.project = project  # Project for the dataset

        # New added after bug in equador database with blank data lines
        if isinstance(nodata, list):
            self.nodata = nodata
        else:
            self.nodata = []
            raise ValueError(
                "nodata value %s has to be an instance of a list" % nodata)

        # added after some issues with xls-files where the data worksheet
        # wasn't the first one
        if worksheet is None:
            worksheet = 1
        self.worksheet = worksheet

        # Sample mapping can be None
        self.sample_mapping = sample_mapping

    def __str__(self):
        io = StringIO()
        self.to_config().write(io)
        return io.getvalue()

    def addcolumn(self, column, name, valuetype, factor=1.0, comment=None, difference=None, minvalue=-1e308, maxvalue=1e308):
        """
        Adds the description of a column to the file format description
        """
        self.columns.append(ImportColumn(
            column, name, valuetype, factor, comment, difference))
        return self.columns[-1]

    def to_config(self):
        """
        Returns a ConfigParser.RawConfigParser with the data of this description
        """
        config = RawConfigParser(allow_no_value=True)
        session = db.Session()
        inst = session.query(db.Datasource).get(self.instrument)
        if not inst:
            raise ValueError(
                'Error in import description: %s is not a valid instrument id')
        session.close()
        section = str(inst)
        config.add_section(section)
        config.set(section, 'instrument', self.instrument)
        config.set(section, 'skiplines', self.skiplines)
        # Replace space and tab by keywords
        config.set(section, 'delimiter', {' ': 'SPACE', '\t': 'TAB'}.get(
            self.delimiter, self.delimiter))
        config.set(section, 'decimalpoint', self.decimalpoint)
        config.set(section, 'dateformat', self.dateformat)
        config.set(section, 'datecolumns', str(self.datecolumns).strip('(), '))
        config.set(section, 'project', self.project)
        config.set(section, 'timezone', self.timezone)
        config.set(section, 'nodata', self.nodata)
        config.set(section, 'worksheet', self.worksheet)
        if self.sample_mapping:
            config.set(section, 'sample_mapping', self.sample_mapping)
        if self.fileextension:
            config.set(section, 'fileextension', self.fileextension)
        for col in self.columns:
            section = col.name
            config.add_section(section)
            col.to_config(config, section)
        return config

    @classmethod
    def from_config(cls, config):
        """
        Creates a TextImportDescriptor from a ConfigParser.RawConfigParser
        by parsing its content
        """
        def getvalue(section, option, type=str):
            if config.has_option(section, option):
                return type(config.get(section, option))
            else:
                return None

        def config_getlist(section, option):
            if config.has_option(section, option):
                return ast.literal_eval(config.get(section, option))
            else:
                return []

        sections = config.sections()
        if not sections:
            raise IOError('Empty config file')

        # Check integrity of the data
        with db.session_scope() as session:

            # Get the data which shall be checked
            project = getvalue(sections[0], 'project')
            timezone = getvalue(sections[0], 'timezone')

            if project:
                rows = session.query(db.Project)\
                    .filter(db.Project.id == project).count()
                if rows != 1:
                    raise ValueError('Error in import description: \'%s\' is no'
                                     ' valid project identifier' % project)

            if timezone:
                # Search in pytz's "set" cause of the set is faster than the
                # list
                if timezone not in common_timezones_set:
                    raise ValueError('Error in import description: \'%s\' is no'
                                     ' valid timezone' % timezone)

        # Create a new TextImportDescriptor from config file
        tid = cls(instrument=config.getint(sections[0], 'instrument'),
                  skiplines=config.getint(sections[0], 'skiplines'),
                  delimiter=getvalue(sections[0], 'delimiter'),
                  decimalpoint=getvalue(sections[0], 'decimalpoint'),
                  dateformat=getvalue(sections[0], 'dateformat'),
                  datecolumns=config_getlist(sections[0], 'datecolumns'),
                  project=getvalue(sections[0], 'project'),
                  timezone=getvalue(sections[0], 'timezone'),
                  nodata=config_getlist(sections[0], 'nodata'),
                  worksheet=getvalue(sections[0], 'worksheet', int),
                  sample_mapping=config_getdict(config, sections[0], 'sample_mapping'))
        tid.name = sections[0]
        for section in sections[1:]:
            tid.columns.append(ImportColumn.from_config(config, section))
        return tid

    @classmethod
    def from_file(cls, path, stoppath='datafiles', pattern='*.conf'):
        """
        Searches in the parent directories of the given path for .conf file
        until the stoppath is reached.
        """
        # As long as no *.conf file is in the path
        while not glob(op.join(path, pattern)):
            # Go to the parent directory
            path = op.dirname(path)
            # if stoppath is found raise an error
            if op.basename(path) == stoppath:
                raise IOError('Could not find .conf file for file description')
        # Use the first .conf file in the directory
        path = glob(op.join(path, pattern))[0]
        # Create a config
        config = RawConfigParser()
        # Load from the file

        try:
            config.read_file(open(path))
        except UnicodeDecodeError:
            rawdata = open(path, 'rb').read()
            result = chardet.detect(rawdata)

            # if chardet can't detect encoding
            if result['encoding'] is None:
                result['encoding'] = 'unknown'

            msg = "Your config at {} is encoded in {}. Please make sure you encode your config in ascii or utf-8"\
                .format(path, result['encoding'])
            raise RuntimeError(msg)

        # Return the descriptor
        descr = cls.from_config(config)
        descr.filename = path
        return descr


class LogImportColumn(ImportColumn):

    def __init__(self):

        # TODO: define fallback dataset attribute
        pass

    @classmethod
    def to_config(cls, config, section):
        # TODO: define fallback dataset
        pass

    @classmethod
    def from_config(cls, config, section):
        """
        Get the column description from a config-file
        """
        ImportColumn.from_config(config, section)

        def getvalue(option, type=str):
            if config.has_option(section, option):
                return type(config.get(section, option))
            else:
                return None

        return cls(column=config.getint(section, 'column'),
                   name=config.get(section, 'name'),
                   valuetype=config.getint(section, 'valuetype'),
                   factor=config.getfloat(section, 'factor'),
                   comment=getvalue('comment'),
                   difference=getvalue('difference'),
                   minvalue=getvalue('minvalue', float),
                   maxvalue=getvalue('maxvalue', float),
                   append=getvalue('append', int),
                   level=getvalue('level', float),
                   access=getvalue('access', int)
                   )


class LogImportDescription(ImportDescription):
    """
    Temporary Helper Class
    """
    # TODO: Refactor this into new class hierarchy

    def __init__(self, instrument, skiplines=0, delimiter=',', decimalpoint='.',
                 dateformat='%d/%m/%Y %H:%M:%S', datecolumns=(0, 1),
                 timezone=conf.CFG_DATETIME_DEFAULT_TIMEZONE, project=None,
                 site=None, dataset=None, value=None, logtext=None, msg=None,
                 worksheet=1, nodata=[], sample_mapping=None):
        """
        instrument: the database id of the instrument that produced this file
        skiplines: The number of lines prepending the actual data
        delimiter: The delimiter sign of the columns. Use TAB for tab-delimited columns, otherwise ',' or ';'
        """

        self.site = site
        self.dataset = dataset
        self.value = value
        self.logtext = logtext
        self.msg = msg

        super(LogImportDescription, self)\
            .__init__(instrument, skiplines, delimiter, decimalpoint,
                      dateformat, datecolumns, timezone, project, nodata=nodata,
                      worksheet=worksheet, sample_mapping=sample_mapping)

    @classmethod
    def from_config(cls, config):
        """
        Creates a TextImportDescriptor from a ConfigParser.RawConfigParser
        by parsing its content
        """

        def getvalue(section, option, type=str):
            if config.has_option(section, option):
                return type(config.get(section, option))
            else:
                return None

        sections = config.sections()
        if not sections:
            raise IOError('Empty config file')

        # Check integrity of the data
        with db.session_scope() as session:

            # Get the data which shall be checked
            project = getvalue(sections[0], 'project')
            timezone = getvalue(sections[0], 'timezone')

            if project:
                rows = session.query(db.Project) \
                    .filter(db.Project.id == project).count()
                if rows != 1:
                    raise ValueError('Error in import description: \'%s\' is no'
                                     ' valid project identifier' % project)

            if timezone:
                # Search in pytz's "set" cause of the set is faster than the
                # list
                if timezone not in common_timezones_set:
                    raise ValueError('Error in import description: \'%s\' is no'
                                     ' valid timezone' % timezone)

        # Create a new TextImportDescriptor from config file

        tid = cls(instrument=config.getint(sections[0], 'instrument'),
                  skiplines=config.getint(sections[0], 'skiplines'),
                  delimiter=getvalue(sections[0], 'delimiter'),
                  decimalpoint=getvalue(sections[0], 'decimalpoint'),
                  dateformat=getvalue(sections[0], 'dateformat'),
                  datecolumns=eval(config.get(sections[0], 'datecolumns')),
                  project=getvalue(sections[0], 'project', int),
                  timezone=getvalue(sections[0], 'timezone'),
                  site=getvalue(sections[0], 'sitecolumn', int),
                  dataset=getvalue(sections[0], 'dataset', int),
                  value=getvalue(sections[0], 'value', float),
                  logtext=getvalue(sections[0], 'logtext'),
                  msg=getvalue(sections[0], 'msg'),
                  worksheet=getvalue(sections[0], 'worksheet', int),
                  sample_mapping=config_getdict(config, sections[0], 'sample_mapping')
                  )
        tid.name = sections[0]
        for section in sections[1:]:
            tid.columns.append(ImportColumn.from_config(config, section))
            print(tid.columns)
        return tid

    def to_columns(self):

        date = None
        time = None

        if len(self.datecolumns) == 1:
            date = self.datecolumns[0]

        if len(self.datecolumns) == 2:
            date = self.datecolumns[0]
            time = self.datecolumns[1]

        res = LogColumns(
            date=date,
            time=time,
            datetime=None,
            site=self.site,
            dataset=self.dataset,
            value=self.value,
            logtext=self.logtext,
            msg=self.msg,
            sample=None
        )
        return res


class ImportStat(object):
    def __init__(self, sum=0.0, min=1e308, max=-1e308, n=0, start=datetime(2100, 1, 1), end=datetime(1900, 1, 1)):
        self.sum, self.min, self.max, self.n, self.start, self.end = sum, min, max, n, start, end

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
        return dict(mean=self.mean, min=self.min, max=self.max, n=self.n, start=self.start, end=self.end)


class AbstractImport(object):
    """ This class imports provides functionality for importing files to the
    database, using a config file. The config file describes the format and
    gives necessary meta data, as the instrument, and the value types of the
    columns. The conf file should be in the same directory as the text file or
    somewhere up the directory tree, but below the datafiles directory."""

    def __init__(self, filename, user, siteid, instrumentid, startdate,
                 enddate):
        self.filename = filename
        self.name = op.basename(self.filename)
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
        datasets = {}
        for k in self.datasets:
            datasets[k] = db.Dataset.get(session, self.datasets[k])

        # A dict to hold the current record id for each column k
        def newid(k):
            return (session.query(db.sql.func.max(db.Record.id))
                    .filter(db.Record._dataset == datasets[k].id).scalar() or 0) + 1
        recid = dict((k, newid(k)) for k in self.datasets)

        # A dict to cache the value entries for committing for each column k
        records = dict((k, []) for k in self.datasets)

        try:
            # Loop through all values

            for i, d in enumerate(self.loadvalues()):

                # TODO: Fix possibilty that nan-values can uploaded into the database
                # see self.get_statistics

                # Get time of record
                t = d['d']

                # Loop through columns
                for col in self.descriptor.columns:
                    k = col.column

                    # If there is a value for column k
                    if not d[k] is None:
                        records[k].append(
                            dict(dataset=datasets[k].id, id=recid[k], time=t, value=d[k]))

                        # Next id for column k
                        recid[k] += 1

                # To protected the memory, commit every 10000 items
                if (i + 1) % self.commitinterval == 0:
                    records = self.raw_commit(records)

            # Commit remaining records
            records = self.raw_commit(records)

            # Update start and end of the datasets
            for k, ds in datasets.items():
                ds.start = session.query(db.sql.func.min(
                    db.Record.time)).filter_by(dataset=ds).scalar()
                ds.end = session.query(db.sql.func.max(
                    db.Record.time)).filter_by(dataset=ds).scalar()
            # Commit changes to the session
            session.commit()

        except:
            # Something wrong? Write to error stream
            self.errorstream.write(traceback())
            session.rollback()

        finally:
            session.close()

    # Use sqlalchemy.core for better performance
    def raw_commit(self, records):
        "Commits the records to the Record table, and clears the records-lists"
        for k, rec in records.items():
            if rec:
                db.engine.execute(db.Record.__table__.insert(), rec)
        # Return a dict like records, but with empty lists
        return dict((r, []) for r in records)

    def createdatasets(self, comment='', verbose=False):
        """
        Creates the datasets according to the descriptor
        """
        session = db.Session()

        # Get instrument, user and site object from db
        inst = session.query(db.Datasource).get(self.instrumentid)
        user = session.query(db.Person).get(self.user)
        site = session.query(db.Site).get(self.siteid)

        # Get "raw" as data quality, to use as a default value
        raw = session.query(db.Quality).get(0)
        for col in self.descriptor.columns:
            # Get the valuetype (vt) from db
            vt = session.query(db.ValueType).get(col.valuetype)
            id = db.newid(db.Dataset, session)
            # New dataset with metadata from above
            ds = db.Timeseries(id=id, measured_by=user, valuetype=vt, site=site, name=col.name,
                               filename=self.filename, comment=col.comment, source=inst, quality=raw,
                               start=self.startdate, end=datetime.today(), level=col.level,
                               access=col.access if col.access is not None else 1,
                               # Get timezone from descriptor or, if not present from global conf
                               timezone=self.descriptor.timezone or conf.CFG_DATETIME_DEFAULT_TIMEZONE,
                               project=self.descriptor.project)
            self.datasets[col.column] = ds.id
        session.commit()
        session.close()

    def parsedate(self, timestr):
        """
        Parses a datestring according to the format given in the description.
        The description should either be a valid python formatstring, like %Y/%m/%d %H:%M
        or "excel" to parse float values as in excel to a date.
        """
        if self.descriptor.dateformat.lower() == 'excel':
            t0 = datetime(1899, 12, 30)
            timestr = timestr.split()
            if len(timestr) == 1:
                timefloat = float(timestr[0])
                days = int(timefloat)
                seconds = round((timefloat % 1) * 86400)
                return t0 + timedelta(days=days, seconds=seconds)
            elif len(timestr) == 2:
                days = int(timestr[0])
                seconds = round((float(timestr[1]) % 1) * 86400)
                return t0 + timedelta(days=days, seconds=seconds)
        else:
            return datetime.strptime(timestr, self.descriptor.dateformat)

    def parsefloat(self, s):
        """
        parses a string to float, using the decimal point from the descriptor
        """
        s = s.replace(self.descriptor.decimalpoint, '.')
        return float(s)

    def get_statistic(self):
        """
        Returns a column name - ImportStat dictionary with the statistics for each import column
        """
        stats = dict((col.column, ImportStat())
                     for col in self.descriptor.columns)

        for d in self.loadvalues():
            alreadyWarned = False
            for col in self.descriptor.columns:
                k = col.column
                if d[k] is not None:
                    if isnan(d[k]):
                        if not alreadyWarned:
                            self.errorstream.write("WARNING: Nan value present for row {}\n".format(d['d']))
                            alreadyWarned = True
                    else:
                        stats[k].sum += d[k]
                        stats[k].max = max(stats[k].max, d[k])
                        stats[k].min = min(stats[k].min, d[k])
                        stats[k].n += 1
                        stats[k].start = min(d['d'], stats[k].start)
                        stats[k].end = max(d['d'], stats[k].end)
        return dict((col.name, stats[col.column]) for col in self.descriptor.columns)

    def loadvalues(self):
        raise NotImplementedError("Use an implementation class")

    @staticmethod
    def extension_fits_to(filename):
        """
        Here should be the implemenation for making a decision by a filename if
        a file can be processed by this class

        :param: filename
        :return: Returns true if a file is applicable for an import class
        """
        raise NotImplementedError("Use an implementation class")

    def upload(self, new_dataset, dataset):

        MAX_ROWS = 100

        # TODO: Move this to the dataset.py
        def overlap(d1, d2):
            # d1 is inside d2
            if d2.start < d1.start < d2.end:
                return True
            elif d2.end > d1.end > d2.start:
                return True
            # d2 is inside d1
            if d1.start < d2.start < d1.end:
                return True
            elif d1.end > d2.end > d1.start:
                return True
            return False

        def get_report():
            pass

        # new_dataset, dataset are valid datasets
        # dataset.start < dataset.end

        if not overlap(new_dataset, dataset):
            # upload
            print("Upload completed successful")
        else:
            print("Report conflicts")
            if new_dataset.count() > MAX_ROWS:

                if dataset.count() > MAX_ROWS:

                    print("Normally no upload allowed")
                    # Only for Admins
                    # Except other

                else:
                    uploadable, conflicts = get_report(dataset, new_dataset)
            else:
                uploadable, conflicts = get_report(new_dataset, dataset)

            if conflicts.real == 0:
                print("Allow normal merge")

            else:
                print("Print multiple choice")


def savetoimports(filename, user, datasets=None):
    """
    Adds the filename to the import history file .import.hist
    """
    print(("savetoimports:", filename))
    d = os.path.dirname(filename)
    f = open(os.path.join(d, '.import.hist'), 'a')
    f.write('%s,%s,%s' % (os.path.basename(filename), user, datetime.now()))
    for ds in datasets:
        f.write(',ds%s' % ds)
    f.write('\n')
    f.close()


# TODO: Rebuild this with database mechanism. Make things more independent
def checkimport(filename):
    print(("checkimport:", filename))
    d = os.path.dirname(filename)
    fn = os.path.join(d, '.import.hist')
    if os.path.exists(fn):
        f = open(fn)
        b = os.path.basename(filename)
        for l in f:
            ls = l.split(',', 3)
            if b in ls[0]:
                d = dict(fn=ls[0], dt=ls[2], u=ls[1], ds=ls[3])
                return "%(u)s has already imported %(fn)s at %(dt)s as %(ds)s" % d
    return ''
