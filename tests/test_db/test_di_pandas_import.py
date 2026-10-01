import pytest
import datetime
import pandas as pd
import numpy as np
import pandas as pd
from sqlalchemy import event
from ..test_db import db, session, conf
from .test_di_base import di_conf_file
from .db_fixtures import project, person, site1_in_db, datasource1_in_db
from odmf import db as orm
from odmf.dataimport import base, pandas_import as pi
from odmf.tools import Path as OdfPath
from types import SimpleNamespace


def make_import_description(valuetype, *, factor=1.0, difference=None,
                            minvalue=-1e6, maxvalue=1e6, append=None,
                            ds_column=None):
    total_columns = 4 if ds_column else None
    description = pi.ImportDescription(
        instrument=1,
        datecolumns=(0, 1),
        dateformat='%d/%m/%Y %H:%M:%S',
        nodata=['NA'],
        total_columns=total_columns,
    )
    description.columns.append(base.ImportColumn(
        column=2,
        name='measurement',
        valuetype=valuetype,
        factor=factor,
        difference=difference,
        minvalue=minvalue,
        maxvalue=maxvalue,
        append=append,
        ds_column=ds_column,
    ))
    return description, description.columns[0]


def write_import_csv(tmp_path, text, name='measurements.csv'):
    filename = tmp_path / name
    filename.write_text(text, encoding='utf-8')
    return OdfPath(str(filename), absolute=True)


@pytest.fixture
def import_value_type(db, session):
    value_type = orm.ValueType(
        id=90, name='test measurement', unit='u', minvalue=0, maxvalue=10
    )
    session.add(value_type)
    session.commit()
    yield value_type
    dataset_ids = [
        dataset_id for dataset_id, in session.query(orm.Dataset.id).filter_by(_valuetype=90)
    ]
    if dataset_ids:
        session.query(orm.Record).filter(
            orm.Record._dataset.in_(dataset_ids)
        ).delete(synchronize_session=False)
        session.query(orm.Dataset).filter_by(_valuetype=90).delete(synchronize_session=False)
    session.delete(value_type)
    session.commit()


@pytest.fixture
def existing_import_timeseries(
    db, session, person, site1_in_db, datasource1_in_db, import_value_type
):
    timeseries = orm.Timeseries(
        id=701,
        name='existing measurement',
        filename='existing.csv',
        start=datetime.datetime(2024, 2, 2),
        end=datetime.datetime(2024, 2, 2),
        site=site1_in_db,
        valuetype=import_value_type,
        measured_by=person,
        quality=session.get(orm.Quality, 0),
        source=datasource1_in_db,
        level=0,
    )
    session.add(timeseries)
    session.add(orm.Record(
        id=4,
        dataset=timeseries,
        time=datetime.datetime(2024, 2, 2, 12),
        value=4,
    ))
    session.commit()
    yield timeseries
    session.query(orm.Record).filter_by(_dataset=timeseries.id).delete()
    session.delete(timeseries)
    session.commit()


@pytest.fixture
def second_import_timeseries(
    db, session, person, site1_in_db, datasource1_in_db, import_value_type
):
    timeseries = orm.Timeseries(
        id=702,
        name='second existing measurement',
        filename='second-existing.csv',
        start=datetime.datetime(2024, 2, 2),
        end=datetime.datetime(2024, 2, 2),
        site=site1_in_db,
        valuetype=import_value_type,
        measured_by=person,
        quality=session.get(orm.Quality, 0),
        source=datasource1_in_db,
        level=0,
    )
    session.add(timeseries)
    session.commit()
    yield timeseries
    session.query(orm.Record).filter_by(_dataset=timeseries.id).delete()
    session.delete(timeseries)
    session.commit()

@pytest.fixture
def csv_file_for_import(tmp_path, di_conf_file):
    # Import sample obtained data of Odyssey logger
    from pathlib import Path
    import shutil
    source_file = Path(__file__).parent / 'RG_050_004.CSV'
    sample_file = tmp_path / 'RG_050_004.CSV'
    shutil.copy(source_file, sample_file)
    assert sample_file.exists()
    # Alternative - create data file with code and save it to tmp_path (2022-03-30)
    return sample_file


def test_load_dataframe(csv_file_for_import, db, project, person):
    from odmf.dataimport import pandas_import as pi
    idescr = pi.ImportDescription.from_file(csv_file_for_import)
    df = pi.load_dataframe(idescr=idescr, filepath=csv_file_for_import)
    assert not df.empty

