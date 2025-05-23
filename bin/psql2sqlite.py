"""
Imports a PostgreSQL dump into sqlite db for test puroposes

1) make a new odmf instance with `odmf configure` / `odmf db-create`
2) In an interactive session with the source instance run `export_all_tables` to create parquet files for each table
3) 
"""
import pandas as pd
from odmf import db
from pathlib import Path

tables = db.base.metadata.tables
def export_all_tables(path, skip_records=False):
    
    """Exports all tables from an ODMF instance as parquet"""
    

    for t in tables:
        if skip_records and t=='record':
            continue
        df = pd.read_sql_table(t, db.engine)
        df.to_parquet(path + '/' + t + '.parquet')
        print(path + '/' + t + '.parquet')

def import_table(path, t, delete=False):
    fn = path + '/' + t + '.parquet'
    df = pd.read_parquet(fn)
    if delete:
        stmt = db.sql.delete(tables[t])
        with db.engine.connect() as con:
            con.execute(stmt)
            print('delete', t)
            con.commit()
    df.to_sql(t, db.engine, if_exists='append', index=False)
    
def import_all_tables(path='.', delete=True, skip_records=False):
    
    for t in tables:
        if skip_records and t=='record':
            continue
        import_table(path, t, delete)
        print(t)
