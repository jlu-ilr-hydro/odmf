import odmf.dataimport.pandas_import
from odmf.dataimport.base import ImportDescription, ImportColumn
import typing
from odmf import db
import pandas as pd
import re
import datetime
from odmf.config import conf
import os
from odmf.tools import Path
from logging import getLogger
logger = getLogger(__name__)
from odmf.dataimport.pandas_import import *

# Import sample obtained data of Odyssey logger
sample_file = 'RG_050_004.CSV'
path = os.path.abspath(sample_file)


def test_load_dataframe():
    df = odmf.dataimport.pandas_import.load_dataframe(idescr=ImportDescription, filepath=path)
    assert df