def test_load_dataframe_xlsx(tmp_path, csv_file_for_import, db, project, person):
    """
    This test converts the test csv file to xlsx and then tries to load it with the same import description. 
    This is to check if the loading of xlsx files is working, and if the import description can be used for both csv and xlsx files without problems. 
    
    As an additional test, it changes a numeric value in a faulty string and see if the string is just ignored (#163).
    """
    import pandas as pd
    from odmf.dataimport import pandas_import as pi
    df_csv = pd.read_csv(csv_file_for_import, decimal='.', delimiter=',', names=range(6), header=None)
    df_csv[4] = df_csv[4].astype(str)  # Change the column to string type to see if it is ignored
    df_csv.iloc[10, 4] = 'faulty_string'  # Change a numeric value to a string to see if it is ignored
    df_csv.to_excel(tmp_path / 'RG_050_004.xlsx', index=False, header=False)
    idescr = pi.ImportDescription.from_file(csv_file_for_import)
    # Now load the xlsx file 
    df_xlsx = pi.load_dataframe(idescr=idescr, filepath=tmp_path / 'RG_050_004.xlsx')
    assert not df_xlsx.empty

def test_load_dataframe_column_problem(csv_file_for_import, db, project, person):
    """
    This test is for issue #103, to see if it is working with total_columns
    https://github.com/jlu-ilr-hydro/odmf/issues/103
    """
    from odmf.dataimport import pandas_import as pi
    idescr = pi.ImportDescription.from_file(csv_file_for_import)
    # Skip another line to create situation in #103
    idescr.skiplines += 1
    # See #103 happening
    with pytest.raises(pi.DataImportError):
        df = pi.load_dataframe(idescr=idescr, filepath=csv_file_for_import)
    # Solve #103 by giving the total line number
    idescr.total_columns = 6
    df = pi.load_dataframe(idescr=idescr, filepath=csv_file_for_import)
    assert not df.empty


def test_aware_times_are_converted_to_dataset_local_wall_time():
    from odmf.dataimport.pandas_import import _naive_local_times

    times = pd.Series(pd.to_datetime(['2021-05-10T12:00:00+00:00']))

    result = _naive_local_times(times, 'Europe/Berlin')

    assert result.iloc[0] == datetime.datetime(2021, 5, 10, 14)
    assert result.dt.tz is None


def test_load_dataframe_applies_difference_factor_and_nodata(tmp_path):
    description, column = make_import_description(
        90, factor=2, difference=True, minvalue=0, maxvalue=10
    )
    filename = write_import_csv(
        tmp_path,
        '01/02/2024,12:00:00,10\n'
        '01/02/2024,13:00:00,13\n'
        '01/02/2024,14:00:00,NA\n',
    )

    frame = pi.load_dataframe(description, filename)

    assert frame['time'].tolist() == [
        pd.Timestamp(2024, 2, 1, 12),
        pd.Timestamp(2024, 2, 1, 13),
        pd.Timestamp(2024, 2, 1, 14),
    ]
    assert pd.isna(frame.loc[0, column.name])
    assert frame.loc[1, column.name] == 6
    assert pd.isna(frame.loc[2, column.name])


def test_get_statistics_reports_out_of_range_values(tmp_path):
    description, _ = make_import_description(90, minvalue=0, maxvalue=10)
    filename = write_import_csv(
        tmp_path,
        '01/02/2024,12:00:00,5\n01/02/2024,13:00:00,11\n',
    )
    frame = pi.load_dataframe(description, filename)

    stats, start, end = pi.get_statistics(description, frame)

    assert stats['measurement']['n'] == 2
    assert stats['measurement']['n_out_of_range'] == 1
    assert stats['measurement']['min'] == 5
    assert stats['measurement']['max'] == 11
    assert start == pd.Timestamp(2024, 2, 1, 12)
    assert end == pd.Timestamp(2024, 2, 1, 13)


