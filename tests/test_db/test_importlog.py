from datetime import date, datetime, time, timedelta

import pandas as pd
import pytest

from odmf.dataimport.importlog import (
    LogbookImport,
    LogImportStructError,
    make_time_column_as_datetime,
)
from odmf import db as orm
from . import conf, db, session
from .db_fixtures import person, site1_in_db


COLUMNS = ['Date', 'Time', 'Site', 'Dataset', 'Value', 'Message', 'LogType', 'Sample']
IMPORT_TIME = datetime(2024, 2, 1, 12, 0)


def write_template(tmp_path, rows, columns=COLUMNS, sheet_name='Field data'):
    filename = tmp_path / 'field-log.xlsx'
    pd.DataFrame(rows, columns=columns).to_excel(
        filename, index=False, sheet_name=sheet_name
    )
    return filename


def record_row(dataset_id=81, value=12.5, **updates):
    row = {
        'Date': IMPORT_TIME.date(),
        'Time': IMPORT_TIME.time(),
        'Site': 1,
        'Dataset': dataset_id,
        'Value': value,
        'Message': 'field measurement',
        'LogType': None,
        'Sample': 'sample-1',
    }
    row.update(updates)
    return row


@pytest.fixture
def manual_timeseries(db, session, person, site1_in_db):
    datasource = orm.Datasource(
        id=81,
        name='manual field measurement',
        sourcetype='manual',
        manuallink='',
    )
    quality = orm.Quality(id=81, name='raw', comment='test quality')
    valuetype = orm.ValueType(
        id=81, name='water level', unit='m', minvalue=0, maxvalue=100
    )
    dataset = orm.Timeseries(
        id=81,
        name='manual field measurements',
        filename='field-measurements.csv',
        start=datetime(2024, 1, 1),
        end=datetime(2024, 1, 2),
        site=site1_in_db,
        valuetype=valuetype,
        measured_by=person,
        quality=quality,
        source=datasource,
        calibration_offset=0,
        calibration_slope=1,
        level=0,
    )
    session.add_all([datasource, quality, valuetype, dataset])
    session.commit()
    yield dataset
    session.query(orm.Log).filter_by(_site=site1_in_db.id).delete(synchronize_session=False)
    session.query(orm.Record).filter_by(_dataset=dataset.id).delete(synchronize_session=False)
    session.delete(dataset)
    session.delete(valuetype)
    session.delete(quality)
    session.delete(datasource)
    session.commit()


def test_make_time_column_combines_excel_date_and_time():
    frame = pd.DataFrame({
        'date': [date(2024, 2, 1)],
        'time': [time(12, 30)],
    })

    make_time_column_as_datetime(frame)

    assert frame.loc[0, 'time'] == pd.Timestamp(2024, 2, 1, 12, 30)


def test_make_time_column_uses_date_with_datetime_time_cells():
    frame = pd.DataFrame({
        'date': ['01/02/2024'],
        'time': ['31/12/1899 12:30'],
    })

    make_time_column_as_datetime(frame)

    assert frame.loc[0, 'time'] == pd.Timestamp(2024, 2, 1, 12, 30)


def test_make_time_column_accepts_datetime_without_separate_date():
    frame = pd.DataFrame({'time': ['01/02/2024 12:30']})

    make_time_column_as_datetime(frame)

    assert frame.loc[0, 'time'] == pd.Timestamp(2024, 2, 1, 12, 30)


def test_make_time_column_reports_unparseable_values():
    frame = pd.DataFrame({'time': ['not a date']})

    with pytest.raises(LogImportStructError, match='not convertible'):
        make_time_column_as_datetime(frame)


