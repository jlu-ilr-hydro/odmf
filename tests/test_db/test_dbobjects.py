import datetime

import pytest
from . import db, session, conf
from .db_fixtures import site1_in_db, datasource1_in_db, log, job, job_repeat, project, person, installation, image


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


    def test_site_load(self, db, session, site1_in_db):
        site = session.get(db.Site, 1)
        assert site == site1_in_db
        assert not site < site
        assert hash(site) == hash(site1_in_db)
        d = site.__jdict__()
        assert isinstance(d, dict)
        assert 'id' in d


class TestDatasource:
    def test_create_datasource(self, datasource1_in_db):
        assert str(datasource1_in_db).startswith(datasource1_in_db.name)
        assert 'id' in datasource1_in_db.__jdict__()

    def test_manuallink(self, datasource1_in_db):
        assert datasource1_in_db.linkname() == 'manual'
        datasource1_in_db.manuallink = ''
        assert not datasource1_in_db.linkname()

    def test_comparison(self, db, session, datasource1_in_db):
        datasource = session.get(db.Datasource, 1)
        assert datasource1_in_db == datasource
        assert not datasource1_in_db < datasource
        with pytest.raises(TypeError):
            _ = datasource1_in_db < 2


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


class TestPerson:
    def test_person(self, person):
        assert person
        assert isinstance(person.firstname, str)
        assert isinstance(person.surname, str)
        d = person.__jdict__()
        assert isinstance(d, dict)
        assert 'username' in d


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
        log_1 = session.get(db.Log, 1)
        assert log_1 == log
        assert not log < log


class TestJob:
    def test_job(self, job):
        assert job
        assert job.id == 1
        assert isinstance(job.due, datetime.datetime)
        d = job.__jdict__()
        assert isinstance(d, dict)
        assert 'id' in d

    def test_job_load(self, job, session, db):
        job_1 = session.get(db.Job, 1)
        assert job_1 == job
        assert not job < job
        assert repr(job).startswith("<Job")

    def test_due_time(self, job):
        assert job.due - datetime.timedelta(days=1) > datetime.datetime(2023, 3, 10)

    def test_job_done(self, job, session, db):
        """
        Tests the make_done function of a normal job
        """
        job: db.Job
        job.make_done(by=job._author)
        old_logcount = session.query(db.Log).count()
        session.commit()
        job_1 = session.get(db.Job, 1)
        assert job_1.done
        assert old_logcount == session.query(db.Log).count()

    def test_job_done_repeat(self, job_repeat, session, db):
        """
        Tests the make_done function of a job with repeat function
        """
        old_logcount = session.query(db.Log).count()
        job_repeat.make_done(by=job_repeat._author)
        session.commit()
        job_1 = session.get(db.Job, 1)
        assert job_1.done
        job_2 = session.get(db.Job, 2)
        assert not job_2.done
        assert job_2.due == job_1.due + datetime.timedelta(days=3)
        assert old_logcount == session.query(db.Log).count()

    def test_job_done_log_no_msg(self, job, site1_in_db, session, db):
        """
        Tests the make_done function for a job with log on done behaviour
        """

        job.log = {'message': None, 'sites': [1]}
        session.commit()
        job.make_done(by=job._author)
        log = session.scalars(db.sql.select(db.Log).where(db.Log.site == site1_in_db)).all()
        assert len(log) == 1
        assert log[0].type == job.type
        assert log[0].message == job.name

    def test_job_done_log_msg(self, job, site1_in_db, session, db):
        """
        Tests the make_done function for a job with log on done behaviour
        """
        job.log = {'message': 'Hallo Welt', 'sites': [1]}
        session.commit()
        job.make_done(by=job._author)
        log = session.scalars(db.sql.select(db.Log).where(db.Log.site == site1_in_db)).all()
        assert log[0].message == 'Hallo Welt'

    def test_job_done_log_no_site(self, job, session, db):
        """
        Tests that no logs are written when 'sites' is empty in job.log
        """
        job.log = {'message': '', 'sites': None}
        session.commit()
        old_logcount = session.query(db.Log).count()
        job.make_done(by=job._author)
        assert session.query(db.Log).count() == old_logcount


class TestProject:
    def test_project(self, project):
        assert project
        assert project.id == 1
        d = project.__jdict__()
        assert isinstance(d, dict)
        assert 'id' in d

    def test_project_load(self, project, session, db):
        project_1 = session.get(db.Project, 1)
        assert project_1 == project

    def test_project_add_member(self, project, person):
        project.add_member(person, 2)
        members = list(project.members())
        assert len(members) >= 1  # , f'Added 1 one member to project, but project has {len(members)} member'
        assert members[0][1] == 2  # , f'Project member has unexpected access level of {members[0].access_level}!=1'

        members2 = list(project.members(4))  # should contain the project owner
        assert len(
            members2) == 1, f'Added one member with al=2 to project, but project has {len(members2)} members above level 3'

    def test_person_add_project(self, project, person):
        person.add_project(project, 1)
        projects = list(person.projects())
        print(projects)
        assert len(projects) >= 1, f'Added 1 one member to project, but project has {len(projects)} member'
        assert projects[0][1] == 1, f'Project member has unexpected access level of {projects[0][1]}!=1'


class TestImage:
    def test_image(self, image):
        assert image
        assert image.image64()
        assert len(image.image) > 0
        assert len(image.thumbnail) > 0
