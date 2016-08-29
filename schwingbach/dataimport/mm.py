from cStringIO import StringIO
from pprint import pprint

import xlrd
from os.path import basename, splitext
from datetime import datetime, timedelta
import cherrypy

from base import AbstractImport, ImportDescription, ImportColumn, ImportStat, LogImportDescription
from dataimport.importlog import LogbookImport, LogImportError
from xls import XlsImport
import conf
from re import search, sub

import db
from pytz import common_timezones_set

class ILogColumn():

    date = None
    time = None
    datetime = None
    site = None
    dataset = None
    value = None
    logtext = None
    msg = None
    sample = None


class ManualMeasurementsColumns(ILogColumn):

    def __init__(self, config, section):

        def getvalue(option, t=str):
            if config.has_option(section, option):
                return t(config.get(section, option))

            else:
                return None

        self.column = config.getint(section, 'column'),
        self.name = config.get(section, 'name'),
        self.valuetype = config.getint(section, 'valuetype'),
        self.factor = config.getfloat(section, 'factor'),
        self.comment = getvalue('comment'),
        self.difference = getvalue('difference'),
        self.minvalue = getvalue('minvalue', float),
        self.maxvalue = getvalue('maxvalue', float),
        self.append = getvalue('append', int),
        self.level = getvalue('level', float),
        self.access = getvalue('access', int)