def test_submit_creates_dataset_and_skips_out_of_range_values(
    tmp_path, db, session, person, site1_in_db, datasource1_in_db, import_value_type
):
    description, _ = make_import_description(
        import_value_type.id, factor=2, minvalue=0, maxvalue=10
    )
    filename = write_import_csv(
        tmp_path,
        '01/02/2024,12:00:00,3\n01/02/2024,13:00:00,6\n',
    )

    messages = pi.submit(session, description, filename, person.username, site1_in_db.id)

    dataset = session.query(orm.Timeseries).filter_by(name='measurement').one()
    records = dataset.records.order_by(orm.Record.id).all()
    assert len(messages) == 1
    assert [record.value for record in records] == [6]
    assert dataset.measured_by.username == person.username
    assert dataset.site.id == site1_in_db.id
    assert dataset.source.id == datasource1_in_db.id
    assert dataset.start == datetime.datetime(2024, 2, 1, 12)
    assert dataset.end == datetime.datetime(2024, 2, 1, 13)


def test_submit_appends_records_and_extends_existing_dataset(
    tmp_path, session, person, site1_in_db, existing_import_timeseries, import_value_type
):
    description, column = make_import_description(
        import_value_type.id, append=existing_import_timeseries.id
    )
    filename = write_import_csv(
        tmp_path,
        '01/02/2024,12:00:00,5\n'
        '03/02/2024,12:00:00,6\n',
    )

    pi.submit(session, description, filename, person.username, site1_in_db.id)

    session.refresh(existing_import_timeseries)
    records = existing_import_timeseries.records.order_by(orm.Record.id).all()
    assert [record.id for record in records] == [4, 5, 6]
    assert existing_import_timeseries.start == datetime.datetime(2024, 2, 1, 12)
    assert existing_import_timeseries.end == datetime.datetime(2024, 2, 3, 12)


def test_get_dataframe_for_ds_column_routes_rows_and_assigns_next_ids(
    db, session, existing_import_timeseries, import_value_type
):
    column = base.ImportColumn(
        column=2, name='measurement', valuetype=import_value_type.id, ds_column=3
    )
    frame = pd.DataFrame({
        'time': pd.to_datetime(['2024-02-03 12:00', '2024-02-04 12:00']),
        'date': pd.to_datetime(['2024-02-03', '2024-02-04']),
        'measurement': [5, 6],
        'dataset for measurement': [existing_import_timeseries.id] * 2,
    })

    records = pi.get_dataframe_for_ds_column(session, column, frame)

    assert records['dataset'].tolist() == [existing_import_timeseries.id] * 2
    assert records['id'].tolist() == [5, 6]
    assert records['value'].tolist() == [5, 6]


def test_get_dataframe_for_ds_column_batches_numpy_ids_in_one_query(
    session, existing_import_timeseries, second_import_timeseries, import_value_type
):
    column = base.ImportColumn(
        column=2, name='measurement', valuetype=import_value_type.id, ds_column=3
    )
    frame = pd.DataFrame({
        'time': pd.to_datetime([
            '2024-02-03 12:00', '2024-02-04 12:00', '2024-02-05 12:00',
        ]),
        'measurement': [5, 6, 7],
        'dataset for measurement': np.array(
            [existing_import_timeseries.id, second_import_timeseries.id,
             existing_import_timeseries.id],
            dtype=np.int64,
        ),
    })
    statements = []
    parameters_seen = []

    def capture_query(_connection, _cursor, statement, parameters, _context, _many):
        if statement.lstrip().upper().startswith('SELECT'):
            statements.append(statement)
            parameters_seen.extend(parameters)

    engine = session.get_bind()
    event.listen(engine, 'before_cursor_execute', capture_query)
    try:
        records = pi.get_dataframe_for_ds_column(session, column, frame)
    finally:
        event.remove(engine, 'before_cursor_execute', capture_query)

    assert records['dataset'].tolist() == [701, 702, 701]
    assert records['id'].tolist() == [5, 1, 6]
    assert len(statements) == 1
    assert all(
        type(parameter) is int
        for parameter in parameters_seen
        if isinstance(parameter, (int, np.integer))
    )


def test_submit_routes_ds_column_records_to_existing_dataset(
    tmp_path, session, person, site1_in_db, existing_import_timeseries, import_value_type
):
    description, _ = make_import_description(
        import_value_type.id, ds_column=3
    )
    filename = write_import_csv(
        tmp_path,
        f'01/02/2024,12:00:00,5,{existing_import_timeseries.id}\n'
        f'03/02/2024,12:00:00,6,{existing_import_timeseries.id}\n',
    )

    pi.submit(session, description, filename, person.username, site1_in_db.id)

    records = existing_import_timeseries.records.order_by(orm.Record.id).all()
    assert [record.id for record in records] == [4, 5, 6]
    assert [record.value for record in records] == [4, 5, 6]


