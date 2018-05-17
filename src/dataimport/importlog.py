"""
Created on 19.02.2013

@author: kraft-p
"""
import xlrd
import os
import db
from datetime import datetime, timedelta


class LogImportError(RuntimeError):
    """
    Error with additional information of the row in the log file
    """

    def __init__(self, row, msg, is_valuetype_error=False):
        RuntimeError.__init__(
            self, "Could not import row %i:%s" % (row + 1, msg))
        self.row = row
        self.text = msg
        self.is_valuetype_error = is_valuetype_error


class LogColumns():
    """
    Enum class a fixed column representation
    """
    date = 0
    time = 1
    datetime = 0, 1
    site = 2
    dataset = 3
    value = 4
    logtext = 5
    msg = 6
    sample = 7

    def __init__(self, date, time, datetime, site, dataset, value, logtext, msg, sample):
        self.date = date
        self.time = time
        self.datetime = datetime
        self.site = site
        self.dataset = dataset
        self.value = value
        self.logtext = logtext
        self.msg = msg
        self.sample = sample

    def __repr__(self):
        return "LogColumns(date=%s, time=%s, datetime=%s, site=%s, dataset=%s, value=%s, logtext=%s, msg=%s, " \
               "sample=%s)" % (
                   self.date, self.time, self.datetime, self.site, self.dataset, self.value, self.logtext, self.msg,
                   self.sample)


class LogbookImport(object):
    """
    Imports from an defined xls file messages to the logbook and append values
    to datasets
    """
    t0 = datetime(1899, 12, 30)

    def get_time(self, date, time):
        if not time:
            return self.t0 + timedelta(date)

        else:
            if time > 1.000001:
                time -= int(time)

            date = int(date)

        return self.t0 + timedelta(date + time)

    def get_obj(self, session, cls, row, col):
        id = None

        # noinspection PyBroadException
        try:
            id = self.sheet.cell_value(row, col)

        except:
            pass

        try:
            if not id:
                return None, None
            obj = session.query(cls).get(int(id))
            if not obj:
                raise Exception('%s.get(%s) not found' % (id, cls))
            return obj, ''
        except Exception as e:
            return None, '%s is not a valid %s id: %s' % (id, cls, e)

    def get_value(self, row, columns):

        try:
            return [self.sheet.cell_value(row, col) for col in columns]

        except:
            try:
                return self.sheet.cell_value(row, columns)
            except TypeError:
                raise TypeError(
                    "List indices row '%s' and col '%s' must be integers" % (row, columns))

    # TODO: Add mechanism to choose a "static" class or a config file
    # for the import. Like:
    # __init__( ... , importWithClass=<Class Identifier>)
    # test interface in mm.py
    def __init__(self, filename, user, sheetname=None, import_with_class=LogColumns, config=None):
        self.filename = filename
        self.workbook = xlrd.open_workbook(filename)
        session = db.Session()
        self.user = db.Person.get(session, user)
        session.close()

        self.columns = import_with_class

        if not self.user:
            raise RuntimeError('%s is not a valid user' % user)

        if sheetname:
            self.sheet = self.workbook.sheet_by_name(sheetname)

        else:
            self.sheet = self.workbook.sheet_by_index(0)

    def __call__(self, commit=False):
        print("CALLING LOG IMPORT")

        session = db.Session()
        logs = []
        errors = {}

        print("Rows in calling: %d" % self.sheet.nrows)

        try:
            for row in range(1, self.sheet.nrows):
                if self.sheet.cell_value(row, 0):
                    try:
                        logs.append(dict(row=row,
                                         error=False,
                                         log=self.importrow(session, row)))

                    except LogImportError as e:
                        errors[e.row] = e.text
                        logs.append(dict(row=row,
                                         error=True,
                                         log=e.text))

            if commit and not errors:
                session.commit()

        finally:
            session.close()

        return logs, not errors

    # FIXME: timetolerance not needed?
    def logexists(self, session, site, time, timetolerance=30):
        """
        Checks if a log at site and time exists in db
        session: an open sqlalchemy session
        site: A site
        time: The time for the log
        timetolerance: the tolerance of the time in seconds
        """
        td = timedelta(seconds=30)

        return session.query(db.Log)\
            .filter(db.Log.site == site,
                    db.sql.between(db.Log.time,
                                   time - td,
                                   time + td)).count() > 0

    def recordexists(self, timeseries, time, timetolerance=30):
        """
        Checks if a record at time exists in dataset

        :param dataset: A timeseries to be checked
        :param time: The time for the record
        :param timetolerance: the tolerance of the time in seconds
        """
        td = timedelta(seconds=30)

        return timeseries.records.filter(
            db.sql.between(db.Record.time,
                           time - td,
                           time + td)).count() > 0

    # TODO: rename LogColumns -> self.columns (holding (an instance of) class
    # with attributes for importrow (check if all attributes are set))
    def importrow(self, session, row):
        """
        Imports a row from the excel file as log or record

        :param session: Database session connector
        :param row: Data to be imported
        """

        # Get date and time
        if len(self.columns.datetime) == 2:
            date, time = self.get_value(row, self.columns.datetime)
            print("DATE %s - TIME %s" % (date, time))
        else:
            date = self.get_value(row, self.columns.date[0])
            print("DATE %s wtih %s" % (date, self.columns.date[0]))

        try:
            time = self.get_time(date, time)

        except:
            raise LogImportError(row, 'Could not read date and time')

        # Get site
        site, err = self.get_obj(session, db.Site, row, self.columns.site)
        if err:
            raise LogImportError(row, err)

        elif not site:
            raise LogImportError(row, 'Missing site')

        # Get datset (if existent)
        ds, err = self.get_obj(session, db.Dataset, row, self.columns.dataset)
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
            # TODO: Nodata comparison here
            value = self.get_value(row, self.columns.value)
            if value is None or value is '':
                v = None
            else:
                v = float(value)

        except TypeError:
            v = None
        except ValueError:
            raise LogImportError(row, "String value '%s' can't be converted to float" %
                                 self.get_value(row, self.columns.value))
            v = None

        if (v is not None) and ds is None:
            raise LogImportError(row, "A value is given, but no dataset")

        # Get logtype and message (for logs or as record comment)
        logtype, msg = self.get_value(
            row, (self.columns.logtext, self.columns.msg))

        # Get job, currently disabled. Column 7 hold the sample name
        #job,err = self.get_obj(session, db.Job, row, self.columns.job)
        #if err: raise LogImportError(row,'%s in not a valid Job.id')
        job = None

        # Get the sample name if present
        try:
            sample = self.get_value(row, self.columns.sample)

        except:
            sample = None

        # TODO: Is this really necessary (low pri)
        # If dataset and value present (import as record)
        if ds and v is not None:

            # Extent time of dataset
            if ds.start > time or ds.records.count() == 0:
                ds.start = time

            if ds.end < time or ds.records.count() == 0:
                ds.end = time

            # Check for duplicate record
            if self.recordexists(ds, time):
                raise LogImportError(
                    row, '%s has already a record at %s' % (ds, time))

            else:
                try:
                    ds.addrecord(value=v,
                                 time=time,
                                 comment=msg,
                                 sample=(sample if sample else None))

                except ValueError as e:
                    raise LogImportError(row, e.message)

            # Check for duplicate log. If log exists, go on quitely
            if not self.logexists(session, site, time):
                logmsg = 'Measurement:%s=%g %s with %s' % (ds.valuetype.name,
                                                           v,
                                                           ds.valuetype.unit,
                                                           ds.source.name)

                if msg:
                    logmsg += ', ' + msg
                newlog = db.Log(id=db.newid(db.Log, session),
                                user=self.user,
                                time=time,
                                message=logmsg,
                                type='measurement',
                                site=site)
                session.add(newlog)
            return "Add value %g %s to %s (%s)" % (v,
                                                   ds.valuetype.unit,
                                                   ds,
                                                   time)

        # if dataset or value are not present, import row as log only
        else:
            if not msg:
                raise LogImportError(row, 'No message to log')

            if self.logexists(session, site, time):
                raise LogImportError(
                    row, 'Log for %s at %s exists already' % (time, site))

            else:
                newlog = db.Log(id=db.newid(db.Log, session),
                                user=self.user,
                                time=time,
                                message=msg,
                                type=logtype,
                                site=site)
                session.add(newlog)
            return "Log: %s" % newlog

        if job:
            job.make_done(self, time)


