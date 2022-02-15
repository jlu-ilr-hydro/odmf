import pytest
import sqlalchemy.orm

@pytest.fixture(scope='class')
def conf():
    from odmf.config import Configuration
    conf = Configuration()
    conf.database_url = 'sqlite://'
    conf.utm_zone = '32N'
    return conf


@pytest.fixture(scope='class')
def db(conf):
    from odmf import config
    config.conf = conf
    from odmf import db
    from odmf.tools import create_db as cdb
    cdb.create_all_tables()
    cdb.add_admin('test')
    cdb.add_quality_data(cdb.quality_data)
    return db


@pytest.fixture()
def session(db) -> sqlalchemy.orm.Session:
    with db.session_scope() as session:
        yield session


@pytest.fixture()
def site1_in_db(db, session):
    site = db.Site(
            id=1, lat=50.5, lon=8.5, height=100,
            name='site_1', comment='This is a comment', icon='an_icon.png'
        )
    session.add(site)
    session.commit()
    yield site
    session.delete(site)
    session.commit()


class TestSite:
    """
    Unittest for db.Site
    """
    def test_create_site_lat_lon(self, db, session):
        site = db.Site(
            id=2, lat=50.5, lon=8.5, height=100,
            name='site_lonlat', comment='This is a comment', icon='an_icon.png'
        )
        assert site.id == 2 and site.name == 'site_lonlat'
        assert repr(site).startswith('Site')
        session.add(site)

    def test_create_site_x_y(self, db, session):
        site = db.Site(
            id=3, x=464539.5541877102, y=5594344.786516231, height=100,
            name='site_xy', comment='This is a comment', icon='an_icon.png'
        )

        assert site.id == 3 and site.name == 'site_xy'
        assert repr(site).startswith('Site')
        assert str(site).startswith('#')
        assert abs(site.lon - 8.5) < 1e-4, 'Longitude differs from expected value'
        assert abs(site.lat - 50.5) < 1e-4, 'Latitude differs from expected value'
        zone, y, x = site.as_UTM()
        assert zone[:2] == db.conf.utm_zone[:2]
        assert '°' in site.as_coordinatetext()

        session.add(site)

    def test_create_site_fail(self, db, session):
        with pytest.raises(ValueError):
            site = db.Site(id=3, name='xyz')

    def test_site_load(self, db, session, site1_in_db):
        site = session.query(db.Site).get(1)
        assert site == site1_in_db
        assert not site < site
        assert hash(site) == hash(site1_in_db)
        d = site.__jdict__()
        assert 'id' in d