def test_log_only_template_can_omit_dataset_column(
    tmp_path, person, site1_in_db, session, manual_timeseries
):
    columns = ['Date', 'Time', 'Site', 'Value', 'Message', 'LogType']
    row = record_row(dataset_id=None, value=None, Message='Bridge inspection')
    filename = write_template(tmp_path, [row], columns)

    importer = LogbookImport(filename, person.username)
    logs, is_ok = importer(commit=True)

    assert is_ok
    assert logs[0]['status'] == 'success'
    saved_log = session.query(orm.Log).filter_by(_site=site1_in_db.id).one()
    assert saved_log.message == 'Bridge inspection'
    assert saved_log.time == IMPORT_TIME


def test_value_only_template_can_omit_logtype_column(
    tmp_path, person, session, manual_timeseries
):
    columns = ['Date', 'Time', 'Site', 'Dataset', 'Value', 'Message', 'Sample']
    filename = write_template(tmp_path, [record_row()], columns)

    importer = LogbookImport(filename, person.username)
    logs, is_ok = importer(commit=True)

    assert is_ok
    assert logs[0]['status'] == 'success'
    saved_record = session.query(orm.Record).filter_by(_dataset=manual_timeseries.id).one()
    assert saved_record.value == 12.5
    assert saved_record.sample == 'sample-1'
    assert saved_record.comment == 'field measurement'
    session.refresh(manual_timeseries)
    assert manual_timeseries.start == datetime(2024, 1, 1)
    assert manual_timeseries.end == IMPORT_TIME


def test_empty_action_row_is_ignored_and_reported_as_warning(
    tmp_path, person, session, manual_timeseries
):
    row = record_row(dataset_id=None, value=None, Message=None)
    filename = write_template(tmp_path, [row, record_row()])

    logs, is_ok = LogbookImport(filename, person.username)(commit=True)

    assert is_ok
    assert [entry['status'] for entry in logs] == ['warning', 'success']
    assert logs[0]['row'] == 1
    assert 'ignored' in logs[0]['log'].lower()
    assert session.query(orm.Record).filter_by(_dataset=manual_timeseries.id).count() == 1


def test_dry_run_does_not_persist_and_commit_writes_record(
    tmp_path, person, session, manual_timeseries
):
    filename = write_template(tmp_path, [record_row()])
    importer = LogbookImport(filename, person.username)

    preview, preview_ok = importer(commit=False)
    assert preview_ok
    assert preview[0]['status'] == 'success'
    assert session.query(orm.Record).filter_by(_dataset=manual_timeseries.id).count() == 0

    committed, committed_ok = importer(commit=True)
    assert committed_ok
    assert committed[0]['status'] == 'success'
    assert session.query(orm.Record).filter_by(_dataset=manual_timeseries.id).count() == 1


def test_hard_row_error_rolls_back_all_rows(
    tmp_path, person, session, manual_timeseries
):
    rows = [record_row(), record_row(dataset_id=999, value=15)]
    filename = write_template(tmp_path, rows)
    importer = LogbookImport(filename, person.username)

    dryrun_logs, dryrun_ok = importer(commit=False)
    assert not dryrun_ok
    assert session.query(orm.Record).filter_by(_dataset=manual_timeseries.id).count() == 0

    logs, is_ok = importer(commit=True)

    assert not is_ok
    assert logs == dryrun_logs
    assert [row['status'] for row in logs] == ['success', 'danger']
    assert 'Dataset 999 does not exist' in logs[1]['log']
    assert session.query(orm.Record).filter_by(_dataset=manual_timeseries.id).count() == 0


@pytest.mark.parametrize(
    ('updates', 'error_text'),
    [
        ({'Site': 2}, 'not located at #2'),
        ({'Value': 101}, 'is not accepted'),
    ],
)
def test_record_row_validation_reports_errors(
    tmp_path, person, manual_timeseries, updates, error_text
):
    filename = write_template(tmp_path, [record_row(**updates)])

    logs, is_ok = LogbookImport(filename, person.username)(commit=False)

    assert not is_ok
    assert logs[0]['status'] == 'danger'
    assert error_text in logs[0]['log']


