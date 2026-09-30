import pytest
import configparser
from types import SimpleNamespace

from .. import conf
from . import db, session
from .db_fixtures import project, person, datasource1_in_db
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


def test_from_file_reads_append_and_dataset_column_metadata(tmp_path, db):
    from odmf.dataimport import base

    config = configparser.ConfigParser(interpolation=None)
    config['Field instrument'] = {
        'instrument': '1',
        'datecolumns': '0, 1',
        'samplecolumn': '5',
        'sample_mapping': "{'A': 10}",
        'nodata': "['-999']",
    }
    config['Appended value'] = {
        'column': '2',
        'valuetype': '15',
        'factor': '0.1',
        'append': '42',
    }
    config['Routed value'] = {
        'column': '3',
        'valuetype': '16',
        'factor': '1.0',
        'ds_column': '4',
    }
    config_path = tmp_path / 'field_instrument.conf'
    with config_path.open('w') as config_file:
        config.write(config_file)

    description = base.ImportDescription.from_file(config_path)

    assert description.datecolumns == (0, 1)
    assert description.samplecolumn == 5
    assert description.sample_mapping == {'A': 10}
    assert description.nodata == ['-999']
    assert description.columns[0].append == 42
    assert description.columns[1].ds_column == 4
    assert description.get_column_names() == (
        [0, 1, 2, 3, 4, 5],
        ['date', 'time', 'Appended value', 'Routed value', 'dataset for Routed value', 'sample'],
    )


def test_import_column_config_roundtrip():
    from odmf.dataimport.base import ImportColumn

    source = ImportColumn(
        column=4,
        name='water level',
        valuetype=15,
        factor=0.25,
        comment='manual observation',
        difference=True,
        minvalue=-2,
        maxvalue=12,
        append=42,
        level=1.5,
        access=0,
        ds_column=6,
    )
    config = configparser.RawConfigParser(allow_no_value=True)
    config.add_section(source.name)

    source.to_config(config, source.name)
    parsed = ImportColumn.from_config(config, source.name)

    assert parsed.column == 4
    assert parsed.name == 'water level'
    assert parsed.valuetype == 15
    assert parsed.factor == 0.25
    assert parsed.comment == 'manual observation'
    assert parsed.difference == 'True'
    assert parsed.minvalue == -2
    assert parsed.maxvalue == 12
    assert parsed.append == 42
    assert parsed.level == 1.5
    assert parsed.access == 0
    assert parsed.ds_column == 6
    assert str(parsed) == 'd[water level]:column=4'


def test_import_column_from_dataset_copies_dataset_metadata():
    from odmf.dataimport.base import ImportColumn

    dataset = SimpleNamespace(
        id=42,
        name='water level',
        valuetype=SimpleNamespace(id=15, minvalue=-2, maxvalue=12),
        comment='dataset comment',
        level=1.5,
        access=0,
    )

    column = ImportColumn.from_dataset(dataset, column=4)

    assert column.column == 4
    assert column.name == 'water level'
    assert column.valuetype == 15
    assert column.minvalue == -2
    assert column.maxvalue == 12
    assert column.comment == 'dataset comment'
    assert column.append == 42
    assert column.level == 1.5
    assert column.access == 0


def test_import_description_normalizes_delimiter_and_builds_column_names():
    from odmf.dataimport.base import ImportDescription, ImportColumn

    description = ImportDescription(
        instrument='5', delimiter='TAB', datecolumns=0, samplecolumn=5, nodata=[]
    )
    description.addcolumn(2, 'water level', 15)
    description.columns.append(ImportColumn(
        column=3, name='temperature', valuetype=16, ds_column=4
    ))

    assert description.instrument == 5
    assert description.delimiter == '\t'
    assert description.datecolumns == (0,)
    assert description.get_column_names() == (
        [0, 2, 3, 4, 5],
        ['date', 'water level', 'temperature', 'dataset for temperature', 'sample'],
    )
    assert description.columns[0].factor == 1.0

    space_delimited = ImportDescription(instrument=5, delimiter='SPACE', nodata=[])
    assert space_delimited.delimiter is None


def test_import_description_rejects_non_list_nodata():
    from odmf.dataimport.base import ImportDescription

    with pytest.raises(ValueError, match='has to be an instance of a list'):
        ImportDescription(instrument=5, nodata='NA')


