import datetime
import pytest
import sqlalchemy.orm
from contextlib import contextmanager
from tests.test_db.test_dbobjects import person, site1_in_db, datasource1_in_db



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
def quality(db, session):
    with temp_in_database(
        db.Quality(
            id=4, name='this is a name', comment='this is a comment'
        ),
        session) as quality:
        yield quality

class TestQuality:
    def test_quality(self, quality):
        assert quality
        assert quality.id == 4
        assert str(quality).startswith(quality.name)
        d = quality.__jdict__()
        assert isinstance(d, dict)
        assert 'id' in d


@pytest.fixture()
def value_type(db, session):
    with temp_in_database(
        db.ValueType(
            id=1, name='this is a name', unit='this is a unit',
            comment='this is a comment', minvalue=0.00, maxvalue=110.20
        ),
        session) as value_type:
        yield value_type

class TestValueType:
    def test_ValueType(self, value_type):
        assert value_type
        assert value_type.id == 1
        assert str(value_type).startswith(value_type.name)
        d = value_type.__jdict__()
        assert isinstance(d, dict)
        assert 'id' in d

    def test_ValueType_load(self, value_type, session, db):
        value_type_1 = session.query(db.ValueType).get(1)
        assert hash(value_type_1) == hash(value_type)
        assert not value_type < value_type
        assert not value_type_1 == value_type


@pytest.fixture()
def dataset(db, session, value_type, quality, person, datasource1_in_db, site1_in_db):
    with temp_in_database(
        db.Dataset(
            id=1, name='this is a name', filename='this is a filename',
            start=datetime.datetime(2020, 2, 20), end=datetime.datetime(2030, 12, 20),
            site=site1_in_db, valuetype=value_type, measured_by=person, quality=quality,
            source=datasource1_in_db, calibration_offset=0, calibration_slope=1, comment='this is a comment',
            type='this is a type', level=2
        ),
        session) as dataset:
        yield dataset


@pytest.fixture()
def record(db, session, dataset):
    with temp_in_database(
        db.Record(
            id=1, dataset=dataset, time=datetime.datetime(2021, 5, 10),
            value=5, sample='this is a sample', comment='this is a comment',
            is_error=False
        ),
        session) as record:
        yield record

class TestRecord:
    def test_record(self, record):
        assert record
        assert record.id == 1
        assert str(record).startswith(record.dataset.name)
        d = value_type.__jdict__()
        assert isinstance(d, dict)
        assert 'id' in d
