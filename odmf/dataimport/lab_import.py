"""
Reads a table with lab data using a configuration file (in yaml format)

Example config file:
"""
import typing
import pandas as pd
import yaml
from .. import db
from ..tools import Path, parquet_import
from .sample_parser import SampleParser

example="""
driver: read_excel   # pandas function to read the table. See: https://pandas.pydata.org/docs/reference/io.html
columns:                 # Description of each column, use the column name as object name
    Sample:              # Name of the sample column, in this case Sample
        type: sample     # Necessary to understand column as sample names
        pattern: (\w+?)_([0-9\.]+_[0-9]+\:[0-9]+)_?(?:[-+]?[0-9\.]+)
        site:
            group: 1
            map:
                F1: 137
                F2: 147
                F3: 201
                B1: 123
                B2: 138
                B3: 203
        time:
            group: 2
            format: "%d%m%y_%H:%M"
        level:
            group: 3
    N_NO3:  # The name
        type: value
        factor: 1.0
        valuetype: 3
    N_NH4:
        type: value
        factor: 14.3
        valuetype: 4
"""

def find_dataset(session: db.Session, time=None, site=None, level=None, valuetype=None, instrument=None, dataset=None, **kwargs):
    """
    Finds a dataset, from a rough description.
    - if the dataset id is given, the dataset is returned
    - if other filters are given, they are used. If no dataset exists at the given date, the next earlier dataset fitting the other filters is returned
    - if multiple datasets match the date, an error is raised
    """
    if not pd.isna(dataset):
        dataset = int(dataset)
        if ds := session.get(db.Dataset, dataset):
            return ds
        else:
            raise ValueError(f"Dataset {dataset} not found")
    else:
        def type_or_none(cls, x):
            if x is None:
                return x
            else:
                return cls(x)
        candidates = db.Dataset.filter(
            session=session, date=time,
            valuetype=type_or_none(int, valuetype),
            instrument=type_or_none(int, instrument),
            level=type_or_none(float, level),
            site=type_or_none(int, site)
        )
        ccount = candidates.count()
        if ccount == 1:
            return candidates.first()
        elif ccount == 0:
            candidate: db.Dataset = (
                db.Dataset.filter(
                    session=session,
                    date=None,
                    valuetype=type_or_none(int, valuetype),
                    instrument=type_or_none(int, instrument),
                    level=type_or_none(float, level),
                    site=type_or_none(int, site)
                ).filter(db.Dataset.end < time)
                .order_by(db.Dataset.end.desc())
                .limit(1)
            ).first()
            if candidate:
                # check if candidate is unique
                if db.Dataset.filter(session=session, date=candidate.end, valuetype=valuetype, instrument=instrument, level=level, site=site).count() == 1:
                    return candidate
                else:
                    raise ValueError(f"Dataset filter not unique, found multiple fitting datasets with the same end date")
            else:
                raise ValueError(f"No dataset found")
        else: #  Found more datasets with filter at date
            raise ValueError(f"Dataset filter not unique at given date and filter")

def find_datasets(df_melt: pd.DataFrame):
    """
    Looks for each row of the molten table up, which dataset fits. If multiple datasets match the row, an error is collected.
    The df_melt dataframe is altered inplace, the function returns a list of dictionaries describing the row and the error in
    that row.
    """
    errors = []
    result = pd.Series(index=df_melt.index, dtype='Int64')
    with db.session_scope() as session:
        for index, row in df_melt.iterrows():
            try:
                ds = find_dataset(session, **dict(row))  # This line is slow!
                result[index] = ds.id
            except ValueError as e:
                errors.append(dict(row) | {'error': str(e)})
    return result, errors

def check_columns(table: pd.DataFrame, labcolumns: dict):
    """
    Checks that the columns in the table match the columns in the labcolumns dictionary. Raises on error
    """
    missing = [
        col for col in labcolumns if col not in table.columns
    ]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    else:
        return labcolumns

def get_type_column(coltype:str, labcolumns: dict):
    """Finds the column of a specific type in the lab columns"""
    for col in labcolumns:
        if labcolumns[col]['type'] == coltype:
            return col
    return None


def parse_sample(series: pd.Series, sample_column: dict):
    """
    Parses the sample column
    :param series: The table column with the sample names
    :param sample_column: the config description of the sample column
    :return: a dataframe with parsed columns, a subset of time, site, dataset, level
    """
    sampler = SampleParser(sample_column)

    parsed = pd.DataFrame([
        sampler(v) for v in series
    ],
        index=series.index
    )
    return parsed.dropna(axis=1, how='all')

