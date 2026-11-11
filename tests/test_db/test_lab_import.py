from datetime import datetime
from contextlib import nullcontext
from types import SimpleNamespace

import pandas as pd
import pytest
import yaml

from odmf.dataimport import lab_import
from . import conf, db, session
from .db_fixtures import datasource1_in_db, site1_in_db


def make_lab_dataset(db, dataset_id, start, end):
    return db.Timeseries(
        id=dataset_id,
        name=f'lab dataset {dataset_id}',
        filename=f'lab-dataset-{dataset_id}.csv',
        start=start,
        end=end,
        _site=1,
        _valuetype=3,
        _source=1,
        _quality=None,
        level=1.5,
    )


@pytest.fixture
def lab_dataset_factory(db, session, site1_in_db, datasource1_in_db):
    value_type = db.ValueType(id=3, name='value', unit='unit')
    session.add(value_type)
    session.commit()
    datasets = []

    def create_dataset(dataset_id, start, end):
        dataset = make_lab_dataset(db, dataset_id, start, end)
        session.add(dataset)
        session.commit()
        datasets.append(dataset)
        return dataset

    yield create_dataset

    for dataset in datasets:
        session.delete(dataset)
    session.delete(value_type)
    session.commit()


@pytest.fixture
def lab_dataset(lab_dataset_factory):
    return lab_dataset_factory(17, datetime(2020, 1, 1), datetime(2020, 1, 2))


def test_labimport_applies_value_factors(tmp_path, monkeypatch):
    input_file = tmp_path / 'measurements.csv'
    input_file.write_text('nitrate,ammonium\n1.5,3\n')
    config_file = tmp_path / 'measurements.labimport'
    config = {
        'driver': 'read_csv',
        'columns': {
            'nitrate': {'type': 'value', 'factor': 2, 'valuetype': 3},
            'ammonium': {'type': 'value', 'factor': 10, 'valuetype': 4},
            'missing_a': {'type': 'value', 'factor': 1, 'valuetype': 5},
            'missing_b': {'type': 'value', 'factor': 1, 'valuetype': 6},
        },
    }
    with config_file.open('w') as file:
        yaml.safe_dump(config, file)

    filename = SimpleNamespace(
        absolute=str(input_file),
        glob_up=lambda pattern: config_file,
    )
    monkeypatch.setattr(
        lab_import,
        'find_datasets',
        lambda melted: (pd.Series([7, 7], index=melted.index, dtype='Int64'), []),
    )
    imported = {}

    def capture_records(dataframe):
        imported['dataframe'] = dataframe.copy()
        return [7], len(dataframe)

    monkeypatch.setattr(lab_import, 'addrecords_dataframe', capture_records)

    _, _, errors, _ = lab_import.labimport(filename, dryrun=False)

    assert sorted(imported['dataframe']['value'].tolist()) == [3.0, 30.0]
    assert set(errors) == {'missing_a', 'missing_b'}


def test_labimport_skips_and_reports_unparseable_samples(tmp_path, monkeypatch):
    input_file = tmp_path / 'samples.csv'
    input_file.write_text('sample,nitrate\nA_20240101,1\nbad-sample,2\nA_20240102,3\n')
    config_file = tmp_path / 'samples.labimport'
    config = {
        'driver': 'read_csv',
        'columns': {
            'sample': {
                'type': 'sample',
                'pattern': r'([A-Z]+)_(\d{8})',
                'site': {'group': 1, 'map': {'A': 1}},
                'time': {'group': 2, 'format': '%Y%m%d'},
            },
            'nitrate': {'type': 'value', 'factor': 1, 'valuetype': 3},
        },
    }
    with config_file.open('w') as file:
        yaml.safe_dump(config, file)

    filename = SimpleNamespace(
        absolute=str(input_file),
        glob_up=lambda pattern: config_file,
    )
    monkeypatch.setattr(
        lab_import,
        'find_datasets',
        lambda melted: (pd.Series([7] * len(melted), index=melted.index, dtype='Int64'), []),
    )
    imported = {}

    def capture_records(dataframe):
        imported['dataframe'] = dataframe.copy()
        return [7], len(dataframe)

    monkeypatch.setattr(lab_import, 'addrecords_dataframe', capture_records)

    _, _, errors, _ = lab_import.labimport(filename, dryrun=False)

    assert imported['dataframe']['value'].tolist() == [1.0, 3.0]
    assert len(errors) == 1
    assert errors[0]['row'] == 1
    assert errors[0]['sample'] == 'bad-sample'
    assert 'pattern' in errors[0]['error']


