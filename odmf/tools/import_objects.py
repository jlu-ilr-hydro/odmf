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
        return f'{self.tablename}-{self.user}-{self.time:%Y-%m-%d-%H-%M}'
    
    def filename(self):
        return self.name + '.undo'
    
    def save(self, path: Path):
        """
        Saves the result as yaml file in path/tablename-user-2025-03-18-12-10.undo

        path: PAth to directory. The filename is derived from self        
        """
        with (path / self.filename).open('w') as f:
            yaml.safe_dump(self, f)

def load_undo_file(path: Path):
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



def read_df_from_stream(filename: str, stream: typing.BinaryIO) -> pd.DataFrame:
    """
    Reads a dataframe from a stream, either in .xlsx, .csv or .parquet
    """
    if filename.endswith('.xlsx'):
        return pd.read_excel(stream)
    elif filename.endswith('.csv'):
        return pd.read_csv(stream)
    elif filename.endswith('.parquet'):
        return pd.read_parquet(stream)
    else:
        raise ObjectImportError(f'{filename} is not a supported file type')


def import_sites_from_stream(session: db.orm.Session, filename: str, stream: typing.BinaryIO) -> ObjectImportReport:
    """
    Imports sites from a stream containing tabular data
    """
    if filename.endswith('.geojson'):
        df = gpd.read_file(stream)
        with warnings.catch_warnings():
            df['centroid'] = df.geometry.centroid.to_crs(epsg=4326)
        df = df.to_crs(epsg=4326)
        if 'lat' not in df.columns or 'lon' not in df.columns:
            df['lon'] = df.centroid.x
            df['lat'] = df.centroid.y
    else:
        df = read_df_from_stream(filename, stream)

    site_ids = import_sites_from_dataframe(session, df)
    return ObjectImportReport(f'Bulk site import from {filename}', 'site', 'id', site_ids, datetime.now())

def import_sites_from_dataframe(session: db.orm.Session, df: pd.DataFrame) -> typing.List[int]:
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

    :param filename: File name to import, should end with .xlsx, .csv or .geojson
    :param stream: Byte stream containing data (file like object)
    :return: List of new site ids
    """

    # Check for required fields and raise exception if missing
    missing = [cname for cname in ['lat', 'lon', 'name'] if cname not in df.columns]
    if missing:
        raise ObjectImportError(f'{','.join(missing)} column names are missing')

    # Add optional fields
    if 'icon' not in df.columns:
        df['icon'] = 'unknown.png'
    if 'height' not in df.columns:
        df['height'] = None

    newid = db.newid(db.Site, session)
    df['id'] = newid + df.index
    df_site = df[['id', 'lat', 'lon', 'height', 'name', 'comment']]
    df_site.to_sql('site', index=False, con=session.connection(), if_exists='append')

    if type(df) is gpd.GeoDataFrame:
        df_geo = pd.DataFrame(index=df.index)
        df_geo['id'] = df['id']
        df_geo['geojson'] = df.geometry.apply(to_geojson)
        for f in ['strokewidth', 'strokecolor', 'strokeopacity', 'fillcolor', 'fillopacity']:
            df_geo[f] = df.get(f)

        df_geo.to_sql('site_geometry', session.connection(), if_exists='append', index=False)
    
    return list(df['id'])


def import_datasets_from_df(session: db.orm.Session, df: pd.DataFrame) -> typing.List[db.Dataset]:
    """
    Imports datasets from a table, perform various checks
    """

    raise ObjectImportError('Importing datasets is not implemented yet')






