from io import StringIO

import xlrd
from os.path import basename, splitext
from datetime import datetime, timedelta
import time
import cherrypy

from .base import AbstractImport, ImportDescription, ImportColumn, ImportStat, LogImportDescription
from .base import config_getdict
from ..dataimport.importlog import LogbookImport, LogImportError, ILogColumn
from .xls import XlsImport
from .. import conf
from re import search, sub

from .. import db
from pytz import common_timezones_set


class ManualMeasurementsColumns(ILogColumn):
    """
    More specific LogColumn with full filling the requirements of @ManualMeasurementsImport

    FIXME: Why this derives from ILogColumn when no super class attributes are used?
    """

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
        self.access = getvalue('access', int),
        self.sample_mapping = config_getdict(config, section, 'sample_mapping')

        self.dataset = config.getint(section, 'dataset')


class ManualMeasurementsImport(LogbookImport):
    """
    Importclass for Manual Measurements
    """

    def __init__(self, filename, user, configfile=None, sheetName=None, config=None, descr=None):

        err = StringIO()
        self.filename = filename

        with db.session_scope() as session:
            self.user = db.Person.get(session, user)
        self.sheetName = sheetName

        if descr:
            self.descr = descr
        else:
            self.descr = LogImportDescription.from_file(filename)

        self.columns = self.descr.to_columns()

        self.sheet = XlsImport.open_sheet(
            xlrd.open_workbook(filename, on_demand=True), filename, self.descr.worksheet, err)

        #self.filename = configfile.file

    def __call__(self, commit=False, preload=False):
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

        if preload:
            self.preload()

        self._preload = preload

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

    # TODO: no signifcant performance throughout preload phase, TEST THIS @chris
    def preload(self, session, start, end):
        """
        Preloads ds_columns and site columns

        :param start:
        :param end:
        :return:
        """
        print("Preload starts ...")

        t0 = time.time()

        # preload sites, datasets and valuetypes (performance issue)
        #
        # after the preload they are stored in the look up tables
        # ------------
        # key => value
        # id  => db.Object
        # ------------
        self._sites = dict()
        self._valuetypes = dict()
        self._datasets = dict()

        # stores start, end interval of a datasets recors in the importing file
        # 0 -> start
        # 1 -> end
        # 2 -> count of records between start and end
        # 3 -> count of logs between start and end
        self._times = dict()

        for row in range(start, end):

            # check site and add to lut
            _site = int(self.sheet.cell_value(row, self.descr.site))
            if _site not in list(self._sites.keys()):
                self._sites[int(_site)] = session.query(db.Site).get(_site)

            # check each column of one row
            for column in self.descr.columns:
                # check valuetype of a row and add to lut
                _valuetype = column.valuetype
                if _valuetype not in list(self._sites.keys()):
                    self._valuetypes[int(_valuetype)] = session.query(
                        db.ValueType).get(_valuetype)

                # check dataset column of a valuetype in a row, add to lut
                if column.ds_column:
                    _dataset = int(self.get_value(row, column.ds_column))
                    if _dataset not in list(self._datasets.keys()):
                        self._datasets[int(_dataset)] = session.query(
                            db.Dataset).get(_dataset)

                    # check time intervals of records of a dataset
                    _time = self.get_datetime(row)

                    if _time:
                        if _dataset in list(self._times.keys()):
                            if self._times[_dataset][0] > _time:
                                self._times[_dataset][0] = _time
                            elif self._times[_dataset][1] < _time:
                                self._times[_dataset][1] = _time
                        else:
                            self._times[_dataset] = [_time, _time, -1, -1]

                        if self._times[_dataset][0] > self._times[_dataset][1]:
                            raise RuntimeError("Caching Error. Please debug the "
                                               "file you are importing ...")

        td = timedelta(seconds=30)

        for ds in list(self._times.keys()):
            # if records are in interval from start - td until end + td
            self._times[ds][2] = session.query(db.Record) \
                .filter(db.Record.dataset == self._datasets[ds],
                        db.Record.time >= self._times[ds][0] - td,
                        db.Record.time <= self._times[ds][1] + td,
                        db.Record.is_error == False).count()

            # if logs are in interval from start - timedelta until end + timedelta
            self._times[ds][3] = session.query(db.Log) \
                .filter(db.Log.site == self._datasets[ds].site,
                        db.sql.between(db.Log.time,
                                       self._times[ds][0] - td,
                                       self._times[ds][1] + td)).count()
        t1 = time.time()

        cherrypy.log("Preload in %.2f s" % (t1 - t0))

    # TODO: rename LogColumns -> self.columns (holding (an instance of) class
    # with attributes for importrow (check if all attributes are set))
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
            date = self.get_date(row, self.columns.date)

            if self.columns.time:
                time = self.get_date(row, self.columns.time)

            dt = self.get_datetime(row)

            if dt.minute is not None and dt.hour is not None:
                if dt.day == date.day and dt.month == date.month and dt.year == date.year:
                    date = dt
                else:
                    print("Warning: Something went wrong while parsing the datetime")

        except:
            raise LogImportError(row, 'Could not read date and time')

        # Get site
        site = self.get_value(row, self.columns.site)

        # Use mapping if provided by .conf file
        if self.descr.sample_mapping:
            try:
                key = site
                site = self.descr.sample_mapping[key]
            except KeyError:
                raise LogImportError(row, 'Key {} cannot be found in the .conf file provided mapping'.format(key))

        # use cache
        if self._preload:
            if site not in list(self._sites.keys()):
                raise LogImportError(row, 'Cache error')
            else:
                site = self._sites[site]
        else:
            # Use value fetched from key value mapping from .conf
            if self.descr.sample_mapping:
                site, err = self.get_obj(session, db.Site, row=None, col=None, strvalue=site)
            # Use row, col value else
            else:
                site, err = self.get_obj(session, db.Site, row, self.columns.site)
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
        #logtype, msg = self.get_value(row, (self.columns.logtext, self.columns.msg))

        # Get job, currently disabled. Column 7 hold the sample name
        # job,err = self.get_obj(session, db.Job, row, self.columns.job)
        # if err: raise LogImportError(row,'%s in not a valid Job.id')
        job = None

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

        if job:
            job.make_done(self, date)

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
            search(conf.CFG_MANUAL_MEASUREMENTS_PATTERN, filename)

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

        date = self.get_date(row, self.columns.date)

        # if a time column is given, determine time
        if self.columns.time:
            act_time = self.get_value(row, self.columns.time)

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
