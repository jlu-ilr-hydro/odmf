import datetime

import pytest
from PIL import Image
import random
import string
from . import temp_in_database, db, session


def randomstring(n):
    return ''.join(random.sample(string.ascii_lowercase, n))

@pytest.fixture()
def site1_in_db(db, session):
    with temp_in_database(
            db.Site(
                id=1, lat=50.5, lon=8.5, height=100,
                name='site_1', comment='This is a comment', icon='an_icon.png'
            ),
            session) as site:
        yield site


@pytest.fixture()
def datasource1_in_db(db, session):
    with temp_in_database(
            db.Datasource(
                id=1, name='instr_1', comment='This is a comment',
                sourcetype='sourcetype', manuallink='path/to/manual'
            ),
            session) as site:
        yield site


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


@pytest.fixture()
def person(db, session):
    with temp_in_database(
        db.Person(
            username=randomstring(10), email='This is an email', firstname='first',
            surname='last', telephone='this is a phone number', comment='this is a comment',
            can_supervise= False, mobile='this is a mobile number', car_available=0, access_level=2
        ),
        session) as person:
        yield person


@pytest.fixture()
def log(db, session, person, site1_in_db):
    with temp_in_database(
        db.Log(
            id=1, time=datetime.datetime(2022, 2, 17),
            user=person, site=site1_in_db, message='this is a message'
        ),
        session) as log:
        yield log

@pytest.fixture()
def job(db, session, person):
    with temp_in_database(
        db.Job(
            id=1, name='this is a name', description='this is a description',
            due=datetime.datetime(2023, 5, 20), author=person,
            responsible=person, done=True, repeat=3,
            link='/path/to/link', type='this is a type',
            donedate=datetime.datetime(2023, 2,20)
        ),
        session) as job:
        yield job


@pytest.fixture()
def project(db, session, person):
    with temp_in_database(
        db.Project(
            id=1, person_responsible=person, name='this is a name', comment='this is a comment'
        ),
        session) as project:
        yield project


@pytest.fixture()
def image(tmp_path, db, session, site1_in_db, person):

    img = Image.new(mode='RGB', size=(400, 300), color=(30, 226, 76))
    img.save(tmp_path / 'test_image.png')

    with temp_in_database(
        db.Image(
            time=datetime.datetime(2021, 7, 10), format='png',
            site=site1_in_db, by=person,
            imagefile=str(tmp_path / 'test_image.png')
        ),
        session) as image:
        yield image

