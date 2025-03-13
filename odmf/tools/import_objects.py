"""
This module provides functions to import database objects from tabular data.

Mainly for sites and datasets, but eventually more like Users, Instruments, etc.
"""

import typing

import pandas as pd
import geopandas as gpd
from shapely import to_geojson
from .. import db
from io import BytesIO
import warnings

class ObjectImportError(Exception):
    ...


def import_sites_from_stream(filename: str, stream: BytesIO) -> typing.List[int]:
    if filename.endswith('.xlsx'):
        df = pd.read_excel(stream)
    elif filename.endswith('.csv'):
        df = pd.read_csv(stream)
    elif filename.endswith('.geojson'):
        df = gpd.read_file(stream)
        with warnings.catch_warnings():
            df['centroid'] = df.geometry.centroid.to_crs(epsg=4326)
        df = df.to_crs(epsg=4326)
        if 'lat' not in df.columns or 'lon' not in df.columns:
            df['lon'] = df.centroid.x
            df['lat'] = df.centroid.y
    else:
        raise ObjectImportError(f'{filename} is not a supported file type [.xlsx, .csv, .geojson]')

    return import_sites_from_dataframe(df)


def import_sites_from_dataframe(df: pd.DataFrame) -> typing.List[int]:
    """
    Imports sites from a pnadas DataFrame or a GeoDataFrame.

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

    with db.session_scope() as session:
        newid = session.newid(db.Site)
        df['id'] = newid + df.index
        df_site = df[['id', 'lat', 'lon', 'height', 'name', 'comment']]
        df_site.to_sql('site', index=False, con=session.connection(), if_exists='append')

        if type(df) is gpd.GeoDataFrame:
            df_geo = df['id']
            df_geo['geojson'] = df.geometry.apply(to_geojson)
            fields = ['strokewidth', 'strokecolor', 'strokeopacity', 'fillcolor', 'fillopacity']
            for f in fields:
                df_geo[f] = df.get(f)

            df_geo.to_sql('site_geometry', session.connection(), if_exists='append', index=False)

    return list(df['id'])







