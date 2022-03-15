import pytest
import configparser
import os.path as op
import os
from glob import glob
from odmf.dataimport import base
from odmf.config import conf


# Create a config file for the Odyssey Logger
def create_conf_file():

    config = configparser.ConfigParser(interpolation=None)
    config['Tipping Bucket (rain intensity)'] = {'instrument': '5',
                                                 'skiplines': '9',
                                                 'delimiter': ',',
                                                 'decimalpoint': '.',
                                                 'dateformat': '%d/%m/%Y %H:%M:%S',
                                                 'datecolumns': '1, 2'}

    config['rain tips'] = {'column': '4',
                           'name': 'rain tips',
                           'valuetype': '15',
                           'factor': '0.2',
                           'difference': True,
                           'minvalue': '0.001',
                           'maxvalue': '10000'}

    with open(r"sample_logger_Odyssey.conf", 'w') as config_file:
        config.write(config_file)
        config_file.flush()
        config_file.close()

    return config_file


# Create the sample config file
create_conf_file()

def test_from_file():
    path = os.getcwd()
    pattern = '*.conf'
    descr, config = base.ImportDescription.from_file(path=path, pattern=pattern)
    assert descr
    assert descr.filename == glob(op.join(path, pattern))[0]
    assert type(config.sections()) == list
    assert len(list(config['Tipping Bucket (rain intensity)'])) == 6
    assert float(config.get('Tipping Bucket (rain intensity)', 'skiplines')) == 9


def test_from_file_validation():
    path="datafiles/not_exist"
    pattern="*.conf"
    with pytest.raises(Exception) as e_info:
        base.ImportDescription.from_file(path=path, pattern=pattern)
        raise Exception(e_info.value)
    assert str(e_info.value) == 'Could not find .conf file for file description'