def test_labimport_reports_unknown_dataset_and_writes_only_valid_rows(tmp_path, monkeypatch):
    input_file = tmp_path / 'datasets.csv'
    input_file.write_text('dataset,nitrate\n99,1\n7,2\n')
    config_file = tmp_path / 'datasets.labimport'
    config = {
        'driver': 'read_csv',
        'columns': {
            'dataset': {'type': 'dataset'},
            'nitrate': {'type': 'value', 'factor': 3, 'valuetype': 3},
        },
    }
    with config_file.open('w') as file:
        yaml.safe_dump(config, file)

    filename = SimpleNamespace(
        absolute=str(input_file),
        glob_up=lambda pattern: config_file,
    )
    session = SimpleNamespace(
        get=lambda model, dataset_id: SimpleNamespace(id=dataset_id) if dataset_id == 7 else None
    )
    monkeypatch.setattr(lab_import.db, 'session_scope', lambda: nullcontext(session))
    writes = []

    def capture_records(dataframe):
        writes.append(dataframe.copy())
        return [7], len(dataframe)

    monkeypatch.setattr(lab_import, 'addrecords_dataframe', capture_records)

    _, _, dryrun_errors, _ = lab_import.labimport(filename, dryrun=True)
    assert writes == []

    _, _, import_errors, _ = lab_import.labimport(filename, dryrun=False)

    assert dryrun_errors == import_errors
    assert len(import_errors) == 1
    assert import_errors[0]['row'] == 0
    assert 'Dataset 99 not found' in import_errors[0]['error']
    assert len(writes) == 1
    assert writes[0]['dataset'].tolist() == [7]
    assert writes[0]['value'].tolist() == [6.0]


def test_labimport_aggregates_repeated_samples_and_reports_counts(tmp_path, monkeypatch):
    input_file = tmp_path / 'repeated-samples.csv'
    input_file.write_text('sample,nitrate\nA_20240101,1\nA_20240101,3\n')
    config_file = tmp_path / 'repeated-samples.labimport'
    config = {
        'driver': 'read_csv',
        'aggregate': 'mean',
        'columns': {
            'sample': {
                'type': 'sample',
                'pattern': r'([A-Z]+)_(\d{8})',
                'site': {'group': 1, 'map': {'A': 1}},
                'time': {'group': 2, 'format': '%Y%m%d'},
            },
            'nitrate': {'type': 'value', 'factor': 1, 'valuetype': 3},
        },
    }
    with config_file.open('w') as file:
        yaml.safe_dump(config, file)

    filename = SimpleNamespace(
        absolute=str(input_file),
        glob_up=lambda pattern: config_file,
    )
    monkeypatch.setattr(
        lab_import,
        'find_datasets',
        lambda melted: (pd.Series([7] * len(melted), index=melted.index, dtype='Int64'), []),
    )
    imported = {}

    def capture_records(dataframe):
        imported['dataframe'] = dataframe.copy()
        return [7], len(dataframe)

    monkeypatch.setattr(lab_import, 'addrecords_dataframe', capture_records)

    datasets, info, errors, _ = lab_import.labimport(filename, dryrun=False)

    assert imported['dataframe']['value'].tolist() == [2.0]
    assert datasets == {7: 1}
    assert info == {'measured': 2, 'aggregated': 1, 'imported': 1}
    assert errors == []


def test_check_columns_returns_available_and_all_missing_columns():
    table = pd.DataFrame({'present': [1]})
    config = {
        'present': {'type': 'value'},
        'missing_a': {'type': 'value'},
        'missing_b': {'type': 'sample'},
    }

    available, missing = lab_import.check_columns(table, config)

    assert available == {'present': {'type': 'value'}}
    assert missing == ['missing_a', 'missing_b']


