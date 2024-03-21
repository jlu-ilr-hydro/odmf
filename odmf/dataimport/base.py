'''
Created on 07.02.2013

@author: philkraf
'''
import sys
from datetime import datetime, timedelta
from glob import glob
from odmf.tools import Path
import os.path as op
import os
from configparser import RawConfigParser
from io import StringIO
import typing
from charset_normalizer import detect

import ast

from ..config import conf
from pytz import common_timezones_set

from logging import getLogger
logger = getLogger(__name__)



def findStartDate(siteid, instrumentid):
    """
    Looks for a site / instrument combination the end of the last existing timeseries
    :return:
    """
    from .. import db

    with db.session_scope() as session:
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
    from .. import db

    logger.info("finddateGaps - START")
    logger.info("finddateGaps - valutype(s) list=%s" % valuetype)

    with db.session_scope() as session:

        dss = session.query(db.Dataset) \
            .filter(db.Dataset._site == siteid,
                    db.Dataset._source == instrumentid,
                    db.Dataset._valuetype.in_(valuetype)) \
            .order_by(db.Dataset._valuetype, db.Dataset.start)

        logger.info("finddateGaps - %d rows after query" % dss.count())

        if dss.count() != 0:
            # Filter for datasets which are in our period
            if startdate:
                dss = dss.filter(db.Dataset.end > startdate)
                logger.info("finddateGaps - %d rows after startdatefilter %s" %
                      (dss.count(), startdate))
            else:
                logger.info("finddateGaps - No startdate")
            if enddate:
                dss = dss.filter(db.Dataset.start < enddate)
                logger.info("finddateGaps - %d rows after enddatefilter %s" %
                      (dss.count(), enddate))
            else:
                logger.info("finddateGaps - No enddate")

        # Check if their are datasets in our period
        if dss is None or dss.count() == 0:
            # There is no data. Allow full upload
            if startdate and enddate:
                logger.info("finddateGaps - Full upload allowed / ",
                      startdate, " ", enddate, " /")
                return [(startdate, enddate)]
            else:
                logger.info("finddateGaps - No datasets")
                return None

        # Make start and enddate if not present
        if not startdate:
            logger.info("finddateGaps - Create startdate at ", dss[0].start)
            startdate = dss[0].start
        if not enddate:
            logger.info("finddateGaps - Create enddate at ", dss[-1].end)
            enddate = dss[-1].end

        # Start search
        res = []

        # Is there space before the first dataset?
        if startdate < dss[0].start:
            logger.info("finddateGaps - Append %s - %s - v:%s" %
                  (startdate, dss[0].start, dss[0].valuetype))
            res.append((startdate, dss[0].start))

        # Check for gaps>1 day between datasets
        for ds1, ds2 in zip(dss[:-1], dss[1:]):
            # if there is a gap between
            if ds2.start - ds1.end >= timedelta(days=1):
                logger.info("finddateGaps - Append %s - %s - v:%s - v:%s" %
                      (ds1.end, ds2.start, ds1.valuetype, ds2.valuetype))
                res.append((ds1.end, ds2.start))

        # Is there space after the last dataset
        if enddate > dss[-1].end:
            logger.info("finddateGaps - Append %s - %s - v:%s" %
                  (dss[-1].end, enddate, dss[-1].valuetype))
            res.append((dss[-1].end, enddate))

        logger.info("finddateGaps - Returning %d gap(s)" % len(res))
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
        ds_column: explicit dataset for uploading column

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
        if self.append is not None:
            config.set(section, '; Append imported data to existing dataset id')
            config.set(section, 'append', self.append)
        if self.ds_column is not None:
            config.set(section, '; Explicit dataset id for column to upload to')
            config.set(section, 'ds_column', self.ds_column)

    def to_string(self):
        """
        Creates a string representation of the import column in cinfig format
        """
        return f'[{self.name}]\n' + '\n'.join(f'{k} = {v}' for k, v in vars(self).items())

    @classmethod
    def from_config(cls, config, section):
        "Get the column description from a config-file"
        def getvalue(option, type=str):
            if config.has_option(section, option):
                return type(config.get(section, option))
            else:
                return None
        return cls(column=config.getint(section, 'column'),
                   name=section,
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

    @classmethod
    def from_dataset(cls, dataset, column):
        return cls(
            column,
            name=dataset.name,
            valuetype=dataset.valuetype.id,
            comment=dataset.comment,
            minvalue=dataset.valuetype.minvalue,
            maxvalue=dataset.valuetype.maxvalue,
            append=dataset.id,
            level=dataset.level,
            access=dataset.access
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
    Describes how tabular data files should be imported into the database
    """
    columns: typing.List[ImportColumn]
    name: str
    instrument: int
    skiplines: int

    def __init__(self, instrument, skiplines=0, skipfooter=None, delimiter=',', decimalpoint='.',
                 dateformat=None, datecolumns=(0, 1),
                 timezone=conf.datetime_default_timezone, project=None,
                 nodata=[], worksheet=1, samplecolumn=None, sample_mapping=None, encoding=None,
                 total_columns=None):
        """
        instrument: the database id of the instrument that produced this file
        skiplines: The number of lines prepending the actual data
        delimiter: The delimiter sign of the columns. Use TAB for tab-delimited columns, otherwise ',' or ';'
        decimalpoint: Symbol used to separate decimal place
        dateformat: Format of date and time values, eg. %Y-%m-%d
        datecolumns: Column numbers containing measurement time
        timezone: str in pytz format
        project: str project for the dataset to link to. Optional.
        nodata: list of values that don't represent valid data. E.g. ['NaN']. Is optional and default is empty list.
        worksheet: The position of the worksheet of an excel file. Optional and default is the first (1)
        sample_column: Column number containing the name of a sample
        sample_mapping: Mapping of labcodes to site ids. Is Optional and default is None
        total_columns: Total number of columns in file. Can be omitted in most cases,
                       when the column number is varying, it allows to read the file
        """
        self.name = ''
        self.fileextension = ''
        self.instrument = int(instrument)
        self.skiplines = skiplines
        self.skipfooter = skipfooter
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

        self.worksheet = worksheet
        self.samplecolumn = samplecolumn
        # Sample mapping can be None
        self.sample_mapping = sample_mapping
        self.encoding = encoding
        self.total_columns = total_columns
    
    def __str__(self):
        io = StringIO()
        self.to_config().write(io)
        return io.getvalue()

    def get_column_names(self) -> typing.Tuple[typing.List[int], typing.List[str]]:
        """
        Get the column positions and column names to be used by self

        Includess (in that order)
        - date / time columns,
        - data columns,
        - columns referencing specific datasets (ds_column)
        - a column containing sample names if samplecolumn is given

        To be used for file loading eg.

        >>>import pandas as pd
        >>>idescr = ImportDescription()
        >>>columns, names = idescr.get_column_names()
        >>>pd.read_csv('...', usecols=columns, names=names)
        """

        columns = (
                list(self.datecolumns)
                + [col.column for col in self.columns]
                + [col.ds_column for col in self.columns if col.ds_column]
        )
        names = ['date', 'time'][:len(self.datecolumns)] + [col.name for col in self.columns] + \
                ['dataset for ' + col.name for col in self.columns if col.ds_column]

        if self.samplecolumn:
            columns += [self.samplecolumn]
            names += ['sample']

        return columns, names

    def addcolumn(self, column, name, valuetype, factor=1.0, comment=None, difference=None, minvalue=-1e308, maxvalue=1e308):
        """
        Adds the description of a column to the file format description
        """
        self.columns.append(ImportColumn(
            column, name, valuetype, factor, comment, difference, minvalue=minvalue, maxvalue=maxvalue))
        return self.columns[-1]

    def to_config(self) -> RawConfigParser:
        """
        Returns a ConfigParser.RawConfigParser with the data of this description
        """
        from .. import db
        config = RawConfigParser(allow_no_value=True)
        with db.session_scope() as session:
            inst = session.get(db.Datasource, self.instrument)
            if not inst:
                raise ValueError(
                    'Error in import description: %s is not a valid instrument id')
            section = str(inst)
        config.add_section(section)
        config.set(section, 'instrument', self.instrument)
        config.set(section, 'skiplines', self.skiplines)
        config.set(section, 'skipfooter', self.skipfooter)
        # Replace space and tab by keywords
        config.set(section, 'delimiter', {' ': 'SPACE', '\t': 'TAB'}.get(
            self.delimiter, self.delimiter))
        config.set(section, 'decimalpoint', self.decimalpoint)
        config.set(section, 'dateformat', self.dateformat)
        config.set(section, 'datecolumns', str(self.datecolumns).strip('(), '))
        config.set(section, 'project', self.project)
        config.set(section, 'timezone', self.timezone)
        config.set(section, 'nodata', self.nodata)
        if self.worksheet:
            config.set(section, 'worksheet', self.worksheet)
        if self.sample_mapping:
            config.set(section, 'sample_mapping', self.sample_mapping)
        if self.fileextension:
            config.set(section, 'fileextension', self.fileextension)
        if self.total_columns:
            config.set(section, 'total_columns', self.total_columns)
        for col in self.columns:
            section = col.name
            config.add_section(section)
            col.to_config(config, section)
        return config

    def to_markdown(self) -> str:
        """
        Returns a string in markdown format showing the configuration setting
        """
        conf = self.to_config()
        s = StringIO()
        for section in conf.sections():
            if conf[section]:
                s.write(section + '\n')
                s.write('-' * len(section) + '\n')
                for k, v in conf[section].items():
                    if k[0]!=';':
                        s.write(f'- {k} = {v}\n')
                s.write('\n')
        return s.getvalue()

    @classmethod
    def from_config(cls, config: RawConfigParser):
        """
        Creates a TextImportDescriptor from a ConfigParser.RawConfigParser
        by parsing its content
        """

        from .. import db

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

        # Get the data which shall be checked
        project = getvalue(sections[0], 'project')
        timezone = getvalue(sections[0], 'timezone')

        # Check integrity of the data
        with db.session_scope() as session:


            if project:
                rows = session.query(db.Project)\
                    .filter(db.Project.id == int(project)).count()
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
        tid = cls(
            instrument=config.getint(sections[0], 'instrument', fallback=0),
            skiplines=config.getint(sections[0], 'skiplines', fallback=0),
            skipfooter=config.getint(sections[0], 'skipfooter', fallback=0),
            delimiter=getvalue(sections[0], 'delimiter'),
            decimalpoint=getvalue(sections[0], 'decimalpoint'),
            dateformat=getvalue(sections[0], 'dateformat'),
            datecolumns=config_getlist(sections[0], 'datecolumns'),
            project=getvalue(sections[0], 'project'),
            timezone=getvalue(sections[0], 'timezone'),
            nodata=config_getlist(sections[0], 'nodata'),
            worksheet=getvalue(sections[0], 'worksheet', int),
            samplecolumn=getvalue(sections[0], 'samplecolumn', int),
            encoding=getvalue(sections[0], 'encoding'),
            total_columns=getvalue(sections[0], 'total_columns', int),
            sample_mapping=config_getdict(config, sections[0], 'sample_mapping')
        )

        tid.name = sections[0]
        for section in sections[1:]:
            tid.columns.append(ImportColumn.from_config(config, section))
        return tid

    @classmethod
    def from_file(cls, path, pattern='*.conf'):
        """
        Searches in the parent directories of the given path for .conf file
        until the stoppath is reached.
        """
        # As long as no *.conf file is in the path
        while not glob(op.join(path, pattern)):
            path = op.dirname(path)
            # if stoppath is found raise an error
            if op.basename(path) == op.basename(conf.datafiles) or path == op.dirname(path):
                raise IOError('Could not find .conf file for file description')
        # Use the first .conf file in the directory
        path = glob(op.join(path, pattern))[0]
        # Create a config
        config = RawConfigParser()
        # Load from the file

        try:
            with open(path) as f:
                config.read_file(f)
        except UnicodeDecodeError:
            rawdata = open(path, 'rb').read()
            result = detect(rawdata)

            # if charset_normalizer can't detect encoding
            if result['encoding'] is None:
                result['encoding'] = 'unknown'

            msg = "Your config at {} is encoded in {}. Please make sure you encode your config in ascii or utf-8"\
                .format(path, result['encoding'])
            raise RuntimeError(msg)

        # Return the descriptor
        descr = cls.from_config(config)
        descr.filename = path
        return descr


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


def savetoimports(filename, user, datasets=None):
    """
    Adds the filename to the import history file .import.hist
    """
    logger.info("savetoimports:", filename)
    d = os.path.dirname(filename)
    f = open(os.path.join(d, '.import.hist'), 'a')
    f.write('%s,%s,%s' % (os.path.basename(filename), user, datetime.now()))
    for ds in datasets:
        f.write(',%s' % ds)
    f.write('\n')
    f.close()


def checkimport(filename: Path):
    """
    Checks if
    """
    logger.debug("checkimport:", filename)
    d = filename.parent()
    fn = d + '.import.hist'
    if fn.exists():
        f = open(fn.absolute)
        b = filename.basename
        for l in f:
            fn, user, dt, ds = l.split(',', 3)
            if filename.basename in fn:
                return f'{user} has already imported file:{fn} at {dt} as {ds}'
    return None


def get_last_ds_for_site(session, idescr: ImportDescription, col: ImportColumn, siteid: int):
    """
    Returns the newest dataset for a site with instrument, valuetype and level fitting to the ImportDescription's column
    To be used by lab imports where a site is encoded into the sample name.

    """
    from .. import db
    q = session.query(db.Dataset).filter(
        db.Dataset._site == siteid,
        db.Dataset._valuetype == col.valuetype,
        db.Dataset._source == idescr.instrument,
    )
    if col.level is not None:
        q = q.filter(db.Dataset.level == col.level)

    return q.order_by(db.Dataset.end.desc()).limit(1).scalar()

def compare_section_and_name(fn):
    """
    Helper function to test if section captions for conf files ever differ from the name option
    Parameters
    ----------
    fn: Filename
    """
    from configparser import RawConfigParser
    config = RawConfigParser()
    config.read_file(open(fn))
    return [
        (fn, sect, config.get(sect, 'name'))
        for sect in config.sections()
        if config.has_option(sect, 'name')
    ]

