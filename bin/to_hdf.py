import tables
import pandas as pd
from odmf import db
from sqlalchemy.types import JSON
from sqlalchemy.sql.selectable import Select

import time
from typing import Optional

def now(ago=None):
    if ago is None:
        return pd.to_datetime('now')
    else:
        ago = pd.to_timedelta(ago)
        return pd.to_datetime('now') - ago


    
def load_sql(session, t: str, limit: int = None, records_since = None):
    query = session.query(db.Base.metadata.tables[t])
    if records_since is not None and t == 'record':
        records_since = pd.to_datetime(records_since)
        query = query.filter(db.Record.time >= records_since )
    if limit is not None:
        query = query.limit(limit)
    return pd.read_sql(query.statement, session.bind)

def get_select( t: str, limit: int = None, records_since = None):
    """
    https://medium.com/data-science/optimizing-pandas-read-sql-for-postgres-f31cd7f707ab
    """
    import io
    query = db.sql.select(db.Base.metadata.tables[t])
    if records_since is not None and t == 'record':
        records_since = pd.to_datetime(records_since)
        query = query.filter(db.Record.time > records_since )
    if limit is not None:
        query = query.limit(limit)
    return query

def to_pandas(source, session, format='csv'):
    """
    Compiles the select statement source for session 
    (SQL-injection possible, never use untrusted text parameters in source)
    and uses postgresql's COPY TO for fast reading of content either in CSV or parquet.
    For some reason, CSV is faster. Simple non-ORM statements work better,
    eg. prefer `select(db.Record.__table__).filter(...)` before `select(db.Record).filter(...)`
    """
    import io
    formats = dict(
        csv='WITH CSV HEADER',
        parquet="WITH (format 'parquet')"
    )
    con = session.connection().connection
    compiled = source.compile(dialect=session.bind.dialect, compile_kwargs={'literal_binds': True})
    cursor = con.cursor()
    query = cursor.mogrify(compiled.string, compiled.params).decode()
    copy = 'COPY ({}) TO STDOUT {}'.format(query, formats[format])
    store = io.BytesIO()
    cursor.copy_expert(copy, store)
    store.seek(0)
    df = getattr(pd, f'read_{format}')(store)
    return df




def to_hdf(fn: str, *, limit: int = None, complevel: int = 9, records_since = None):
    """
    Exports all tables of the ORM system to an HDF file. This can be used for backup or migration purposes.

    fn: The filename to export to. If the file already exists, it will be overwritten.
    limit: If not None, limits the number of rows exported for each table to this number. This can be used for testing or to export only a subset of the data.

    Exporting 70M rows from the record table takes about 10 minutes, so be patient when exporting large databases.
    """
    with db.session_scope() as session:
        for t in db.Base.metadata.tables:
            print(f'Exporting {t}...', end=' ')
            start_time = time.time()
            df = load_sql(session, t, limit, records_since)
            load_time = time.time()
            print(f'loaded {len(df)} rows from {t} in {load_time - start_time:.2f}s')
            df.to_hdf(fn, key=t, mode='a', complevel=complevel, format='fixed')
            end_time = time.time()
            print(f'wrote to {fn} in {end_time - load_time:.2f}s.')

def to_pickle(fn: str, *, limit: int = None, complevel: int = 9, records_since = None):
    """
    Exports all tables of the ORM system to an HDF file. This can be used for backup or migration purposes.

    fn: The filename to export to. If the file already exists, it will be overwritten.
    limit: If not None, limits the number of rows exported for each table to this number. This can be used for testing or to export only a subset of the data.

    Exporting 70M rows from the record table takes about 10 minutes, so be patient when exporting large databases.
    """
    with db.session_scope() as session:
        for t in db.Base.metadata.tables:
            print(f'{t}...', end=' ')
            start_time = time.time()
            df = load_sql(session, t, limit, records_since)
            load_time = time.time()
            print(f'loaded {len(df)} rows from {t} in {load_time - start_time:.2f}s', end=' ')
            df.to_pickle(t + '.' + fn)
            end_time = time.time()
            print(f'and wrote to {fn} in {end_time - load_time:.2f}s.')


def from_hdf(fn: str):
    """
    Imports all tables of the ORM system from an HDF file. This can be used for backup or migration purposes.
    fn: The filename to import from. The file must have been created using the to_hdf function.

     Importing 70M rows from the record table takes about 10 minutes, so be patient when importing large databases.
    """
    with db.session_scope() as session:
        for t in db.Base.metadata.tables:
            print(f'Importing {t}...')
            dtype = {c.name: c.type for c in db.Base.metadata.tables[t].columns}
            df = pd.read_hdf(fn, key=t)
            table = db.Base.metadata.tables[t]
            for df_c in df.columns:
                if df_c not in table.columns:
                    del table[df_c]
            df.to_sql(t, session.bind, if_exists='delete_rows', index=False, dtype=dtype)

if __name__ == '__main__':
    ...
