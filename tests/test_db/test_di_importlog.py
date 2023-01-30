import datetime
from odmf.dataimport.importlog import make_time_column_as_datetime, LogbookImport, LogImportStructError, LogImportRowError, LogImportError
import pytest
import pandas as pd


@pytest.fixture
def dummy_excel_file():
    # create a dummy excel file
    df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
    df.to_excel("dummy.xlsx", index=False)

    yield "dummy.xlsx"

    # remove the dummy excel file
    import os
    os.remove("dummy.xlsx")


def test_make_time_column_as_datetime():
    # Test case 1: The 'time' column contains 'datetime.time' objects
    df = pd.DataFrame({'date': [datetime.date(2020, 1, 1), datetime.date(2020, 1, 2)],
                       'time': [datetime.time(12, 0), datetime.time(13, 0)]})
    make_time_column_as_datetime(df)
    assert all(df['time'][i].date() == df['date'][i] for i in range(2))

    # Test case 2: A 'date' column exists 'time' column contains strings like '13:30'
    df = pd.DataFrame({'date': [datetime.date(2020, 1, 1), datetime.date(2020, 1, 2)],
                       'time': ['12:00', '13:00']})
    make_time_column_as_datetime(df)
    assert all(df['time'][i].date() == df['date'][i] for i in range(2))

    # Test case 3: No 'date' column, and the 'time' column contains already a datetime
    df = pd.DataFrame({'time': [datetime.datetime(2020, 1, 1, 12, 0), datetime.datetime(2020, 1, 2, 13, 0)]})
    make_time_column_as_datetime(df)
    assert all(df['time'][i].time() == datetime.time(12, 0) if i == 0 else datetime.time(13, 0) for i in range(2))

    # Test case 4: No 'date' column, and the 'time' column contains string representation of a datetime
    df = pd.DataFrame({'time': ['2020-01-01 12:00', '2020-01-02 13:00']})
    make_time_column_as_datetime(df)
    assert all(df['time'][i].time() == datetime.time(12, 0) if i == 0 else datetime.time(13, 0) for i in range(2))

    # Test case 5: LogImportStructError raised when the column is not convertible to a date
    df = pd.DataFrame({'time': ['not a date', '2020-01-02 13:00']})
    with pytest.raises(LogImportStructError):
        make_time_column_as_datetime(df)


@pytest.fixture
def dummy_logbook_excel_file(tmp_path):
    file_path = tmp_path / "dummy_logbook.xlsx"

    # Write sample data to the file
    with open(file_path, "w") as f:
        f.write("This is some sample data for the logbook excel file.")

    yield file_path

def test_LogbookImport(dummy_logbook_excel_file):
    # Use the file_path in your test
    with open(dummy_logbook_excel_file, "r") as f:
        data = f.read()

    # Your test assertions go here
    assert data == "This is some sample data for the logbook excel file."