def apply_sample_column(table: pd.DataFrame, labcolumns: dict, samplecolumn: str):
    """
    Alters the given table by adding a column 'sample' with the sample name and
    all information gathered from the sample name as new columns dataset, site, level, instrument
    if they do not exist already as explicit columns

    Returns None
    """
    sample_df = parse_sample(table[samplecolumn], labcolumns[samplecolumn])
    for col in sample_df.columns:
        if col not in table.columns:
            table[col] = sample_df[col]
    return table.rename(columns={samplecolumn: 'sample'}, inplace=True)


def melt_table(table: pd.DataFrame, labcolumns: dict):
    """
    Unpivots the table by the value columns (DataFrame.melt)
    """
    # Set id_vars and value_vars for pandas.DataFrame.melt
    id_vars = ['time', 'dataset', 'site', 'instrument', 'level', 'sample']
    # filter id_vars, to what exists
    id_vars = [c for c in id_vars if c in table.columns]
    value_vars = {
        c : labcolumns[c]['valuetype']
        for c in labcolumns
        if labcolumns[c]['type'] == 'value'
    }
    # Melt the value columns into the long format
    df_melt = table.melt(id_vars, list(value_vars), var_name='value_column', value_name='value')
    # Translate the value columns name into the valuetype id
    df_melt['valuetype'] = df_melt['value_column'].map(value_vars)
    del df_melt['value_column']
    if not 'dataset' in df_melt.columns:
        df_melt['dataset'] = pd.NA
    return df_melt

def rename_column_by_type(table: pd.DataFrame, labcolumns, *coltypes):
    """
    Renames the columns in table to the type name. Alters the table!
    """
    for coltype in coltypes:
        if column := get_type_column(coltype, labcolumns):
            table.rename(columns={column: coltype}, inplace=True)

def clean_and_aggregate_df_melt(df_melt: pd.DataFrame):
    """Removes unused columns and aggregates dataframe"""
    keep_cols = ['dataset', 'time', 'value', 'sample']
    df_melt_clean = df_melt.copy()
    for col in df_melt_clean.columns:
        if col not in keep_cols:
            del df_melt_clean[col]
    return df_melt_clean.groupby(['dataset', 'time', 'sample']).mean().reset_index()


def labimport(filename: Path, dryrun=True) -> (typing.Sequence[int], dict, typing.Sequence[dict]):
    """
    Steps to do
    + aggregate by dataset and time (`df.groupby(by=['dataset', 'time']).mean()`)
    What happens if one dataset exist, but not the second?
    + result table has record schema (dataset, id, time, value, is_error) -> import
    :return:
    """

    conffile = filename.glob_up('*.labimport')
    with conffile.open() as f:
        labconf = yaml.safe_load(f)

    read = getattr(pd, labconf.get('driver', 'read_excel'))
    df: pd.DataFrame = read(filename.absolute, **labconf.get('driver-options', {}))
    labcolumns = check_columns(df, labconf.get('columns', {}))

    rename_column_by_type(df, labcolumns, 'time', 'dataset', 'site', 'level')

    if samplecolumn := get_type_column('sample', labcolumns):
        apply_sample_column(df, labcolumns, samplecolumn)
    elif samplecolumn:= get_type_column('samplename', labcolumns):
        df.rename(columns={samplecolumn: 'sample'}, inplace=True)
    else:
        df['sample'] = None

    df_melt = melt_table(df, labcolumns)
    datasets, errors = find_datasets(df_melt)
    df_melt['dataset'] = datasets
    df_melt = df_melt.dropna()
    df_agg = clean_and_aggregate_df_melt(df_melt)
    info = {
        'measured' : len(df_melt),
        'aggregated' : len(df_agg),
    }
    if not dryrun:
        _, record_count = parquet_import.addrecords_dataframe(df_agg)
        info['imported'] = record_count
    datasets = {
        int(i) : (df_agg.dataset == i).sum()
        for i in df_agg.dataset
    }
    return datasets, info, errors, labconf


if __name__ == '__main__':
    from odmf.dataimport import lab_import as li
    from odmf.tools import Path
    import yaml
    p = Path('lab/3_2021.xls')
    labconf = yaml.safe_load(open(p.glob_up('*.labimport').absolute))
    df = pd.read_excel(p.absolute, **labconf.get('driver-options', {}))
    labcolumns = li.check_columns(df, labconf.get('columns', {}))
    li.apply_sample_column(df, labcolumns, 1)
    df_melt = li.melt_table(df, labcolumns)
    datasets, errors = li.find_datasets(df_melt)
