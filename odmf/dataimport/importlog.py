"""
Created on 19.02.2013

@author: kraft-p
"""
import xlrd
import os
import pandas as pd
from .. import db
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


class LogbookImport:
    """
    Imports from a defined xls file messages to the logbook and append values to datasets

    Structure of the table:
    [Date] | Time | Site | Dataset | Value  | Message | [LogType] | [Sample]
    """

    def __init__(self, filename, user, sheetname=0):
        self.filename = filename
        self.dataframe = df = pd.read_excel(filename, sheetname)
        self.dataframe.columns = [c.lower() for c in self.dataframe.columns]
        if not all(c in df.columns for c in "time|site|dataset|value|logtype|message".split('|')):
            raise RuntimeError('The log excel sheet misses some of the follwing columns: '
                               'time|site|dataset|value|logtype|message')

        if 'date' in df.columns:
            df.time = df.date + (df.time - df.time.dt.normalize())
        for c in ('site', 'dataset'):
            df[c] = df[c].astype('Int64')

        with db.session_scope() as session:
            _user: db.Person = session.query(db.Person).get(user)
            if not _user:
                raise RuntimeError('%s is not a valid user' % user)
            else:
                self.user = _user.username

    def __call__(self, commit=False):
        logs = []
        has_error = False
        with db.session_scope() as session:
            with session.no_autoflush:
                for row, data in self.dataframe.iterrows():
                    try:
                        log = dict(row=row + 1,
                                   error=False,
                                   log=self.importrow(session, row + 1, data, commit)
                                   )
                    except LogImportError as e:
                        has_error = True
                        log = dict(row=row + 1,
                                   error=True,
                                   log=e.text)
                    logs.append(log)
            if commit:
                session.commit()
            else:
                session.rollback()

        return logs, not has_error

    def recordexists(self, timeseries, time, timetolerance=30):
        """
        Checks if a record at time exists in dataset

        :param dataset: A timeseries to be checked
        :param time: The time for the record
        :param timetolerance: the tolerance of the time in seconds
        """
        td = timedelta(seconds=timetolerance)

        return timeseries.records.filter(
            db.sql.between(db.Record.time,
                           time - td,
                           time + td)).count() > 0

    def logexists(self, session, site, time, timetolerance=30):
        """
        Checks if a log at site and time exists in db
        session: an open sqlalchemy session
        site: A site
        time: The time for the log
        timetolerance: the tolerance of the time in seconds
        """
        td = timedelta(seconds=timetolerance)

        return session.query(db.Log)\
            .filter(db.Log._site == site,
                    db.sql.between(db.Log.time,
                                   time - td,
                                   time + td)).count() > 0

    def get_dataset(self, session, row, data) -> db.Timeseries:
        """Loads the dataset from a row and checks if it is manually measured and at the correct site"""
        ds = session.query(db.Dataset).get(data.dataset)
        if not ds:
            raise LogImportError(row, f'Dataset {data.dataset} does not exist')
        # check dataset is manual measurement
        if ds.source is None or ds.source.sourcetype != 'manual':
            raise LogImportError(row, f'{ds} is not a manually measured dataset, '
                                      'if the dataset is correct please change '
                                      'the type of the datasource to manual'
                                 )
        # check site
        if ds.site.id != data.site:
            raise LogImportError(row, f'Dataset ds:{ds.id} is not located at #{data.site}')
        return ds

    def row_to_record(self, session, row, data):
        """
        Creates a new db.Record object from a row of the log format data file
        """
        # load and check dataset
        ds = self.get_dataset(session, row, data)
        time = data.time.to_pydatetime()
        value = data.value
        # Check for duplicate
        if self.recordexists(ds, time):
            raise LogImportError(row, f'{ds} has already a record at {time}')
        # Check if the value is in range
        if not ds.valuetype.inrange(value):
            raise LogImportError(row, f'{value:0.5g}{ds.valuetype.unit} is not accepted for {ds.valuetype}')
        # Create Record
        comment = data.message if pd.notna(data.message) else None
        sample = data.get('sample')
        record = db.Record(value=value, time=time, dataset=ds, comment=comment, sample=sample)
        # Extend dataset timeframe if necessary
        ds.start, ds.end = min(ds.start, time), max(ds.end, time)

        return record, f'Add value {value:g} {ds.valuetype.unit} to {ds} ({time})'

    def row_to_log(self, session, row, data):
        """
        Creates a new db.Log object from a row without dataset
        """
        time = data.time.to_pydatetime()
        site = session.query(db.Site).get(data.site)
        user = session.query(db.Person).get(self.user)

        if not site:
            raise LogImportError(row, f'Log: Site #{data.site} not found')

        if pd.isnull(data.get('message')):
            raise LogImportError(row, 'No message to log')

        if self.logexists(session, data.site, time):
            raise LogImportError(
                row, f'Log for {time} at {site} exists already')

        else:
            log = db.Log(user=user,
                         time=time,
                         message=data.get('message'),
                         type=data.get('logtype'),
                         site=site)

        return log, f'Log: {log}'

    def importrow(self, session: db.Session, row, data, commit=False):
        """
        Imports a row from the log-excelfile, either as record to a dataset
        or as a log entry. The decision is made on the basis of the data given.
        """
        # Get time from row
        if pd.isnull(data.time):
            raise LogImportError(row, 'Time not readable')

        if pd.isnull(data.site):
            raise LogImportError(row, 'Site is missing')

        result = msg = None
        if pd.notna(data.dataset):
            if pd.isnull(data.value):
                raise LogImportError(row, f'No value given to store in ds:{data.dataset}')
            # Dataset given, import as record
            result, msg = self.row_to_record(session, row, data)

        elif pd.notna(data.value):
            raise LogImportError(row, 'A value is given, but no dataset to store it')

        elif pd.notna(data.message):
            # No dataset but Message is given -> import as log
            result, msg = self.row_to_log(session, row, data)

        if result and commit:
            session.add(result)

        return msg

if __name__ == '__main__':
    import os

    os.chdir('instances/schwingbach')
    from odmf.dataimport import importlog as il

    li = il.LogbookImport('datafiles/test_log.xls', 'philipp')
    res, is_ok = li()
    print(len(res), 'OK' if is_ok else 'NOT OK!')