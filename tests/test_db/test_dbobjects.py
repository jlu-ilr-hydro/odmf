import datetime

import pytest
import sqlalchemy.orm
from contextlib import contextmanager


@pytest.fixture(scope='class')
def conf():
    """
    Creates a configuration with a :memory: SQLite database
    """
    from odmf.config import Configuration
    conf = Configuration()
    conf.database_url = 'sqlite://'
    conf.utm_zone = '32N'
    return conf


@pytest.fixture(scope='class')
def db(conf):
    """
    Creates a database in memory with the schema from the ORM classes,
    an admin user with Password 'test' and the basic quality levels
    """
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


@contextmanager
def temp_in_database(obj, session):
    """
    Adds the ORM-object obj to the session and commits it to the database.
    After usage the object is deleted from the session and is commited again
    """
    session.add(obj)
    session.commit()
    yield obj
    session.delete(obj)
    session.commit()


@pytest.fixture()
def site1_in_db(db, session):
    with temp_in_database(
            db.Site(
                id=1, lat=50.5, lon=8.5, height=100,
                name='site_1', comment='This is a comment', icon='an_icon.png'
            ),
            session) as site:
        yield site


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
        assert isinstance(d, dict)
        assert 'id' in d


@pytest.fixture()
def datasource1_in_db(db, session):
    with temp_in_database(
            db.Datasource(
                id=1, name='instr_1', comment='This is a comment',
                sourcetype='sourcetype', manuallink='path/to/manual'
            ),
            session) as site:
        yield site


class TestDatasource:
    def test_create_datasource(self, datasource1_in_db):
        assert str(datasource1_in_db).startswith(datasource1_in_db.name)
        assert 'id' in datasource1_in_db.__jdict__()

    def test_manuallink(self, datasource1_in_db):
        assert datasource1_in_db.linkname() == 'manual'
        datasource1_in_db.manuallink = ''
        assert not datasource1_in_db.linkname()

    def test_comparison(self, db, session, datasource1_in_db):
        datasource = session.query(db.Datasource).get(1)
        assert datasource1_in_db == datasource
        assert not datasource1_in_db < datasource
        with pytest.raises(TypeError):
            _ = datasource1_in_db < 2

@pytest.fixture()
def installation(db, session, site1_in_db, datasource1_in_db):
    with temp_in_database(
            db.Installation(
                site1_in_db, datasource1_in_db,
                id=1, installdate=datetime.datetime(2021, 2, 15),
                comment='A test installation'
            ),
            session) as installation:
        yield installation


class TestInstallation:
    def test_installation_load(self, installation):
        assert installation
        assert installation.id == 1
        assert installation.site.id == 1
        assert installation.instrument.id == 1
        assert str(installation).startswith('Installation')
        assert repr(installation).startswith('<Installation(')
        d = installation.__jdict__()
        assert isinstance(d, dict)
        assert 'id' in d

    def test_installation_active(self, installation):
        assert installation.active
        installation.removedate = datetime.datetime(2022, 2, 14)
        assert not installation.active

    def test_installation_backref(self, site1_in_db, datasource1_in_db, installation):
        assert installation == site1_in_db.instruments.first()
        assert installation == datasource1_in_db.sites.first()

    def test_no_site(self, installation):
        installation.site = None
        with pytest.raises(AssertionError):
            installation.session().commit()
        installation.session().rollback()

    def test_no_instrument(self, installation):
        installation.instrument = None
        with pytest.raises(AssertionError):
            installation.session().commit()
        installation.session().rollback()

# TODO: Amir:
# - Person
# - Log
# - Job
# - Project
# In dataset.py:
# - Quality
# - ValueType
# - Record

# Advanced:
# - Image (need to create a temp image with PIL and save to a temp folder)