def test_import_description_from_config_uses_defaults(db):
    from odmf.dataimport.base import ImportDescription

    config = configparser.RawConfigParser(interpolation=None)
    config['Field instrument'] = {'instrument': '5'}
    config['water level'] = {
        'column': '2',
        'valuetype': '15',
        'factor': '1.0',
    }

    description = ImportDescription.from_config(config)

    assert description.instrument == 5
    assert description.skiplines == 0
    assert description.skipfooter == 0
    assert description.datecolumns == ()
    assert description.nodata == []
    assert description.sample_mapping == {}
    assert description.columns[0].name == 'water level'
    assert description.columns[0].append is None
    assert description.columns[0].ds_column is None


def test_import_description_from_config_rejects_invalid_project_and_timezone(db):
    from odmf.dataimport.base import ImportDescription

    config = configparser.RawConfigParser(interpolation=None)
    config['Field instrument'] = {
        'instrument': '5',
        'project': '999999',
    }
    with pytest.raises(ValueError, match='no valid project identifier'):
        ImportDescription.from_config(config)

    config['Field instrument']['project'] = ''
    config['Field instrument']['timezone'] = 'Mars/Olympus_Mons'
    with pytest.raises(ValueError, match='no valid timezone'):
        ImportDescription.from_config(config)


def test_import_description_to_config_and_markdown_roundtrip(
    db, session, project, datasource1_in_db
):
    from io import StringIO
    from odmf.dataimport.base import ImportDescription, ImportColumn

    description = ImportDescription(
        instrument=datasource1_in_db.id,
        skiplines=3,
        skipfooter=1,
        delimiter='TAB',
        decimalpoint=',',
        dateformat='%d/%m/%Y %H:%M:%S',
        datecolumns=(0, 1),
        timezone='Europe/Berlin',
        project=project.id,
        nodata=['NA', '-999'],
        worksheet=2,
        samplecolumn=5,
        sample_mapping={'A': 1},
        encoding='utf-8',
        total_columns=7,
    )
    description.columns.append(ImportColumn(
        column=2,
        name='water level',
        valuetype=15,
        factor=0.25,
        comment='manual observation',
        difference=True,
        minvalue=-2,
        maxvalue=12,
        level=1.5,
        access=0,
        ds_column=6,
    ))

    config = description.to_config()
    serialized = StringIO()
    config.write(serialized)
    serialized.seek(0)
    disk_config = configparser.RawConfigParser()
    disk_config.read_file(serialized)
    parsed = ImportDescription.from_config(disk_config)
    markdown = description.to_markdown()

    assert parsed.instrument == description.instrument
    assert parsed.skiplines == 3
    assert parsed.skipfooter == 1
    assert parsed.delimiter == '\t'
    assert parsed.decimalpoint == ','
    assert parsed.dateformat == '%d/%m/%Y %H:%M:%S'
    assert parsed.datecolumns == (0, 1)
    assert parsed.timezone == 'Europe/Berlin'
    assert parsed.project == str(project.id)
    assert parsed.nodata == ['NA', '-999']
    assert parsed.worksheet == 2
    assert parsed.sample_mapping == {'A': 1}
    assert parsed.total_columns == 7
    assert parsed.columns[0].ds_column == 6
    assert 'water level' in markdown
    assert 'sample_mapping' in markdown
    assert (parsed.samplecolumn, parsed.encoding) == (5, 'utf-8')


def test_config_getdict_handles_missing_valid_and_invalid_values():
    from odmf.dataimport.base import config_getdict

    config = configparser.RawConfigParser(interpolation=None)
    config['Instrument'] = {'mapping': "{'A': 1}"}
    config['Invalid'] = {'mapping': "{'A': object()}"}

    assert config_getdict(config, 'Instrument', 'mapping') == {'A': 1}
    assert config_getdict(config, 'Instrument', 'missing') == {}
    with pytest.raises(ValueError, match='no valid dict type'):
        config_getdict(config, 'Invalid', 'mapping')


def test_from_config_rejects_empty_configuration():
    from odmf.dataimport.base import ImportDescription

    with pytest.raises(IOError, match='Empty config file'):
        ImportDescription.from_config(configparser.RawConfigParser())
