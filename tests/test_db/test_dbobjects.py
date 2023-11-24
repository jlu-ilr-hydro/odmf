import datetime

import pytest
from PIL import Image
import random
import string
from . import temp_in_database, db, session, conf


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


@pytest.fixture()
def person(db, session):
    with temp_in_database(
        db.Person(
            username=randomstring(10), email='This is an email', firstname='first',
            surname='last', telephone='this is a phone number', comment='this is a comment',
            can_supervise= False, mobile='this is a mobile number', car_available=0
        ),
        session) as person:
        yield person

class TestPerson:
    def test_person(self, person):
        assert person
        assert isinstance(person.firstname, str)
        assert isinstance(person.surname, str)
        d = person.__jdict__()
        assert isinstance(d, dict)
        assert 'username' in d


@pytest.fixture()
def log(db, session, person, site1_in_db):
    with temp_in_database(
        db.Log(
            id=1, time=datetime.datetime(2022, 2, 17),
            user=person, site=site1_in_db, message='this is a message'
        ),
        session) as log:
        yield log

class TestLog:
    def test_log(self, log):
        assert log
        assert log.id == 1
        assert log.site.id == 1
        assert isinstance(log.time, datetime.datetime)
        assert isinstance(log.message, str)
        d = log.__jdict__()
        assert isinstance(d, dict)
        assert 'id' in d

    def test_log_load(self, log, session, db):
        log_1 = session.query(db.Log).get(1)
        assert log_1 == log
        assert not log < log


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

class TestJob:
    def test_job(self, job):
        assert job
        assert job.id == 1
        assert isinstance(job.due, datetime.datetime)
        d = job.__jdict__()
        assert isinstance(d, dict)
        assert 'id' in d

    def test_job_load(self, job, session, db):
        job_1 = session.query(db.Job).get(1)
        assert job_1 == job
        assert not job < job
        assert repr(job).startswith("<Job")

    def test_due_time(self, job):
        assert job.due - datetime.timedelta(days=1) > datetime.datetime(2023, 3, 10)


@pytest.fixture()
def project(db, session, person):
    with temp_in_database(
        db.Project(
            id=1, person_responsible=person, name='this is a name', comment='this is a comment'
        ),
        session) as project:
        yield project


class TestProject:
    def test_project(self, project):
        assert project
        assert project.id == 1
        d = project.__jdict__()
        assert isinstance(d, dict)
        assert 'id' in d

    def test_project_load(self, project, session, db):
        project_1 = session.query(db.Project).get(1)
        assert project_1 == project

    def test_project_add_member(self, project, person):
        project.add_member(person, 2)
        members = list(project.members())
        print(members)
        assert len(members) >= 1# , f'Added 1 one member to project, but project has {len(members)} member'
        assert members[0][1] == 2# , f'Project member has unexpected access level of {members[0].access_level}!=1'

        members2 = list(project.members(3)) # should be empty list
        print(members2)
        assert len(members2) == 0 , f'Added one member with al=2 to project, but project has {len(members2)} members above level 3'

    def test_person_add_project(self, project, person):
        person.add_project(project, 1)
        projects = list(person.projects())
        print(projects)
        assert len(projects) >= 1 , f'Added 1 one member to project, but project has {len(projects)} member'
        assert projects[0][1] == 1 , f'Project member has unexpected access level of {projects[0][1]}!=1'



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


class TestImage:
    def test_image(self, image):
        assert image
        assert image.image64()
        assert len(image.image) > 0
        assert len(image.thumbnail) > 0