from typing import Dict

from .base import ImportDescription, ImportColumn
import typing
from .. import db
import pandas as pd
import re
import datetime
from ..config import conf
from odmf.tools import Path


class DataImportError(RuntimeError):
    ...


def _new_datasets_from_descr(session, idescr: ImportDescription,
                             user: str, siteid: int, filepath: Path=None,
                             start: datetime.datetime=None, end: datetime.datetime=None) -> typing.Dict[typing.Any, db.Dataset]:
    """
    Creates new db.Dataset objects according to the import description.
    This works only for idescrs with

    Returns:
         Dictionary mapping columns (id/names) to db.Dataset objects

    The id's of the datasets are only available after flush/commit of the session
    """

    # Get instrument, user and site object from db
    inst = session.query(db.Datasource).get(idescr.instrument)
    user = session.query(db.Person).get(user)
    site = session.query(db.Site).get(siteid)

    def col_to_dataset(col: ImportColumn):
        """
        Creates a dataset from an ImportColumn.
        """
        # Get "raw" as data quality, to use as a default value
        raw = session.query(db.Quality).get(0)
        # Get the valuetype (vt) from db
        vt = session.query(db.ValueType).get(col.valuetype)

        if col.ds_column:
            # Columns that reference a dataset column are not referenced by
            return None
        elif col.append:
            try:
                ds = session.query(db.Dataset).get(int(col.append))
                ds.start = min(start, ds.start)
                ds.end = max(end, ds.end)
            except (TypeError, ValueError):
                raise DataImportError(
                    f'{idescr.filename}:{col.name} wants to append data ds:{col.append}. This dataset does not exist')

        else:
            # New dataset with metadata from above
            ds = db.Timeseries(measured_by=user, valuetype=vt, site=site, name=col.name,
                               filename=filepath.name, comment=col.comment, source=inst, quality=raw,
                               start=start, end=end, level=col.level,
                               access=col.access if col.access is not None else 1,
                               # Get timezone from descriptor or, if not present from global conf
                               timezone=idescr.timezone or conf.datetime_default_timezone,
                               project=idescr.project)
        return ds

    return {
        col.column: col_to_dataset(col)
        for col in idescr.columns
    }


def _prepare_ds_column_datasets(session, column: ImportColumn, data: pd.DataFrame):
    """
    Checks the Dataframe data for the datasets to be used by the ds_column
    """
    missing_ds = []
    ds_ids = data['dataset for ' + column.name]
    for dsid in ds_ids.unique():
        ds = session.query(db.Dataset).get(dsid)
        if ds:
            # Filter data for the current ds
            ds_data = data[ds_ids == dsid]
            ds.start = min(ds.start, ds_data.date.min().to_pydatetime())
            ds.end = max(ds.end, ds_data.date.max().to_pydatetime())
        else:
            missing_ds.append(dsid)

    if missing_ds:
        raise DataImportError(f'{column.name} misses the following datasets {missing_ds!s}.')


def _make_time_column_as_datetime(df: pd.DataFrame):
    """
    Converts the time column to a datetime

    Possible cases:

    1. The 'time' column contains 'datetime.time' objects -> Add to date column
    2. A 'date' column exists 'time' column contains strings like '13:30' or a datetime like 2020-01-01 13:30 (wrong date)
        -> convert and add to date column
    3. No 'date' column, and the 'time' column contains already a datetime or a string representation of a datetime
        -> convert to datetime
    """
    def convert_time_column(c: pd.Series) -> pd.Series:
        """
        Converts a column to_datetime and raises a LogImportStructError on failure
        """
        try:
            return pd.to_datetime(c, dayfirst=True)
        except:
            raise DataImportError(f'The column {c.name} is not convertible to a date')

    if 'time' in df.columns:
        if type(df['time'][0]) is datetime.time:
            df['date'] = convert_time_column(df['date'])
            df['time'] = [pd.Timestamp(datetime.datetime.combine(d, t)) for d, t in zip(df['date'], df['time'])]
        else:
            df['date'] = convert_time_column(df['date'])
            df['time'] = convert_time_column(df['time'])
            df['time'] = df['date'] + (df['time'] - df['time'].dt.normalize())
    else:
        df['time'] = convert_time_column(df['date'])

    del df['date']


