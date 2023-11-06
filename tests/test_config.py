import pytest
from pathlib import Path

from . import conf

def test_conf_create(conf):
    assert conf.database_url == 'sqlite://'
    import odmf
    assert conf.version == odmf.__version__


def test_conf_write(conf, tmp_path):
    with (tmp_path / 'config.yml').open('w') as out:
        conf.to_yaml(out)

    from odmf import config
    new_conf_dict = config.load_config(tmp_path).to_dict()
    conf_dict = conf.to_dict()
    assert all(new_conf_dict[n] == conf_dict[n] for n in conf_dict)


def test_static_double_entry(conf, tmp_path):
    """
    A config should not have duplicate entries in its static directories
    """
    from odmf import config
    statics = config.static_locations(tmp_path, tmp_path.absolute())
    assert len(statics) == 2


def test_abspath(conf, tmp_path):
    import odmf
    import pathlib
    save_path = pathlib.Path(odmf.prefix + '/ressource.txt')
    save_path.write_text('some content')
    abspath = conf.abspath('ressource.txt')
    assert abspath == save_path


def test_abspath_fail(conf):
    with pytest.raises(FileNotFoundError):
        _ = conf.abspath('xyz.txt')


def test_update(conf):
    conf.update(conf.to_dict())
    conf.update({'xyz': 17})
    assert 'xyz' not in conf.to_dict()


def test_google_maps_api(conf):
    assert conf.google_maps_api('js-function')

