from io import StringIO

import xlrd
from os.path import basename, splitext
from datetime import datetime, timedelta
import time
import cherrypy

from .base import config_getdict, ImportDescription, ImportColumn
from ..dataimport.importlog import LogbookImport, LogImportError
from .xls import XlsImport
from ..config import conf
from re import search, sub

from .. import db
from pytz import common_timezones_set


class LogImportDescription(ImportDescription):
    """
    Temporary Helper Class
    """
    # TODO: Refactor this into new class hierarchy

    def __init__(self, instrument, skiplines=0, delimiter=',', decimalpoint='.',
                 dateformat='%d/%m/%Y %H:%M:%S', datecolumns=(0, 1),
                 timezone=conf.datetime_default_timezone, project=None,
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


class ManualMeasurementsImport:
    """
    Importclass for Manual Measurements
    """

    def __init__(self, filename, user, configfile=None, sheetName=None, config=None, descr=None):

        err = StringIO()
        self.filename = filename

        with db.session_scope() as session:
            self.user = session.query(db.Person).get(user)
        self.sheetName = sheetName

        if descr:
            self.descr: LogImportDescription = descr
        else:
            self.descr = LogImportDescription.from_file(filename)

        self.columns = self.descr.to_columns()

        self.sheet = XlsImport.open_sheet(
            xlrd.open_workbook(filename, on_demand=True), filename, self.descr.worksheet, err)


    def __call__(self, commit=False):
        session = db.Session()
        logs = []
        errors = {}

        start = 0 + self.descr.skiplines
        end = self.sheet.nrows

        cherrypy.log("Rows in calling mm: %d" % self.sheet.nrows)

        # TODO: Make the importrow more performant
        # if self.sheet.nrows > 50:
        #    raise ValueError("Your file has more than 50 rows. This can lead to"
        #                     "a server timeout. Please split your file and "
        #                     "proceed!")


        try:
            for row in range(start, end):
                print(row, " / ", end)
                if self.sheet.cell_value(row, 1):
                    row_has_error = False
                    for valuetype_column in self.descr.columns:
                        try:
                            log = self.importrow(
                                session, row, valuetype_column=valuetype_column, commit=commit)
                            logs.append(dict(row=row,
                                             error=False,
                                             log=log))

                        except LogImportError as e:
                            if not e.is_valuetype_error and row_has_error:
                                continue
                            errors[e.row] = e.text
                            logs.append(dict(row=row,
                                             error=True,
                                             log=e.text))
                            row_has_error = True

            if commit and not errors:
                s = "Commited approx. %s" % len(logs)
                cherrypy.log(s)
                session.commit()

        finally:
            session.close()

        return logs, not errors


    def importrow(self, session, row, valuetype_column=None, commit=False):
        """
        Imports a row from the excel file as log or record

        :param session: Database session connector
        :param row: Data to be imported
        :param valuetype_column: {ImportColumn} a single column, since
                                 importrow is used here to import column-wise
        :param commit: boolean, True if imported rows are commited to the database
        """

        print(("valuetype_column '%s'" % (valuetype_column)))
        time = None

        # Get date and time
        try:
            # TODO: Rework date/time determination, make it consistent for all types of imports
            # TODO: Build test cases for date/time determination
            date = self.get_date(row, self.descr.date)

            if self.descr.time:
                time = self.get_date(row, self.descr.time)

            dt = self.get_datetime(row)

            if dt.minute is not None and dt.hour is not None:
                if dt.day == date.day and dt.month == date.month and dt.year == date.year:
                    date = dt
                else:
                    print("Warning: Something went wrong while parsing the datetime")

        except:
            raise LogImportError(row, 'Could not read date and time')

        # Get site
        site = self.get_value(row, self.descr.site)

        # Use mapping if provided by .conf file
        if self.descr.sample_mapping:
            try:
                key = site
                site = self.descr.sample_mapping[key]
            except KeyError:
                raise LogImportError(row, 'Key {} cannot be found in the .conf file provided mapping'.format(key))

        # use cache
        # Use value fetched from key value mapping from .conf
        if self.descr.sample_mapping:
            site, err = self.get_obj(session, db.Site, row=None, col=None, strvalue=site)
        # Use row, col value else
        else:
            site, err = self.get_obj(session, db.Site, row, self.descr.site)
        if err:
            raise LogImportError(row, err)

        if not site:
            raise LogImportError(row, 'Missing site')

        # valuetype
        valuetype, err = self.get_obj(
            session, db.ValueType, row, valuetype_column)
        if err:
            raise LogbookImport(row, err)

        # Dataset

        # get dataset from column, if existent
        if self.descr.dataset is not None:
            ds, err = self.get_obj(session, db.Dataset,
                                   row, self.descr.dataset)

        if valuetype_column.ds_column is not None:
            ds, err = self.get_obj(session, db.Dataset,
                                   row, valuetype_column.ds_column)

            if err:
                raise LogbookImport(row, err)

        # otherwise compute it from valuetype and siteid out of the database
        else:
            # Get datset (if existent)

            if type(site) == float:
                ds, len, err = self.get_latest_dataset(
                    session, valuetype_column.valuetype, site)
            else:
                ds, len, err = self.get_latest_dataset(
                    session, valuetype_column.valuetype, site.id)

            if err:
                raise LogImportError(row, err)

        # if valuetype_column.ds_column:
        #    ds = int(self.get_value(row, valuetype_column.ds_column))
        #    ds = self._datasets[ds]

        # If dataset is not manual measured or dataset is not at site throw
        # error
        if ds and (ds.source is None or ds.source.sourcetype != 'manual'):
            raise LogImportError(row, '%s is not a manually measured dataset, '
                                      'if the dataset is correct please change '
                                      'the type of the datasource to manual'
                                 % ds)

        elif ds and ds.site.id != site.id:
            raise LogImportError(row, '#%s is not at site #%i' % (ds, site.id))

        elif ds and ds._valuetype != valuetype_column.valuetype:
            raise LogImportError(row, 'Target: #%s has no valuetype #%i' % (
                ds, valuetype_column.valuetype))

        # Get value
        v = None

        # TODO: Refactor this into new class hierachy

        try:
            if self.get_value(row, valuetype_column.column) in self.descr.nodata:
                v = None

            else:
                v = float(self.get_value(row, valuetype_column.column))

        except TypeError:
            v = None

        except ValueError:
            v = None

        if (v is not None) and ds is None:
            raise LogImportError(row, "A value is given, but no dataset")

        # all record attributes ok
        # now check if a record is already in the database for that special timestamp
        # if self._times[ds.id][2] > 0:
        # TODO: check for preload, uncomment line above

        record = session.query(db.Record).filter(db.Record.dataset == ds,
                                                 db.Record.time == dt,
                                                 db.Record.is_error == False).count()
        if record == 1:
            if commit:
                # happens when the database has already a record at this time, in the session
                raise LogImportError(row, "Can't commit possible duplicate row for dataset '%s' and time '%s' "\
                                          "Please inspect your file." % (ds, dt))
            raise LogImportError(row, "For dataset '%s' and time '%s', there is already a record in database" %
                                 (ds, dt))
        elif record > 1:
            raise LogImportError(row, "For dataset '%s' and the time '%s', there are multiple records already in the "
                                      "database" % (ds, dt))

        # Get logtype and message (for logs or as record comment)
        logtype = None
        msg = None

        # Get the sample name if present
        sample = None

        # TODO: Is this really necessary (low pri)
        # If dataset and value present (import as record)
        if ds and v is not None:

            # Extent time of dataset
            if ds.start > date or ds.records.count() == 0:
                ds.start = date

            if ds.end < date or ds.records.count() == 0:
                ds.end = date

            try:
                # if commit to database (as record)
                if commit:
                    ds.addrecord(value=v,
                                 time=date,
                                 comment=msg,
                                 sample=(sample if sample else None))

            except ValueError as e:
                raise LogImportError(row, e.message)

            return "Add value %g %s to %s (%s)" % (v, ds.valuetype, ds, date)
        # if dataset exsist but the value is None the value will not be imported and a warning will be shown
        elif (ds is not None) and v is None:
            return "Warning: None-Value for Site %s at %s will not be added to %s" % (site, date, ds)
        # rais error in case the dataset is none
        else:
            raise LogImportError(row, "A value is given, but no dataset")

    def get_value(self, row, col):
        """
        Calls super get values, casts row and col to int index first
        :param row: excel row index int
        :param col: excel col index int
        :raises TypeError:
        :return: value at excel row and col index
        """
        if isinstance(row, str):
            if row.isdigit():
                row = int(row)

        if isinstance(col, str):
            if col.isdigit():
                col = int(col)

        return super(ManualMeasurementsImport, self).get_value(row, col)

    def get_obj(self, session, cls, row=None, col=None, strvalue=None):
        """
        Calls super get obj, casts row and col to int index first
        :param session: sqlalchemy session object
        :param cls: orm class from odmf.db
        :param row: excel row index
        :param col: excel col index
        :param strvalue:
        :return: orm database obj from id
        """
        if isinstance(row, str):
            if row.isdigit():
                row = int(row)

        if isinstance(col, str):
            if col.isdigit():
                col = int(col)

        return super(ManualMeasurementsImport, self).get_obj(session, cls, row, col, strvalue)

    def get_time(self, date, time):
        """
        Wrapper for calling the super method
        """
        if time is None:
            return None

        return super(ManualMeasurementsImport, self).get_time(date, time)

    @classmethod
    def from_config(cls, config, section):
        """
        Get the column description from a config-file
        :param config:
        """
        def getvalue(option, t=str):
            if config.has_option(section, option):
                return t(config.get(section, option))

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
                   access=getvalue('access', int))

    @staticmethod
    def extension_fits_to(filename):
        """
        Determines if a given filename extension fits to the import
        :param filename: abs filename str
        :return: Boolean, True if filename extension fits to import
        """

        name, ext = splitext(filename)
        return (ext.lower() == '.xls' or ext.lower() == '.xlsx') and \
            search(conf.manual_measurements_pattern, filename)

    def get_date(self, row, date):

        value = self.get_value(row, date)
        if type(value) in [str, str]:
            return datetime.strptime(value, self.descr.dateformat)
        elif type(value) == float:
            return self.get_time(value, value)

        raise ValueError("Couldn't read date time")

    def get_latest_dataset(self, session, valuetype, siteid):
        """
        Helper method
        """

        # get manual sources
        sources = session.query(db.Datasource).filter(
            db.Datasource.sourcetype == 'manual').all()
        # to list
        sources = [src.id for src in sources]

        # search all manual sources with given valuetype and siteid and order by dataset.end for the latest
        datasets = session.query(db.Dataset).filter(db.Dataset._valuetype == valuetype)\
            .filter(db.Dataset._site == siteid)\
            .filter(db.Dataset._source.in_(sources)).order_by(db.Dataset.end.desc())

        if datasets.count() == 0:
            return None, 0, 'No datasets found for valuetype=%s and siteid=%s' % (valuetype, siteid)

        a_datasets = datasets.all()
        dataset = datasets.first()
        length = datasets.count()

        return dataset, length, ''

    def get_datetime(self, row):
        """
        Helper method
        """

        #date = self.get_value(row, self.columns.date)

        date = self.get_date(row, self.descr.date)

        # if a time column is given, determine time
        if self.descr.time:
            act_time = self.get_value(row, self.descr.time)

            date = date + timedelta(act_time)
        # otherwise not
        # else:
            #time = 0

        #datetime = self.t0 + timedelta(date + time)

        # return datetime
        return date

    @classmethod
    def from_file(cls, path):
        # call "super" from file
        # TODO: Inheritance should be super(ManualMeasurementsImport).from_file. See DbImport.logimport()
        return LogImportDescription.from_file(path)
