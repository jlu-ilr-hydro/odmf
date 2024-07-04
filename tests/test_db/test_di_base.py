import pytest
import configparser

from .. import conf
from . import db, session
from .db_fixtures import project, person
# Create a config file for the Odyssey Logger
@pytest.fixture()
def di_conf_file(tmp_path):

    config = configparser.ConfigParser(interpolation=None)
    config['Tipping Bucket (rain intensity)'] = {
        'instrument': '5',
        'skiplines': '9',
        'delimiter': ',',
        'decimalpoint': '.',
        'dateformat': '%d/%m/%Y %H:%M:%S',
        'datecolumns': '1, 2',
        'project': '1'
    }

    config['rain tips'] = {'column': '4',
                           'name': 'rain tips',
                           'valuetype': '15',
                           'factor': '0.2',
                           'difference': True,
                           'minvalue': '0.001',
                           'maxvalue': '10000'}
    config_path = tmp_path / "sample_logger_Odyssey.conf"
    with config_path.open('w') as config_file:
        config.write(config_file)

    return config_path


def test_from_file(di_conf_file, db, session, project):
    from odmf.dataimport import base
    pattern = '*.conf'
    descr = base.ImportDescription.from_file(path=di_conf_file, pattern=pattern)
    assert descr
    assert descr.filename == str(di_conf_file)
    assert descr.datecolumns == (1, 2)
    assert descr.columns[0].name == 'rain tips'


def test_from_file_validation(db):
    from odmf.dataimport import base
    path = "datafiles/not_exist"
    pattern = "*.conf"
    with pytest.raises(IOError) as e_info:
        base.ImportDescription.from_file(path=path, pattern=pattern)
        assert str(e_info.value) == 'Could not find .conf file for file description'
