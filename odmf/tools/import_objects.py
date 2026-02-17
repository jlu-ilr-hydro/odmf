"""
This module provides functions to bulk import database objects from tabular data.

Mainly for sites and datasets, but eventually more like Users, Instruments, etc.
"""

import typing

import pandas as pd
import geopandas as gpd
from shapely import to_geojson
from pathlib import Path
import yaml

from .. import db
from sqlalchemy import MetaData
import warnings
from dataclasses import dataclass, asdict
from datetime import datetime

class ObjectImportError(Exception):
    ...


def dbcount(session, column: db.sql.Column, where):
    return session.scalar(db.sql.select(db.sql.func.count(column)).where(where))

@dataclass
class ObjectImportReport:
    """
    This class contains information about a bulk import action and can undo that action
    """
    name: str
    tablename: str
    keyname: str
    keys: typing.List[str|int]
    time: datetime
    user: str = None
    warnings: typing.List[str] = None

    def undo(self, session: db.orm.Session):
        metadata = MetaData()
        metadata.reflect(bind=db.engine)
        table = metadata.tables[self.tablename]
        column = table.c[self.keyname]
        stmt = db.sql.delete(table).where(column.in_(self.keys))
        result = session.execute(stmt)
        n = result.rowcount
        if self.tablename == 'site':
            table = metadata.tables[self.tablename + '_geometry']
            column = table.c[self.keyname]
            stmt = db.sql.delete(table).where(column.in_(self.keys))
            session.execute(stmt)

        return n
    
    def asdict(self):
        return asdict(self)
    
    def __str__(self):
        return f'{self.tablename}: {self.name}'
    
    def filename(self):
        return f'{self.tablename}-{self.user}-{self.time:%Y-%m-%d-%H-%M}.undo'
    
    def save(self, path: Path):
        """
        Saves the result as yaml file in path/tablename-user-2025-03-18-12-10.undo

        path: PAth to directory. The filename is derived from self        
        """
        if not path.exists():
            path.mkdir(parents=True)
        with (path / self.filename()).open('w') as f:
            yaml.safe_dump(self.asdict(), f)

def load_undo_file(path: Path) -> ObjectImportReport:
    """
    Loads an undo file from the given path. The path should contain the whole filename
    """
    with path.open() as f:
        data = yaml.safe_load(f)
        return ObjectImportReport(**data)

def list_undo_files(path: Path, tablename: str='*', user:str='*') -> typing.List[Path]:
    """
    Returns the .undo files in the directory, filtered by tablename and user
    """
    glob = f'{tablename}-{user}-*.undo'
    return list(path.glob(glob))


def read_df_from_stream(filename: str, stream: typing.BinaryIO, lower_case_columns=False) -> pd.DataFrame:
    """
    Reads a dataframe from a stream, either in .xlsx, .csv or .parquet
    """
    if filename.endswith('.xlsx'):
        df = pd.read_excel(stream)
    elif filename.endswith('.csv'):
        df = pd.read_csv(stream, sep=None, engine='python')
    elif filename.endswith('.parquet'):
        df = pd.read_parquet(stream)
    else:
        raise ObjectImportError(f'{filename} is not a supported file type')
    if lower_case_columns:
        df.columns = [c.lower() for c in df.columns]
    return df


def import_sites_from_stream(session: db.orm.Session, filename: str, stream: typing.BinaryIO, user:str) -> ObjectImportReport:
    """
    Imports sites from a stream containing tabular data
    """
    if filename.endswith('.geojson'):
        df = gpd.read_file(stream)
        df.columns = [c.lower() for c in df.columns] 
        with warnings.catch_warnings():
            df['centroid'] = df.geometry.centroid.to_crs(epsg=4326)
        df = df.to_crs(epsg=4326)
        if 'lat' not in df.columns or 'lon' not in df.columns:
            df['lon'] = df.centroid.x
            df['lat'] = df.centroid.y
    else:
        df = read_df_from_stream(filename, stream, lower_case_columns=True)

    site_ids, warn = import_sites_from_dataframe(session, df)
    return ObjectImportReport(
        name=f'Bulk site import from {filename}', #
        tablename='site', keyname='id', 
        keys=site_ids, time=datetime.now(),
        user=user,
        warnings=warn
    )