def test_rename_column_by_type_renames_configured_column():
    table = pd.DataFrame({'Sample time': [datetime(2024, 1, 1)]})
    labcolumns = {'Sample time': {'type': 'time'}}

    lab_import.rename_column_by_type(table, labcolumns, 'time')

    assert 'time' in table.columns
    assert 'Sample time' not in table.columns


def test_melt_table_maps_value_columns_to_value_types():
    table = pd.DataFrame({
        'dataset': [17],
        'time': [datetime(2024, 1, 1)],
        'sample': ['sample-1'],
        'nitrate': [1.5],
        'ammonium': [3.0],
    })
    labcolumns = {
        'nitrate': {'type': 'value', 'valuetype': 3},
        'ammonium': {'type': 'value', 'valuetype': 4},
    }

    melted = lab_import.melt_table(table, labcolumns)

    assert list(zip(melted['valuetype'], melted['value'])) == [(3, 1.5), (4, 3.0)]
    assert melted['dataset'].tolist() == [17, 17]
    assert melted['sample'].tolist() == ['sample-1', 'sample-1']


def test_clean_df_melt_keeps_record_columns():
    table = pd.DataFrame({
        'dataset': [17],
        'time': [datetime(2024, 1, 1)],
        'value': [1.5],
        'sample': ['sample-1'],
        'site': [1],
        'valuetype': [3],
    })

    cleaned = lab_import.clean_df_melt(table)

    assert list(cleaned.columns) == ['dataset', 'time', 'value', 'sample']
    assert cleaned.iloc[0].to_dict() == {
        'dataset': 17,
        'time': datetime(2024, 1, 1),
        'value': 1.5,
        'sample': 'sample-1',
    }


def test_find_dataset_returns_explicit_dataset_id(session, lab_dataset):
    result = lab_import.find_dataset(session, dataset=lab_dataset.id)

    assert result.id == lab_dataset.id


def test_find_dataset_returns_unique_metadata_match(session, lab_dataset):
    result = lab_import.find_dataset(
        session,
        time=datetime(2020, 1, 1, 12),
        site=1,
        level=1.5,
        valuetype=3,
        instrument=1,
    )

    assert result.id == lab_dataset.id


def test_find_dataset_uses_most_recent_earlier_match(session, lab_dataset_factory, lab_dataset):
    recent_dataset = lab_dataset_factory(
        18, datetime(2020, 1, 4), datetime(2020, 1, 5)
    )
    session.add(recent_dataset)
    session.commit()

    result = lab_import.find_dataset(
        session,
        time=datetime(2020, 1, 7),
        site=1,
        level=1.5,
        valuetype=3,
        instrument=1,
    )

    assert result.id == recent_dataset.id


def test_find_dataset_reports_missing_match(session, lab_dataset):
    with pytest.raises(ValueError, match='No dataset found'):
        lab_import.find_dataset(
            session,
            time=datetime(2020, 1, 7),
            site=99,
            level=1.5,
            valuetype=3,
            instrument=1,
        )


def test_find_dataset_reports_ambiguous_match(session, lab_dataset_factory, lab_dataset):
    lab_dataset_factory(18, datetime(2020, 1, 1), datetime(2020, 1, 3))

    with pytest.raises(ValueError, match='not unique at given date'):
        lab_import.find_dataset(
            session,
            time=datetime(2020, 1, 2),
            site=1,
            level=1.5,
            valuetype=3,
            instrument=1,
        )


def test_find_datasets_returns_row_errors_and_resolved_ids(lab_dataset):
    melted = pd.DataFrame(
        {'dataset': [999, lab_dataset.id]},
        index=['missing', 'present'],
    )

    datasets, errors = lab_import.find_datasets(melted)

    assert pd.isna(datasets.loc['missing'])
    assert datasets.loc['present'] == lab_dataset.id
    assert len(errors) == 1
    assert errors[0]['row'] == 'missing'
    assert 'Dataset 999 not found' in errors[0]['error']