def load_excel(idescr: ImportDescription, filepath: Path, columns: list, names: list) -> pd.DataFrame:
    try:
        return pd.read_excel(
            filepath.absolute,
            sheet_name=idescr.worksheet or 0,
            names=names, usecols=columns,
            skiprows=idescr.skiplines, skipfooter=idescr.skipfooter,
            na_values=idescr.nodata
        )
    except FileNotFoundError:
        raise DataImportError(f'{filepath} does not exist')
    except Exception as e:
        raise DataImportError(f'{filepath} read error. Is this an excel file? Underlying message: {str(e)}')


def load_csv(idescr: ImportDescription, filepath: Path, columns: list, names: list) -> pd.DataFrame:
    try:
        encoding = idescr.encoding or 'utf-8'
        return pd.read_csv(
            filepath.absolute,
            names=names, usecols=columns,
            skiprows=idescr.skiplines, skipfooter=idescr.skipfooter or 0,
            delimiter=idescr.delimiter, decimal=idescr.decimalpoint,
            na_values=idescr.nodata,
            encoding=encoding, engine='python'
        )
    except FileNotFoundError:
        raise DataImportError(f'{filepath} does not exist')
    except UnicodeDecodeError:
        raise DataImportError(f'{filepath} could not be read. Is this a {encoding} encoded textfile?')
    except Exception as e:
        raise DataImportError(f'{filepath} read error. Is this a seperated text file? Underlying message: {str(e)}')


def load_dataframe(idescr: ImportDescription, filepath: Path) -> pd.DataFrame:
    """
    Loads a pandas dataframe from a data file (csv or xls[x]) using an import description
    """

    columns = list(idescr.datecolumns) + [col.column for col in idescr.columns] + \
              [col.ds_column for col in idescr.columns if col.ds_column]
    names = ['date', 'time'][:len(idescr.datecolumns)] + [col.name for col in idescr.columns] + \
            ['dataset for ' + col.name for col in idescr.columns if col.ds_column]

    if idescr.samplecolumn:
        columns += [idescr.samplecolumn]
        names += ['sample']
        if re.match(r'.*\.xls[xmb]?$', filepath):
            df = load_excel(idescr, filepath, columns, names)
        else:
            df = load_csv(idescr, filepath, columns, names)

    _make_time_column_as_datetime(df)
    warnings = []

    for col in idescr.columns:
        # Apply the difference operation
        if col.difference:
            df[col.name] = df[col.name].diff()

        # Remove all values, where one of the columns is outside its minvalue / maxvalue range
        not_in_range = (df[col.name] < col.minvalue) | (df[col.name] > col.maxvalue)
        if any(not_in_range):
            warnings.append('Removed {} records, because {} was not in its allowed range'.format(sum(not_in_range), str(col)))
        df.drop(index=not_in_range, inplace=True)

        # Apply unit conversion factor factor
        df[col.name] *= col.factor

    return df, warnings


def submit(idescr: ImportDescription, filepath: Path, user: str, siteid: int):
    """
    Loads tabular data from a file, creates or loads necessary datasets and imports the data as records
    """
    df, _ = load_dataframe(idescr, filepath)

    if len(df) == 0:
        raise DataImportError(f'No records to import from {filepath} with {idescr.filename}.')

    start = df.time.min().to_pydatetime()
    end = df.time.max().to_pydatetime()
    messages = []
    with db.session_scope() as session:
        datasets = _new_datasets_from_descr(session, idescr, user=user, siteid=siteid,
                                            filepath=filepath, start=start, end=end)
        # TODO: Inform about import actions (eg. Datasets created)

        for col in idescr.columns:
            if col.ds_column:
                _prepare_ds_column_datasets(session, col, df)

        # Commit session to generate id's for new datasets
        session.commit()

        # Get the dataset id's
        datasetids = {
            col: datasets[col].id
            for col in datasets
        }

    # Make dataframe in the style of the records table
    for col in idescr.columns:
        col_df = pd.DataFrame(df.time)
        if not col.ds_column:
            col_df['dataset'] = datasetids[col.column]
        else:
            col_df['dataset'] = df['dataset for ' + col.name]
        col_df['value'] = df[col.name]

        if idescr.samplecolumn:
            col_df['sample'] = df['sample']

    # Now submit the data
    col_df.to_sql('record', db.engine, if_exists='append')




