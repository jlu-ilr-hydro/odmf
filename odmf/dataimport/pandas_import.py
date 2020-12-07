
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


class ColumnDataset:
    """
    A combination of an ImportColumn and a Dataset, used for import.

    The datasets are created in the db if the column is not for appending.
    The datasets start and end time is already adjusted
    """
    id: int
    dataset: db.Dataset
    column: ImportColumn
    idescr: ImportDescription
    record_count: int = 0

    def __init__(self, session, idescr: ImportDescription, col: ImportColumn,
                 id: int, user: db.Person, site: db.Site, inst: db.Datasource,
                 valuetypes: typing.Dict[int, db.ValueType], raw: db.Quality,
                 start: datetime.datetime, end: datetime.datetime,
                 filename: typing.Optional[str] = None
                 ):

        self.column = col
        self.idescr = idescr
        self.id = id

        assert not col.ds_column, "Cannot create a ColumnDataset for a column with variable dataset target"

        if col.append:
            try:
                self.dataset = session.query(db.Dataset).get(int(col.append))
                self.dataset.start = min(start, self.dataset.start)
                self.dataset.end = max(end, self.dataset.end)
                self.record_count = self.dataset.size()

            except (TypeError, ValueError):
                raise DataImportError(
                    f'{idescr.filename}:{col.name} wants to append data ds:{col.append}. This dataset does not exist')

        else:
            # New dataset with metadata from above
            self.dataset = db.Timeseries(
                id=id, measured_by=user,
                valuetype=valuetypes[col.valuetype],
                site=site, name=col.name,
                filename=filename, comment=col.comment, source=inst, quality=raw,
                start=start, end=end, level=col.level,
                access=col.access if col.access is not None else 1,
                # Get timezone from descriptor or, if not present from global conf
                timezone=idescr.timezone or conf.datetime_default_timezone,
                project=idescr.project)
            session.add(self.dataset)

    def to_record_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepares nad populates a dataframe with the layout of the db.Record-Table

        df: The dataframe containing all data to import
        """

        # Remove all values, where one of the columns is outside its minvalue / maxvalue range
        values_ok = check_column_values(self.column, df)
        col_df = pd.DataFrame(df.time)
        col_df = col_df[values_ok]
        col_df['dataset'] = self.id
        col_df['id'] = df.index + self.record_count
        col_df['value'] = df[self.column.name]
        if 'sample' in df.columns:
            col_df['sample'] = df['sample']

        return col_df

    def __repr__(self):
        return f'ColumnDataset: {self.column} -> ds:{self.dataset.id}'


def columndatasets_from_description(
        session, idescr: ImportDescription,
        user: str, siteid: int, filepath: Path = None,
        start: datetime.datetime = None, end: datetime.datetime = None
) -> typing.List[ColumnDataset]:

    """
    Creates fitting
    """
    with session.no_autoflush:
        # Get instrument, user and site object from db
        inst = session.query(db.Datasource).get(idescr.instrument)
        user = session.query(db.Person).get(user)
        site = session.query(db.Site).get(siteid)
        # Get "raw" as data quality, to use as a default value
        raw = session.query(db.Quality).get(0)
        # Get all the relevant valuetypes (vt) from db as a dict for fast look up
        valuetypes = {
            vt.id: vt for vt in
            session.query(db.ValueType).filter(
                db.ValueType.id.in_([col.valuetype for col in idescr.columns])
            )
        }
        newid = db.newid(db.Dataset, session)
        datasets = []
        for col in idescr.columns:
            if not col.ds_column:  # Do not create or find datasets for columns with varying datasets
                datasets.append(
                    ColumnDataset(
                        session, idescr, col,
                        newid + len(datasets),
                        user, site, inst, valuetypes, raw,
                        start, end, filepath.name
                    )
                )
        return datasets


def _make_time_column_as_datetime(df: pd.DataFrame):
    """
    Converts the time column to a datetime

    Possible cases:

    1. The 'time' column contains 'datetime.time' objects -> Add to date column
    2. A 'date' column exists 'time' column contains strings like '13:30' or like 2020-01-01 13:30 (wrong date)
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
        except Exception:
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


def check_column_values(col: ImportColumn, df: pd.DataFrame):
    return df[col.name].between(col.minvalue, col.maxvalue)


def _load_excel(idescr: ImportDescription, filepath: Path, columns: list, names: list) -> pd.DataFrame:
    """
    loads data from excel, called by load_dataframe
    """
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


