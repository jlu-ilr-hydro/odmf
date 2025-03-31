import pytest
import pandas as pd
import numpy as np
import geopandas as gpd
import shapely.geometry
import io

from . import db, conf, session

from .test_dbobjects import person, site1_in_db, project
from .test_dbdataset import value_type, datasource1_in_db, quality 
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
        elif format == 'ods':
            df.to_excel(buffer, index=False, engine='odf')
        elif format == 'parquet':
            df.to_parquet(buffer, index=False)

        buffer.seek(0)
        return 'sites.' + format, buffer

    return make_table_stream

fmts = ['xlsx',  'csv', 'parquet', 'ods', 'geojson']
site_table_params = (
    [[fmt, []] for fmt in fmts] +
    [[fmt, ['id']] for fmt in fmts] +
    [[fmt, ['id', 'height']] for fmt in fmts] +
    [['geojson', ['id', 'lon', 'lat', 'height']]]
)

@pytest.mark.parametrize('format,excluded_columns',  site_table_params)
def test_site_table(format, excluded_columns, db, session, site_table):
    fn, buffer = site_table(format, *excluded_columns)
    report = impo.import_sites_from_stream(session, fn, buffer, 'odmf.admin')
    assert report.keyname == 'id'
    assert report.tablename == 'site'
    session.commit()
    sites = session.scalars(db.sql.select(db.Site).where(db.Site.id.in_(report.keys))).all()
    assert len(sites) == len(report.keys)
    assert all(s.comment == format + '|' + '|'.join(excluded_columns) for s in sites)

site_table_params_fail = (
    [[fmt, ['name']] for fmt in fmts] +
    [[fmt, ['lon']] for fmt in ['xlsx', 'ods', 'csv', 'parquet']] +
    [[fmt, ['lat']] for fmt in ['xlsx', 'ods', 'csv', 'parquet']] +
    [['oireuw', []]]
)

@pytest.mark.parametrize('format,excluded_columns', site_table_params_fail)
def test_site_table_fail(format, excluded_columns, db, session, site_table):
    fn, buffer = site_table(format, *excluded_columns)
    with pytest.raises(impo.ObjectImportError, match=r'.*'):
        impo.import_sites_from_stream(session, fn, buffer, 'odmf.admin')

@pytest.mark.parametrize('format', fmts)
def test_site_table_undo(format, db, session, site_table):
    fn, buffer = site_table(format, 'id')
    with db.session_scope() as sess:
        report = impo.import_sites_from_stream(sess, fn, buffer, 'odmf.admin')
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


@pytest.fixture
def dataset_table():
    def make_table_stream(format: str, *excluded_columns, n=10):
        
     
        df = pd.DataFrame(index=pd.RangeIndex(0, n))
        df['id'] = df.index
        df['name'] = [f'dataset:{i+1}' for i in df.index]
        df['start'] = pd.date_range('2020-01-01', periods=n, freq='D')
        df['end'] = pd.date_range('2020-01-02', periods=n, freq='D')
        df['valuetype'] = 1
        df['site'] = 1
        df['source'] = 1
        df['type'] = 'timeseries'
        df['access'] = 1
        df['project'] = 1
        df['comment'] = format + '|' + '|'.join(excluded_columns)
        df['level'] = -0.5
        df['quality'] = 4
        df['timezone'] = 'UTC'

        for f in excluded_columns:
            if f in df.columns:
                del df[f]

        buffer = io.BytesIO()
        if format == 'csv':
            df.to_csv(buffer, index=False)
        elif format == 'xlsx':
            df.to_excel(buffer, index=False)
        elif format == 'ods':
            df.to_excel(buffer, index=False, engine='odf')
        elif format == 'parquet':
            df.to_parquet(buffer, index=False)

        buffer.seek(0)
        return 'datasets.' + format, buffer

    return make_table_stream

dataset_table_params = (
    [[fmt, []] for fmt in fmts[:-1]] +
    [[fmt, ['id']] for fmt in fmts[:-1]] +
    [[fmt, ['start', 'end']] for fmt in fmts[:-1]]
)

@pytest.fixture
def db_object_maker(db, session, person):
    def make_object(cls, **kwargs):
        obj = cls( **kwargs)
        session.add(obj)
        session.flush()
        return obj
    return make_object

@pytest.mark.parametrize('format,excluded_columns',  dataset_table_params)
def test_dataset_table(format, excluded_columns, db, session, dataset_table, person, db_object_maker):
    fn, buffer = dataset_table(format, *excluded_columns)
    quality = db_object_maker(db.Quality, name='quality', id=4)
    site = db_object_maker(db.Site, name='site', lat=50, lon=8, height=100, id=1)
    valuetype = db_object_maker(db.ValueType, name='valuetype', id=1)
    datasource = db_object_maker(db.Datasource, name='instrument', id=1)
    project = db_object_maker(db.Project, name='project', id=1)
    session.commit()
    report = impo.import_datasets_from_stream(session, fn, buffer, person.username)
    assert report.keyname == 'id'
    assert len(report.keys) == 10
    assert report.tablename == 'dataset'
    session.commit()
    datasets = session.scalars(db.sql.select(db.Dataset).where(db.Dataset.id.in_(report.keys))).all()
    assert len(datasets) == len(report.keys)
    assert all(d.comment == format + '|' + '|'.join(excluded_columns) for d in datasets)
    report.undo(session)
    session.commit()
    datasets = session.scalars(db.sql.select(db.Dataset).where(db.Dataset.id.in_(report.keys))).all()
    session.delete(quality)
    session.delete(site)
    session.delete(valuetype)
    session.delete(datasource)
    session.delete(project)
    session.commit()
    assert len(datasets) == 0