def test_get_dataframe_for_ds_column_rejects_missing_datasets(
    session, import_value_type
):
    column = base.ImportColumn(
        column=2, name='measurement', valuetype=import_value_type.id, ds_column=3
    )
    frame = pd.DataFrame({
        'time': pd.to_datetime(['2024-02-03 12:00']),
        'measurement': [5],
        'dataset for measurement': [99999],
    })

    with pytest.raises(pi.DataImportError, match='misses the following datasets'):
        pi.get_dataframe_for_ds_column(session, column, frame)


def test_validate_ds_column_targets_accepts_existing_timeseries(
    session, existing_import_timeseries, import_value_type
):
    description, _ = make_import_description(import_value_type.id, ds_column=3)
    frame = pd.DataFrame({
        'dataset for measurement': [existing_import_timeseries.id] * 3,
    })

    assert pi.validate_ds_column_targets(session, description, frame) is None


def test_validate_ds_column_targets_reports_missing_ids_with_one_query(
    session, existing_import_timeseries, import_value_type
):
    description, _ = make_import_description(import_value_type.id, ds_column=3)
    description.columns.append(base.ImportColumn(
        column=4,
        name='second measurement',
        valuetype=import_value_type.id,
        ds_column=5,
    ))
    frame = pd.DataFrame({
        'dataset for measurement': [existing_import_timeseries.id, 99999],
        'dataset for second measurement': [99999, existing_import_timeseries.id],
    })
    statements = []

    def count_selects(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith('SELECT'):
            statements.append(statement)

    engine = session.get_bind()
    event.listen(engine, 'before_cursor_execute', count_selects)
    try:
        with pytest.raises(pi.DataImportError) as error:
            pi.validate_ds_column_targets(session, description, frame)
    finally:
        event.remove(engine, 'before_cursor_execute', count_selects)

    assert 'measurement misses the following datasets [99999]' in str(error.value)
    assert 'second measurement misses the following datasets [99999]' in str(error.value)
    assert len(statements) == 1


def test_submit_rejects_missing_ds_column_target_before_creating_datasets(
    tmp_path, session, person, site1_in_db, import_value_type
):
    description, _ = make_import_description(import_value_type.id, ds_column=3)
    filename = write_import_csv(tmp_path, '01/02/2024,12:00:00,5,99999\n')

    with pytest.raises(pi.DataImportError, match='misses the following datasets'):
        pi.submit(session, description, filename, person.username, site1_in_db.id)

    assert session.query(orm.Timeseries).filter_by(name='measurement').count() == 0


def test_preview_reports_missing_ds_column_target(
    tmp_path, monkeypatch, db, existing_import_timeseries, import_value_type
):
    from odmf.webpage.filemanager import dbimport as dbimport_page

    description, _ = make_import_description(import_value_type.id, ds_column=3)
    filename = tmp_path / 'preview.csv'
    filename.write_text('preview content')
    frame = pd.DataFrame({
        'time': pd.to_datetime(['2024-02-03 12:00']),
        'measurement': [5],
        'dataset for measurement': [99999],
    })
    rendered = {}

    class PreviewPath:
        def __init__(self, _filename):
            self.absolute = str(filename)

        def up(self):
            return ''

    monkeypatch.setattr(dbimport_page, 'Path', PreviewPath)
    monkeypatch.setattr(dbimport_page.di, 'checkimport', lambda _path: None)
    monkeypatch.setattr(
        dbimport_page.di.ImportDescription,
        'from_file',
        lambda _path: description,
    )
    monkeypatch.setattr(dbimport_page.pi, 'load_dataframe', lambda _config, _path: frame)
    monkeypatch.setattr(
        dbimport_page.pi,
        'get_statistics',
        lambda _config, _frame: ({}, frame.time.min(), frame.time.max()),
    )
    monkeypatch.setattr(dbimport_page, 'plot_series', lambda _config, _frame: {})

    def capture_render(_template, **kwargs):
        rendered.update(kwargs)
        return SimpleNamespace(render=lambda: 'preview')

    monkeypatch.setattr(dbimport_page.web, 'render', capture_render)

    result = dbimport_page.DbImportPage().conf('preview.csv')

    assert result == 'preview'
    assert 'measurement misses the following datasets [99999]' in rendered['error']
    




