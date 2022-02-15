
import pytest


@pytest.fixture()
def conf():
    from odmf.config import Configuration
    conf = Configuration()
    conf.database_url = 'sqlite://'
    return conf


def test_config_dburl(conf):
    assert conf.database_url.startswith('sqlite://')


@pytest.fixture()
def empty_db(conf):
    from odmf import config
    config.conf = conf
    from odmf import db
    return db


def test_dburl_connection(empty_db):

    with empty_db.engine.connect():
        assert 'sqlite://' in str(empty_db.engine.url)


def test_metamodel(empty_db):
    """
    Create the metamodel and check for all created tables
    """
    empty_db.Base.metadata.create_all(empty_db.engine)
    # Get all tables from all the ORM classes in the module odmf.db
    tables = [getattr(cl, '__tablename__') for n, cl in vars(db).items() if hasattr(cl, '__tablename__')]
    with empty_db.engine.connect() as con:
        for table_name in tables:
            cur = con.execute(f'''SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';''')
            assert len(list(cur)) == 1, f'Did not find table "{table_name}" in database'


@pytest.fixture()
def db(empty_db):
    """
    Creates the db schema, a database user 'odmf.admin'
    and the standard quality levels
    """
    from odmf.tools import create_db as cdb
    # Create schema
    cdb.create_all_tables()
    # Add 'odmf.admin' to table person
    cdb.add_admin('test')
    # Add standard quality levels
    cdb.add_quality_data(cdb.quality_data)
    return empty_db


@pytest.fixture()
def session(db):
    with db.session_scope() as session:
        yield session


def test_base_db(db, session):
    admin = session.query(db.Person).first()
    assert admin.username == 'odmf.admin'
    qualities = session.query(db.Quality).all()
    assert len(qualities) >= 4
