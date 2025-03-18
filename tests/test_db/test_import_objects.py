import pytest
import pandas as pd
import numpy as np
import geopandas as gpd
import shapely.geometry
import io

from . import db, session, conf

import odmf.tools.import_objects as impo


def as_polygon(lon: float, lat: float):
    return shapely.geometry.Polygon([[lon-0.1, lat-0.1],[lon+0.1, lat-0.1], [lon+0.1, lat+0.1],[lon-0.1, lat+0.1]])


@pytest.fixture
def site_table():
    def make_table_stream(format: str, *excluded_columns, n=10):
        
        lat = np.random.uniform(50, 51, n)
        lon = np.random.uniform(8, 9, n)
        if format == 'geojson':
            df = gpd.GeoDataFrame(geometry=[as_polygon(x, y) for x, y in zip(lon, lat)], crs='epsg:4326')
        else:
            df = pd.DataFrame(index=pd.RangeIndex(0, n))
        df['id'] = df.index
        df['lat'] = lat
        df['lon'] = lon
        df['name'] = [f'site:{i+1}' for i in df.index]
        df['height'] = df.index * 0.1
        df['icon'] = 'icon.png'
        df['comment'] = format + '|' + '|'.join(excluded_columns)
        df['strokewidth'] = 3
        df['strokecolor'] = '#FFF'
        df['strokeopacity'] = 0.8
        df['fillcolor'] = '#FFF'
        df['fillopacity'] = 0.2

        for f in excluded_columns:
            if f in df.columns:
                del df[f]

        buffer = io.BytesIO()
        if format == 'geojson':
            df.to_file(buffer, driver='GeoJSON', index=False)
        elif format == 'csv':
            df.to_csv(buffer, index=False)
        elif format == 'xlsx':
            df.to_excel(buffer, index=False)
        elif format == 'parquet':
            df.to_parquet(buffer, index=False)

        buffer.seek(0)
        return 'sites.' + format, buffer

    return make_table_stream

fmts = ['xlsx',  'csv', 'parquet', 'geojson']
site_table_params = (
    [[fmt, []] for fmt in fmts] +
    [[fmt, ['id']] for fmt in fmts] +
    [[fmt, ['id', 'height']] for fmt in fmts] +
    [['geojson', ['id', 'lon', 'lat', 'height']]]
)

@pytest.mark.parametrize('format,excluded_columns',  site_table_params)
def test_site_table(format, excluded_columns, db, session, site_table):

        fn, buffer = site_table(format, *excluded_columns)
        report = impo.import_sites_from_stream(session, fn, buffer)
        assert report.keyname == 'id'
        assert report.tablename == 'site'
        session.commit()
        sites = session.scalars(db.sql.select(db.Site).where(db.Site.id.in_(report.keys))).all()
        assert len(sites) == len(report.keys)
        assert all(s.comment == format + '|' + '|'.join(excluded_columns) for s in sites)

site_table_params_fail = (
    [[fmt, ['name']] for fmt in fmts] +
    [[fmt, ['lon']] for fmt in ['xlsx', 'csv', 'parquet']] +
    [[fmt, ['lat']] for fmt in ['xlsx', 'csv', 'parquet']] +
    [['oireuw', []]]
)

@pytest.mark.parametrize('format,excluded_columns', site_table_params_fail)
def test_site_table_fail(format, excluded_columns, db, session, site_table):
    fn, buffer = site_table(format, *excluded_columns)
    with pytest.raises(impo.ObjectImportError, match=r'.*'):
        impo.import_sites_from_stream(session, fn, buffer)

@pytest.mark.parametrize('format', fmts)
def test_site_table_undo(format, db, site_table):
    fn, buffer = site_table(format, 'id')
    with db.session_scope() as sess:
        report = impo.import_sites_from_stream(sess, fn, buffer)
        assert report.keyname == 'id'
        assert report.tablename == 'site'

    report_dict = report.asdict()

    report = impo.ObjectImportReport(**report_dict)

    with db.session_scope() as sess:
        sites = sess.scalars(db.sql.select(db.Site).where(db.Site.id.in_(report.keys))).all()
        assert len(sites) == len(report.keys)
        if format == 'geojson':
            sgeo = pd.read_sql_table('site_geometry', sess.connection())
            assert len(sgeo[sgeo.id.isin(report.keys)]) == len(report.keys)

    with db.session_scope() as sess:
        report.undo(sess)

    with db.session_scope() as sess:
        sites = sess.scalars(db.sql.select(db.Site).where(db.Site.id.in_(report.keys))).all()
        assert len(sites) == 0
        if format == 'geojson':
            sgeo = pd.read_sql_table('site_geometry', sess.connection())
            assert len(sgeo[sgeo.id.isin(report.keys)]) == 0