class RecordImport(object):

    def __init__(self, filename, user, sheetname=None):
        self.filename = filename
        self.workbook = xlrd.open_workbook(filename)
        if sheetname:
            self.sheet = self.workbook.sheet_by_name(sheetname)
        else:
            self.sheet = self.workbook.sheet_by_index(0)

    t0 = datetime(1899, 12, 30)

    def get_time(self, date, time):
        if not time:
            return self.t0 + timedelta(date)
        else:
            if time > 1.000001:
                time -= int(time)
            date = int(date)
        return self.t0 + timedelta(date + time)

    def row_to_record(self, row, dataset, id, rangeok=None):
        if not rangeok:
            if not (dataset.minvalue is None or dataset.maxvalue is None):
                rangeok = [dataset.minvalue, dataset.maxvalue]
            else:
                rangeok = [-1e308, 1e308]
        rec = db.Record(id=id, dataset=dataset)
        rec.time = self.get_time(row[0].value, row[1].value)
        try:
            rec.value = float(row[2].value)
            if rec.value > max(rangeok) or rec.value < min(rangeok):
                rec.value = None
        except ValueError as TypeError:
            rec.value = None
        if row[3].value:
            rec.sample = row[3].value
        comment = (', '.join([str(c.value)
                              for c in row[4:] if c.value])).strip()
        if comment:
            rec.comment = comment
        return rec

    def __call__(self, commit=False):
        dsid = int(self.sheet.cell_value(3, 1))
        errors = {}
        logs = []

        try:
            session = db.Session()
            ds = session.query(db.Dataset).get(dsid)
            if not ds:
                session.close()
                errors[0] = 'Dataset %i not found in database. File %s is not imported' % (
                    dsid, os.path.basename(self.filename))
                return [dict(row=0, error=True, log=errors[0])], False
            rid = 1
            for row in range(16, self.sheet.nrows):
                try:
                    rec = self.row_to_record(self.sheet.row(row), ds, rid)
                    session.add(rec)
                    logs.append(dict(row=row, error=False,
                                     log="Add record %s" % rec))
                    rid += 1
                except Exception as e:
                    errors[row] = e.message
                    logs.append(dict(row=row, error=True, log=e.message))
            if commit and not errors:
                session.commit()
        finally:
            session.close()
        return logs, not errors