class ManualMeasurementsImport(LogbookImport):
    """
    Importclass for Manual Measurements
    """

    def __init__(self, filename, user, configfile=None, sheetName=None, config=None):

        err = StringIO()
        self.filename = filename
        self.sheet = XlsImport.open_sheet(xlrd.open_workbook(filename, on_demand=True), filename, err)
        with db.session_scope() as session:
            self.user = db.Person.get(session, user)
        self.sheetName = sheetName

        self.descr = LogImportDescription.from_file(filename)
        self.columns = self.descr.to_columns()

        #self.filename = configfile.file

    def __call__(self, commit=False):
        session = db.Session()
        logs = []
        errors = {}

        start = 0 + self.descr.skiplines
        end = self.sheet.nrows

        cherrypy.log("Rows in calling mm: %d" % self.sheet.nrows)

        try:
            for row in xrange(start, end):
                if self.sheet.cell_value(row, 1):
                    row_has_error = False
                    for valuetype_column in self.descr.columns:
                        try:
                            log = self.importrow(session, row, valuetype_column=valuetype_column)
                            logs.append(dict(row=row,
                                             error=False,
                                             log=log))

                        except LogImportError as e:
                            if not e.is_valuetype_error and row_has_error:
                                continue
                            errors[e.row] = e.text.decode('utf-8')
                            logs.append(dict(row=row,
                                             error=True,
                                             log=e.text))
                            row_has_error = True

            if commit and not errors:
                session.commit()

        finally:
            session.close()

        return logs, not errors

    # TODO: rename LogColumns -> self.columns (holding (an instance of) class
    # with attributes for importrow (check if all attributes are set))
    def importrow(self, session, row, valuetype_column=None):
        """
        Imports a row from the excel file as log or record

        :param session: Database session connector
        :param row: Data to be imported
        """

        # Get date and time
        try:
            date = self.get_date(row, self.columns.date)
            time = self.get_date(row, self.columns.time)
            dt = self.get_datetime(row)

        except:
            raise LogImportError(row, 'Could not read date and time')

        # Get site
        site, err = self.get_obj(session, db.Site, row, self.columns.site)
        if err:
            raise LogImportError(row, err)

        elif not site:
            raise LogImportError(row, 'Missing site')

        # Dataset

        # get dataset from column, if existent
        if self.descr.dataset is not None:
            ds, err = self.get_obj(session, db.Dataset, row, self.descr.dataset)

        # otherwise compute it from valuetype and siteid out of the database
        else:
            # Get datset (if existent)
            ds, len, err = self.get_latest_dataset(session, valuetype_column.valuetype, site.id)
            if err:
                raise LogImportError(row, err)

        # If dataset is not manual measured or dataset is not at site throw
        # error
        if ds and (ds.source is None or ds.source.sourcetype != 'manual'):
            raise LogImportError(row, '%s is not a manually measured dataset, '
                                      'if the dataset is correct please change '
                                      'the type of the datasource to manual'
                                 % ds)

        elif ds and ds.site != site:
            raise LogImportError(row, '%s is not at site #%i' % (ds, site.id))

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

        if (not v is None) and ds is None:
            raise LogImportError(row, "A value is given, but no dataset")

        # all record attributes ok
        # now check if a record is already in the database for that special timestamp
        record = session.query(db.Record).filter(db.Record.dataset == ds,
                                                 db.Record.time == dt,
                                                 db.Record.is_error == False).count()
        if record == 1:
            raise LogImportError(row, "For dataset '%s' and time '%s', there is already a record in database" %
                                 (ds, dt))
        elif record > 1:
            raise LogImportError(row, "For dataset '%s' and the time '%s', there are multiple records already in the "
                                      "database" % (ds, dt))


        # Get logtype and message (for logs or as record comment)
        logtype = None
        msg = None
        #logtype, msg = self.get_value(row, (self.columns.logtext, self.columns.msg))

        # Get job, currently disabled. Column 7 hold the sample name
        # job,err = self.get_obj(session, db.Job, row, self.columns.job)
        # if err: raise LogImportError(row,'%s in not a valid Job.id')
        job = None

        # Get the sample name if present
        try:
            sample = self.get_value(row, self.columns.sample)

        except:
            sample = None

        # TODO: Is this really necessary (low pri)
        # If dataset and value present (import as record)
        if ds and not v is None:

            # Extent time of dataset
            if ds.start > date or ds.records.count() == 0:
                ds.start = date

            if ds.end < date or ds.records.count() == 0:
                ds.end = date

            # Check for duplicate record
            if self.recordexists(ds, date):
                raise LogImportError(row, '%s has already a record at %s' % (ds, date))

            else:
                try:
                    ds.addrecord(value=v,
                                 time=date,
                                 comment=msg,
                                 sample=(sample if sample else None))

                except ValueError as e:
                    raise LogImportError(row, e.message)

            # Check for duplicate log. If log exists, go on quitely
            if not self.logexists(session, site, date):
                logmsg = 'Measurement:%s=%g %s with %s' % (ds.valuetype.name,
                                                           v,
                                                           ds.valuetype.unit,
                                                           ds.source.name)

                if msg: logmsg += ', ' + msg

                newlog = db.Log(id=db.newid(db.Log, session),
                                user=self.user,
                                time=date,
                                message=logmsg,
                                site=site,
                                type='measurement')
                session.add(newlog)
            return "Add value %g %s to %s (%s)".encode('utf-8') % (v,
                                                    ds.valuetype,
                                                    ds,
                                                    date)

        # if dataset or value are not present, import row as log only
        else:
            if not msg:
                raise LogImportError(row, 'No message to log')

            if self.logexists(session, site, date):
                raise LogImportError(row, 'Log for %s at %s exists already' % (date, site))

            else:

                newlog = db.Log(id=db.newid(db.Log, session),
                                user=self.user,
                                time=date,
                                message=msg,
                                type=logtype,
                                site=site)
                session.add(newlog)
            return u"Log: %s" % newlog

        if job:
            job.make_done(self, date)

    def get_value(self, row, col):

        if isinstance(row, str):
            if row.isdigit():
                row = int(row)

        if isinstance(col, str):
            if col.isdigit():
                col = int(col)

        return super(ManualMeasurementsImport, self).get_value(row, col)

    def get_obj(self, session, cls, row, col):

        if isinstance(row, str):
            if row.isdigit():
                row = int(row)

        if isinstance(col, str):
            if col.isdigit():
                col = int(col)
        return super(ManualMeasurementsImport, self).get_obj(session, cls, row, col)

    def get_time(self, date, time):
        if time is None:
            return None

        return super(ManualMeasurementsImport, self).get_time(date, time)

    def from_config(cls, config, section):
        """
        Get the column description from a config-file
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

        :param filename:
        :return:
        """

        name, ext = splitext(filename)
        return (ext.lower() == '.xls' or ext.lower() == '.xlsx') and \
               search(conf.CFG_MANUAL_MEASUREMENTS_PATTERN, filename)

    def get_date(self, row, date):

        value = self.get_value(row, date)
        if type(value) in [str, unicode]:
            return datetime.strptime(value, self.descr.dateformat)
        elif type(value) == float:
            return self.get_time(value, value)

        raise ValueError("Couldn't read date time")

    def get_latest_dataset(self, session, valuetype, siteid):

        # get manual sources
        sources = session.query(db.Datasource).filter(db.Datasource.sourcetype == 'manual').all()
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

        date = self.get_value(row, self.columns.date)
        time = self.get_value(row, self.columns.time)

        datetime = self.t0 + timedelta(date + time)

        return datetime
