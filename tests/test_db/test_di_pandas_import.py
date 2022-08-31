import pytest

from .. import conf
from ..test_db import db
from .test_di_base import di_conf_file

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


def test_load_dataframe(csv_file_for_import, db):
    from odmf.dataimport import pandas_import as pi
    idescr = pi.ImportDescription.from_file(csv_file_for_import)
    df = pi.load_dataframe(idescr=idescr, filepath=csv_file_for_import)
    assert not df.empty