def test_record_row_rejects_nonmanual_dataset(
    tmp_path, person, session, manual_timeseries
):
    manual_timeseries.source.sourcetype = 'logger'
    session.commit()
    filename = write_template(tmp_path, [record_row()])

    logs, is_ok = LogbookImport(filename, person.username)(commit=False)

    assert not is_ok
    assert logs[0]['status'] == 'danger'
    assert 'not a manually measured dataset' in logs[0]['log']


def test_value_without_dataset_is_a_hard_row_error(tmp_path, person, manual_timeseries):
    filename = write_template(tmp_path, [record_row(dataset_id=None, value=12.5)])

    logs, is_ok = LogbookImport(filename, person.username)(commit=False)

    assert not is_ok
    assert logs[0]['status'] == 'danger'
    assert 'value is given, but no dataset' in logs[0]['log']


def test_log_row_rejects_unknown_site(tmp_path, person, manual_timeseries):
    filename = write_template(
        tmp_path,
        [record_row(dataset_id=None, value=None, Site=999, Message='Field note')],
    )

    logs, is_ok = LogbookImport(filename, person.username)(commit=False)

    assert not is_ok
    assert logs[0]['status'] == 'danger'
    assert 'Site #999 not found' in logs[0]['log']


def test_duplicate_record_rows_in_one_file_are_reported_as_warnings(
    tmp_path, person, session, manual_timeseries
):
    filename = write_template(tmp_path, [record_row(), record_row(value=13)])

    logs, is_ok = LogbookImport(filename, person.username)(commit=True)

    assert is_ok
    assert [entry['status'] for entry in logs] == ['warning', 'warning']
    assert session.query(orm.Record).filter_by(_dataset=manual_timeseries.id).count() == 0


def test_constructor_rejects_unknown_user(tmp_path, manual_timeseries):
    filename = write_template(tmp_path, [record_row()])

    with pytest.raises(LogImportStructError, match='not a valid user'):
        LogbookImport(filename, 'not-a-real-user')


@pytest.mark.parametrize(
    ('offset_seconds', 'is_duplicate'),
    [(-31, False), (-30, True), (30, True), (31, False)],
)
def test_record_duplicate_tolerance_includes_30_second_boundary(
    offset_seconds, is_duplicate, person, session, manual_timeseries
):
    existing_time = IMPORT_TIME
    session.add(orm.Record(
        id=1,
        dataset=manual_timeseries,
        time=existing_time,
        value=10,
        sample=None,
    ))
    session.commit()
    importer = object.__new__(LogbookImport)

    assert importer.recordexists(
        manual_timeseries,
        existing_time + timedelta(seconds=offset_seconds),
    ) is is_duplicate


@pytest.mark.parametrize(
    ('offset_seconds', 'is_duplicate'),
    [(-31, False), (-30, True), (30, True), (31, False)],
)
def test_log_duplicate_tolerance_includes_30_second_boundary(
    offset_seconds, is_duplicate, person, session, site1_in_db, manual_timeseries
):
    session.add(orm.Log(
        time=IMPORT_TIME,
        user=person,
        site=site1_in_db,
        message='existing field note',
        type='observation',
    ))
    session.commit()
    importer = object.__new__(LogbookImport)

    assert importer.logexists(
        session,
        site1_in_db.id,
        IMPORT_TIME + timedelta(seconds=offset_seconds),
    ) is is_duplicate


def test_template_can_select_a_named_sheet(tmp_path, person, manual_timeseries):
    filename = write_template(tmp_path, [record_row()], sheet_name='Measurements')

    importer = LogbookImport(filename, person.username, sheetname='Measurements')
    logs, is_ok = importer(commit=False)

    assert is_ok
    assert logs[0]['status'] == 'success'


def test_constructor_reports_missing_required_columns(tmp_path, person):
    filename = write_template(
        tmp_path,
        [{'Date': date(2024, 2, 1), 'Time': time(12, 0)}],
        columns=['Date', 'Time'],
    )

    with pytest.raises(LogImportStructError, match='misses some'):
        LogbookImport(filename, person.username)
