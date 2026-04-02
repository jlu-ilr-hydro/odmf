import tables
import pandas as pd
from odmf import db
from sqlalchemy.types import JSON
import time

def to_hdf(fn: str, limit: int = None):
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
            query = session.query(db.Base.metadata.tables[t])
            if limit is not None:
                query = query.limit(limit)
            df = pd.read_sql(query.statement, session.bind)
            df.to_hdf(fn, key=t, mode='a')
            end_time = time.time()
            print(f' in {end_time - start_time:.2f} seconds.')


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
            df.to_sql(t, session.bind, if_exists='delete_rows', index=False, dtype=dtype)