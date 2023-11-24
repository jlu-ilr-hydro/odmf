import pytest
from contextlib import contextmanager
import cherrypy
from .. import conf


@pytest.fixture()
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
def db_session(db):
    with db.session_scope() as session:
        yield session

@contextmanager
def temp_in_database(obj, db_session):
    """
    Adds the ORM-object obj to the session and commits it to the database.
    After usage the object is deleted from the session and is commited again
    """
    db_session.add(obj)
    db_session.commit()
    yield obj
    db_session.delete(obj)
    db_session.commit()


@pytest.fixture()
def root(db):
    from cherrypy.lib.sessions import RamSession
    cherrypy.session = RamSession()
    cherrypy.request.login = None
    from odmf.webpage.root import Root
    return Root()
