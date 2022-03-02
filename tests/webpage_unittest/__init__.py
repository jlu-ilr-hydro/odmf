import pytest

@pytest.fixture(scope='package', autouse=True)
def conf(tmp_path_factory):
    """
    Creates a configuration with a :memory: SQLite database
    """
    import odmf
    prefix = tmp_path_factory.mktemp('home')
    odmf.prefix = str(prefix)
    from odmf import config
    conf = config.Configuration()
    conf.description = '******** TEST *********'
    conf.database_url = 'sqlite://'
    conf.utm_zone = '32N'
    with (prefix / 'config.yml').open('w') as f:
        conf.to_yaml(f)
    config.conf = conf
    return conf


@pytest.fixture(scope='package')
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
