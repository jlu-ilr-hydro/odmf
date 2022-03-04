
from .base import ImportDescription, ImportColumn
import typing
from .. import db
import pandas as pd
import re
import datetime
from ..config import conf
from odmf.tools import Path
from logging import getLogger
logger = getLogger(__name__)

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

        assert not col.ds_column, "Cannot create a ColumnDataset for a column with variable dataset target"

        if col.append:
            try:
                self.dataset: db.Timeseries = session.query(db.Dataset).get(int(col.append))
                assert self.dataset.type == 'timeseries'
                self.dataset.start = min(start, self.dataset.start)
                self.dataset.end = max(end, self.dataset.end)
                self.record_count = self.dataset.maxrecordid()

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

        self.id = self.dataset.id

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
        col_df['id'] = df[values_ok].index + self.record_count + 1
        col_df['value'] = df[self.column.name]
        col_df['is_error'] = False
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
    Creates fitting ColumnDataset combinations for an ImportDescription
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

        newdatasets = []
        appendatasets = []
        for col in idescr.columns:
            if col.append:
                appendatasets.append(
                    ColumnDataset(
                        session, idescr, col, None,
                        user, site, inst, valuetypes, raw,
                        start, end, filepath.name
                    )
                )
            elif not col.ds_column:
                newdatasets.append(
                    ColumnDataset(
                        session, idescr, col,
                        newid + len(newdatasets),
                        user, site, inst, valuetypes, raw,
                        start, end, filepath.name
                    )
                )

        return appendatasets + newdatasets


def _make_time_column_as_datetime(df: pd.DataFrame, fmt=None):
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
        # First try the given format, second try with a "free" format. Needed eg. for a two column format
        for timeformat in [fmt, None]:
            try:
                return pd.to_datetime(c, dayfirst=True, infer_datetime_format=True, format=timeformat)
            except Exception as e:  # difficult to get more specific, as Pandas Exception model is a bit strange
                # Some sensors believe 24:00 is a valid time, pandas not
                if any('24:' in a for a in e.args):  # Checks if the error message contains 24
                    # Deal with 24:00 in a datetime string
                    problems = c.str.contains('24:00')  # Mark the problems
                    # Make dates by replacing 24:00 with 00:00
                    changed = pd.to_datetime(c.str.replace('24:00', '00:00'))  # Convert to datetime
                    # Change date from eg. 2.12.2020 24:00 -> 3.12.2020 00:00
                    changed[problems] += datetime.timedelta(days=1)
                    return changed

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
    try:
        return df[col.name].between(col.minvalue, col.maxvalue)
    except TypeError:
        return pd.Series(False, index=df.index)


def _load_excel(idescr: ImportDescription, filepath: Path) -> pd.DataFrame:
    """
    loads data from excel, called by load_dataframe
    """
    columns, names = idescr.get_column_names()
    try:
        df = pd.read_excel(
            filepath.absolute,
            sheet_name=idescr.worksheet or 0,
            header=None,
            skiprows=idescr.skiplines, skipfooter=idescr.skipfooter,
            na_values=idescr.nodata
        )
        df = df[columns]
        df.columns = names
        return df

    except FileNotFoundError:
        raise DataImportError(f'{filepath} does not exist')
    except Exception as e:
        raise DataImportError(f'{filepath} read error. Is this an excel file? Underlying message: {str(e)}')


