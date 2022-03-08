import datetime

import numpy as np
import pandas as pd
import pytest
import sqlalchemy.orm
from contextlib import contextmanager
from tests.test_db.test_dbobjects import person, site1_in_db, datasource1_in_db
import pathlib



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
            level=2
        ),
        session) as dataset:
        yield dataset


class TestDataset:
    def test_dataset(self, site1_in_db, dataset):
        assert dataset.id == 1
        assert dataset.type is None
        assert dataset.site == site1_in_db


@pytest.fixture()
def timeseries(db, session, value_type, quality, person, datasource1_in_db, site1_in_db):
    with temp_in_database(
            db.Timeseries(
                id=1, name='this is a name', filename='this is a filename',
                start=datetime.datetime(2020, 2, 20), end=datetime.datetime(2030, 12, 20),
                site=site1_in_db, valuetype=value_type, measured_by=person, quality=quality,
                source=datasource1_in_db, calibration_offset=0, calibration_slope=1, comment='this is a comment',
                level=2
            ),
            session) as timeseries:
        yield timeseries



@pytest.fixture()
def record(db, session, timeseries):
    with temp_in_database(
        db.Record(
            id=1, dataset=timeseries, time=datetime.datetime(2021, 5, 10),
            value=5, sample='this is a sample', comment='this is a comment',
            is_error=False
        ),
        session) as record:
        yield record


@pytest.fixture()
def thousand_records(tmp_path):
    id = [1] * 1000
    data = np.arange(-10, 190, 0.2)
    date = pd.date_range('2022-01-01', periods=len(data), freq='h')
    d = {'id': id, 'date': date, 'values': data}
    df = pd.DataFrame(d)
    df.to_csv(tmp_path / 'df_to_csv.csv')
    ... # TODO: save to database

# save csv to db
import csv
from sqlalchemy import Column, Date, Float, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dateutil.parser import parse

engine = create_engine('sqlite:///thousand_records.sqlite3')
Base = declarative_base()

class thousand_records_table(Base):
    __tablename__ ='thousand_records'

    id = Column(Integer, primary_key=True)
    Date = Column(Date, nullable=True)
    Values = Column(Float)

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

def parse_none(dt):
    try:
        return parse(dt)
    except:
        return None

def prepare_thousands_records(row):
    row['Date'] = parse_none(row['Date'])
    return thousand_records_table(**row)

with open(str(tmp_path / 'df_to_csv')) as csv_file:
    csvreader = csv.DictReader(csv_file)

    thousand_records_listing = [prepare_thousands_records(row) for row in csvreader]

    session = Session()
    session.add_all(thousand_records_listing)
    session.commit()

class TestTimeseriesThousandRecords:

    def test_timeseries_thousand_records(self, thousand_records_listing):
        assert thousand_records_listing


class TestTimeseries:

    def test_timeseries_empty(self, timeseries):
        assert timeseries
        assert timeseries.records.count() == 0
        d = timeseries.__jdict__()
        assert isinstance(d, dict)
        assert 'id' in d


    def test_record(self, timeseries, record):
        assert record
        assert record.id == 1
        assert str(record).startswith(record.dataset.name)
        d = record.__jdict__()
        assert isinstance(d, dict)
        assert 'id' in d
        assert timeseries.records.count() == 1