def check_column(df: pd.DataFrame, cname, default: typing.Any=pd.NA, warnings=None):
    if warnings is None:
        warnings = []
    # Add missing column
    if cname not in df.columns:
        df[cname] = default
        warnings.append(cname + ' column added with default value ' + str(default))
    else:
        # Use default for NA values
        na = pd.isna(df[cname])
        df.loc[na, cname] = default
        if na.any():
            warnings.append(f'{na.sum()} NA values in {cname} replaced with default {default}')

def check_fkey(session: db.orm.Session, df: pd.DataFrame, c: db.sql.Column, errors, warnings):
    """
    Check foreign key constraints for a column, appends to errors and warnings
    if the column has no foreign key, it is ignored
    """
    if c.name in df.columns:
        for fkey in c.foreign_keys:
            # Look for NA values in source
            na_count = df[c.name].isna().sum()
            if na_count > 0:
                if c.nullable:
                    warnings.append(f'{c.name} column has {na_count} NA values')
                else:
                    errors.append(f'{c.name} column has {na_count} NULL values')
                    return
            # SQLAlchemy's .in_ operator has problems with pandas int's like pd.int64, so we must convert to
            # the python type equivalent of the referenced column type
            t = fkey.column.type.python_type
            # get all unique keys in the source without NA
            keys = [t(k) for k in df[c.name].unique() if not pd.isna(k)]
            # get the number of existing referenced objects
            n = dbcount(session, fkey.column, fkey.column.in_(keys))
            # if they are not all present - add error
            if n < len(keys):
                errors.append(f'{len(keys) - n} {c.name}s not found in database')
    elif c.nullable:  # if the column is not in the source, but the column is nullable, warn
        warnings.append(f'{c.name} column missing, no references')
    else:  # if the column is not nullable, fail
        errors.append(f'{c.name} column missing')



def import_sites_from_dataframe(session: db.orm.Session, df: pd.DataFrame):
    """
    Imports sites from a pandas DataFrame or a GeoDataFrame.

    The input table needs to have a name column. If the table
    has no geometry column, the table needs to have a lat and lon column.

    The following fields are optional, but imported if present:

     - height: height in meters above ground
     - icon: the name of an map icon (.png file)
     - comment: A comment or description of the site

     A geojson file may contain the following attributes:
    - strokewidth (a float in pixel)
    - strokecolor (a hex string like #FFFFFF)
    - strokeopacity (a float between 0 and 1)
    - fillcolor (a hex string like #FFFFFF)
    - fillopacity (a float between 0 and 1)

    :return: List of new site ids
    """
    warnings = []
    # Check for required fields and raise exception if missing
    missing = [cname for cname in ['lat', 'lon', 'name'] if cname not in df.columns]
    if missing:
        raise ObjectImportError(f'{','.join(missing)} column names are missing')

    # Add optional fields
    if 'icon' not in df.columns:
        df['icon'] = 'unknown.png'
        warnings.append('icon column missing, using default icon')
    
    if 'height' not in df.columns:
        df['height'] = None
        warnings.append('height column missing, using NULL height') 
    

    newid = db.newid(db.Site, session)
    df['id'] = newid + df.index
    df_site = df[['id', 'lat', 'lon', 'height', 'name', 'comment', 'icon']]
    df_site.to_sql('site', index=False, con=session.connection(), if_exists='append')

    if type(df) is gpd.GeoDataFrame:
        df_non_point = df[df.geometry.type != 'Point']
        if len(df_non_point) > 0:
            df_geo = pd.DataFrame(index=df_non_point.index)
            df_geo['id'] = df_non_point['id']
            df_geo['geojson'] = df_non_point.geometry.apply(to_geojson)
            for f in ['strokewidth', 'strokecolor', 'strokeopacity', 'fillcolor', 'fillopacity']:
                df_geo[f] = df_non_point.get(f)

            df_geo.to_sql('site_geometry', session.connection(), if_exists='append', index=False)
    
    return list(df['id']), warnings