def _load_csv(idescr: ImportDescription, filepath: Path) -> pd.DataFrame:
    """
    Loads the data from a csv like file

    called by load_dataframe
    """
    encoding = idescr.encoding or 'utf-8'
    columns, names = idescr.get_column_names()
    try:
        df = pd.read_csv(
            filepath.absolute, header=None,
            skiprows=idescr.skiplines, skipfooter=idescr.skipfooter or 0,
            delimiter=idescr.delimiter, decimal=idescr.decimalpoint,
            na_values=idescr.nodata, skipinitialspace=True,
            encoding=encoding, engine='python', quotechar='"'
        )
        df = df[columns]
        df.columns = names
        return df
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
) -> pd.DataFrame:
    """
    Loads a pandas dataframe from a data file (csv or xls[x]) using an import description
    """


    if type(filepath) is not Path:
        filepath = Path(filepath)


    if re.match(r'.*\.xls[xmb]?$', filepath.name):
        df = _load_excel(idescr, filepath)
        if df.empty:
            raise DataImportError(
                f'No data to import found in {filepath}. If this file was generated by a third party program '
                f'(eg. logger software), open in excel and save as a new .xlsx - file')
    else:
        df = _load_csv(idescr, filepath)
    _make_time_column_as_datetime(df, idescr.dateformat)

    for col in idescr.columns:
        # Apply the difference operation
        if col.difference:
            df[col.name] = df[col.name].diff()
        try:
            df[col.name] *= col.factor
        except TypeError:
            ...

    return df


def get_statistics(idescr: ImportDescription, df: pd.DataFrame) \
        -> typing.Tuple[typing.Dict[str, typing.Dict[str, float]], datetime.datetime, datetime.datetime]:
    """
    Creates some statistics for a dataframe
    """
    res = {}
    startdate = df['time'].min().to_pydatetime()
    enddate = df['time'].max().to_pydatetime()
    for col in idescr.columns:
        s = df[col.name]
        res[col.name] = {}
        # If the column is not float some of the stats don't make sense, just skip them
        try:
            res[col.name]['start'] = startdate
            res[col.name]['end'] = enddate
            res[col.name]['n'] = s.size
            res[col.name]['n_out_of_range'] = len(s) - check_column_values(col, df).sum()
            res[col.name]['min'] = s.min()
            res[col.name]['max'] = s.max()
            res[col.name]['sum'] = s.sum()
            res[col.name]['mean'] = s.mean()
        except (TypeError, ValueError):
            ...

    return res, startdate, enddate


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
        # type(dsid) --> np.int64
        dsid = int(dsid)
        # int conversion is necessary to prevent
        # (psycopg2.ProgrammingError) can't adapt type 'numpy.int64'
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
    col_df['is_error'] = False
    return col_df[~pd.isna(col_df['value'])]


def _get_recordframe(session: db.Session, idescr: ImportDescription,
                     datasets: typing.List[ColumnDataset], df: pd.DataFrame):
    """
    Returns a single dataframe in the Layout of the record table including all records to export
    """
    return pd.concat([
        cds.to_record_dataframe(df)
        for cds in datasets
    ] + [
        get_dataframe_for_ds_column(session, col, df)
        for col in idescr.columns
        if col.ds_column
    ])


def submit(session: db.Session, idescr: ImportDescription, filepath: Path, user: str, siteid: int):
    """
    Loads tabular data from a file, creates or loads necessary datasets and imports the data as records

    """
    messages = []
    df = load_dataframe(idescr, filepath)
    logger.debug(f'loaded {filepath}, got {len(df)} rows with {len(df.columns)} columns')

    if len(df) == 0:
        raise DataImportError(f'No records to import from {filepath} with {idescr.filename}.')

    # Load all datasets for appending and create new datasets
    datasets = columndatasets_from_description(
        session, idescr, user=user,
        siteid=siteid, filepath=filepath,
        start=df.time.min().to_pydatetime(),
        end=df.time.max().to_pydatetime()
    )

    # make datasets available in the session
    session.flush()

    logger.debug(f'created or referenced {len(datasets)} datasets')
    messages.extend(
        f'ds{cds.id} : Import {cds.column} from file:{filepath}'
        for cds in datasets
    )

    recordframe = _get_recordframe(session, idescr, datasets, df)
    logger.info(f'insert {len(recordframe)} records into {len(recordframe.dataset.unique())} datasets')

    conn = session.connection()
    recordframe.to_sql('record', conn, if_exists='append', index=False, method='multi', chunksize=1000)

    return messages
