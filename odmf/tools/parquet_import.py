#!/usr/bin/env python3
"""
Imports parquet file in the record table format into the database, perfoming a couple of checks

Philipp Kraft 2022-06-23
"""
import logging
import pandas as pd
from odmf import db

logger = logging.getLogger(__name__)


def _adjust_columns(df: pd.DataFrame):
    """
    Adds and removes columns of the DataFrame df to fit with record table format

    dataset, id, time, value [,sample, comment, is_error]
    """
    if 'id' not in df.columns:
        df['id'] = df.index

    if 'is_error' not in df.columns:
        df['is_error'] = False

    if not all(cname in df.columns for cname in ['dataset', 'id', 'time', 'value']):
        raise KeyError('Your table misses one or more of the columns dataset, id, time, value [,sample, comment]')

    # remove unused columns
    for c in list(df.columns):
        if c not in ['dataset', 'id', 'time', 'value', 'sample', 'comment', 'is_error']:
            del df[c]


def _check_datasets(df, session):
    """
    Checks if all datasets in df.dataset exist in the database
    """
    datasets = set(int(id) for id in df.dataset.unique())
    all_db = set(v[0] for v in session.query(db.Dataset.id))
    missing = datasets - all_db
    if missing:
        raise KeyError('Your table contains records for not existing dataset-ids: ' + ', '.join(
            str(ds) for ds in missing))
    return list(datasets)


def _adjust_id(df: pd.DataFrame, ds: db.Dataset):
    """
    Adjusts the record-id to fit to existing records
    """
    maxrecordid = ds.maxrecordid() + 1
    old_min_id = df.loc[df['dataset'] == ds.id, 'id'].min()
    logger.info('ds:', ds.id, '.maxrecordid() = ', maxrecordid, ' old min(id) =', old_min_id)
    if old_min_id <= maxrecordid:
        offset = maxrecordid - old_min_id
        logger.info(offset, ' offset')
        df.loc[df['dataset'] == ds.id, 'id'] += offset
        logger.info(df.loc[df['dataset'] == ds.id, 'id'].min(), 'new min(id)')


def _adjust_time(df: pd.DataFrame, ds: db.Dataset):
    """
    Sets the new start and end of the datasets
    """
    ds.start = min(ds.start, df.loc[df.dataset == ds.id, 'time'].min().to_pydatetime())
    ds.end = max(ds.end, df.loc[df.dataset == ds.id, 'time'].max().to_pydatetime())

def addrecords_dataframe(df: pd.DataFrame):
    """
    Adds records from a dataframe to the database
    :param df: The dataframe in record table format
    :return:
    """
    from ..webpage.auth import users

    df = df[~df.value.isna()]
    _adjust_columns(df)

    with db.session_scope() as session:

        # Check datasets
        ds_ids = _check_datasets(df, session)

        datasets = session.query(db.Dataset).filter(db.Dataset.id.in_(ds_ids)).order_by(db.Dataset.id)

        # Alter id and timeranges
        error_ds = [
            ds.id
            for ds in datasets
            if ds.access > ds.get_access_level(users.current)
        ]

        if error_ds:
            error_ds = ', '.join(f'ds{ds}' for ds in error_ds)
            raise ValueError(f'{users.current} may not append to datasets {error_ds}')

        for ds in datasets:
            _adjust_id(df, ds)
            _adjust_time(df, ds)

        # commit to db
        conn = session.connection()
        df.to_sql('record', conn, if_exists='append', index=False, method='multi', chunksize=1000)
        return ds_ids, len(df)

def addrecords_parquet(filename):
    """
    Expects a table in the apache arrow format to import records to existing datasets. Expected column names:
    dataset, id, time, value [,sample, comment, is_error]
    """
    df = pd.read_parquet(filename)
    return addrecords_dataframe(df)

if __name__ == '__main__':
    import sys
    logger.setLevel(logging.INFO)
    addrecords_parquet(sys.argv[1])

