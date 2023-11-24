import pytest

@pytest.fixture(autouse=True)
@pytest.mark.parametrize
def conf(tmp_path_factory):
    """
    Creates a configuration with a :memory: SQLite database
    """
    prefix = tmp_path_factory.mktemp('home')
    datafiles = prefix / 'datafiles'
    datafiles.mkdir(exist_ok=True, parents=True)
    import odmf
    odmf.prefix = str(prefix)
    import odmf.config
    conf = odmf.config.Configuration(
        static=[str(prefix)],
        description = '******** TEST *********',
        root_url='/test',
        database_url='sqlite://',
        utm_zone='32N',
        datafiles=str(datafiles)
    )
    with (prefix / 'config.yml').open('w') as f:
        conf.to_yaml(f)
    odmf.config.conf = conf
    return conf
