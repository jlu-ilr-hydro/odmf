import pytest
from ..test_db import db, session, conf
from .test_di_base import di_conf_file
from .db_fixtures import project, person

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
    