def import_datasets_from_stream(session: db.orm.Session, filename: str, stream: typing.BinaryIO, user: str) -> ObjectImportReport:
    """
    Imports sites from a stream containing tabular data
    """
    df = read_df_from_stream(filename, stream, lower_case_columns=True)

    ds_ids, warnings = import_datasets_from_dataframe(session, df, user)
    return ObjectImportReport(
        name=f'Bulk dataset import from {filename}', 
        tablename='dataset', 
        keyname='id', 
        keys=ds_ids, 
        time=datetime.now(),
        user=user,
        warnings=warnings
    )


def import_datasets_from_dataframe(session: db.orm.Session, df: pd.DataFrame, user: str):
    """
    Imports datasets from a table, perform various checks
    """
    errors = []
    warnings = []


    if 'name' not in df.columns:
        warnings.append('name column missing')

    check_column(df,'measured_by', user, warnings)

    # Use check foreign keys and apply db defaults
    for c in db.Dataset.__table__.c.values():
        if c.foreign_keys:
            check_fkey(session, df, c, errors, warnings)
        if c.default:
            check_column(df, c.name, c.default.arg, warnings)
        if c.type.python_type == datetime:
            if c.name in df.columns:
                df[c.name] = pd.to_datetime(df[c.name], errors='coerce')
            check_column(df, c.name, datetime.now(), warnings)
    
    # Set other useful defaults
    check_column(df,'type', 'timeseries', warnings)
    check_column(df, 'level', warnings=warnings)
    check_column(df, 'comment', warnings=warnings)

    if errors:
        raise ObjectImportError('Importing datasets failed: ' + ', '.join(errors))
    
    df['id'] = db.newid(db.Dataset, session) + df.index
    df.to_sql('dataset', session.connection(), if_exists='append', index=False)

    return list(df['id']), warnings


def import_log_from_stream(session: db.orm.Session, filename: str, stream: typing.BinaryIO, user:str) -> ObjectImportReport:
    df = read_df_from_stream(filename, stream, lower_case_columns=True)

    log_ids, warnings = import_log_from_dataframe(session, df, user)
    return ObjectImportReport(
        name=f'Bulk dataset import from {filename}',
        tablename='log',
        keyname='id',
        keys=log_ids,
        time=datetime.now(),
        user=user,
        warnings=warnings
    )


def import_log_from_dataframe(session: db.orm.Session, df: pd.DataFrame, user: str):

    errors = []
    warnings = []

    check_column(df, 'user', user, warnings)
    check_column(df, 'type', warnings=warnings)
    check_column(df, 'time', datetime.now(), warnings=warnings)
    if any(pd.isna(df['type'])):
        errors.append('type must not contain no data')

    check_column(df, 'message', warnings=warnings)
    # Use check foreign keys and apply db defaults
    for c in db.Log.__table__.c.values():
        if c.foreign_keys:
            check_fkey(session, df, c, errors, warnings)

    if errors:
        raise ObjectImportError('Importing datasets failed: ' + ', '.join(errors))

    df['id'] = db.newid(db.Log, session) + df.index
    df.to_sql('log', session.connection(), if_exists='append', index=False)

    return list(df['id']), warnings


def import_objects(session: db.orm.Session, table, filename: str, stream: typing.BinaryIO, user: str) -> ObjectImportReport:
    func_dict = {
        'site': import_sites_from_stream,
        'dataset': import_datasets_from_stream,
        'log': import_log_from_stream
    }

    if table not in func_dict:
        raise ObjectImportError(f'table "{table}" cannot import from tabular data')

    return func_dict[table](session, filename, stream, user)