def _load_csv(idescr: ImportDescription, filepath: Path, columns: list, names: list) -> pd.DataFrame:
    """
    Loads the data from a csv like file

    called by load_dataframe
    """
    encoding = idescr.encoding or 'utf-8'
    try:
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
        raise DataImportError(
            f'{filepath} could not be read as {encoding} encoding. Specify correct encoding (eg. windows-1252) in {idescr.filename}'
        )
    except Exception as e:
        raise DataImportError(f'{filepath} read error. Is this a seperated text file? Underlying message: {str(e)}')


def load_dataframe(
        idescr: ImportDescription,
        filepath: typing.Union[Path, str]
) -> typing.Tuple[pd.DataFrame, typing.List[str]]:
    """
    Loads a pandas dataframe from a data file (csv or xls[x]) using an import description
    """

    columns = (
            list(idescr.datecolumns)
            + [col.column for col in idescr.columns]
            + [col.ds_column for col in idescr.columns if col.ds_column]
    )
    names = ['date', 'time'][:len(idescr.datecolumns)] + [col.name for col in idescr.columns] + \
            ['dataset for ' + col.name for col in idescr.columns if col.ds_column]

    if type(filepath) is not Path:
        filepath = Path(filepath)

    if idescr.samplecolumn:
        columns += [idescr.samplecolumn]
        names += ['sample']

    if re.match(r'.*\.xls[xmb]?$', filepath.name):
        df = _load_excel(idescr, filepath, columns, names)
        if df.empty:
            raise DataImportError(
                f'No data to import found in {filepath}. If this file was generated by a third party program '
                f'(eg. logger software), open in excel and save as a new .xlsx - file')
    else:
        df = _load_csv(idescr, filepath, columns, names)

    _make_time_column_as_datetime(df)

    warnings = []

    for col in idescr.columns:
        # Apply the difference operation
        if col.difference:
            df[col.name] = df[col.name].diff()

        # Apply unit conversion factor factor
        print(col.name)
        df[col.name] *= col.factor

    return df, warnings


def get_dataframe_for_ds_column(session, column: ImportColumn, data: pd.DataFrame):
    """
    To be used for columns with ds_column:

    Creates a dataframe in the layout of the record table and adjusts all start / end dates of the fitting datasets

    ------------- Untested -----------------
    """

    assert column.ds_column, "no ds_column available"
    missing_ds = []
    ds_ids = data['dataset for ' + column.name]

    newids = {}

    def get_newid_range(ds: db.Timeseries):
        start = ds.maxrecordid() + 1
        end = start + (ds_ids == ds.id).sum()
        return range(start, end)

    for dsid in ds_ids.unique():
        ds = session.query(db.Dataset).get(dsid)
        if ds:
            # Filter data for the current ds
            ds_data = data[ds_ids == dsid]
            newids[dsid] = get_newid_range(ds)

            ds.start = min(ds.start, ds_data.date.min().to_pydatetime())
            ds.end = max(ds.end, ds_data.date.max().to_pydatetime())
        else:
            missing_ds.append(dsid)

    if missing_ds:
        raise DataImportError(f'{column.name} misses the following datasets {missing_ds!s}.')

    col_df = pd.DataFrame(data.time)

    col_df['dataset'] = data['dataset for ' + column.name]
    col_df['id'] = data.index
    col_df['value'] = data[column.name]

    if 'sample' in data.columns:
        col_df['sample'] = data['sample']

    return col_df[~pd.isna(col_df['value'])]


def submit(session: db.Session, idescr: ImportDescription, filepath: Path, user: str, siteid: int):
    """
    Loads tabular data from a file, creates or loads necessary datasets and imports the data as records

    """
    df, messages = load_dataframe(idescr, filepath)

    if len(df) == 0:
        raise DataImportError(f'No records to import from {filepath} with {idescr.filename}.')

    start = df.time.min().to_pydatetime()
    end = df.time.max().to_pydatetime()

    record_frames = []
    datasets = columndatasets_from_description(
        session, idescr, user=user, siteid=siteid,
        filepath=filepath, start=start, end=end
    )
    session.flush()
    messages.extend(
        f'ds:{cds.id} : Import {cds.column} of {filepath}'
        for cds in datasets
    )

    record_frames.extend(
        cds.to_record_dataframe(df)
        for cds in datasets
    )

    record_frames.extend(
        get_dataframe_for_ds_column(session, col, df)
        for col in idescr.columns
        if col.ds_column
    )

    conn = session.connection()
    # Make dataframe in the style of the records table
    for rf in record_frames:
        rf.to_sql('record', conn, if_exists='append', index=False)

    return messages
