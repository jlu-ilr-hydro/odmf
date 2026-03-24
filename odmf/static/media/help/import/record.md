# Import large prepared datasets with a record table

If you can design a workflow (eg. in Python or R) to assemble measurements in a predefined form, you can create
a table that is exactly like the internal **record** table to import data into **existing datasets**. The tabular format can be Excel, CSV or Parquet (recommended). The method assumes your workflow applies sanity checks etc. 

!!! warning "Warning!"
    Only completely correct files can be used for import Because **record import** can scatter values around in the database, errors are very difficult to correct and usually only resolved with the site admin and the the programming backdoor.

## Table layout
### Necessary columns

- dataset (int), references existing datasets
- time (datetime), timestamp of the measurement, in CSV files use ISO format YYYY-mm-dd HH:MM:SS
- value (float), actual value in the unit of the valuetype of the target dataset prior to the calibration.

### Optional columns

- id (int) will be changed if necessary
- is_error (bool), marks error records, default is False
- sample (text), indicates a sample name for external reference
- comment (text), any additional explanation

## Import from the file manager

The table can be imported from the file-manager using the *record-import* button for fitting Excel, CSV or Parquet (recommended) files. If the table can be read and has the necessary columns, the button appears in the tabular view. CSV files can only be imported in the international format, `,` as seperator and `.` as decimal point.

!!! note "Note:"
    Tables for log-import (help:import/log ) are also valid record import tables. Log import does more checking for typing errors etc.

## Import via the API

It is also possible to post the table in Parquet format to the API. You need to:

- create a http session with your login
- write the table data to a parquet stream
- post the stream to ../api/dataset/add_records_parquet. 

If you are a Python programmer, you can use the Python package
[odmfclient](https://github.com/jlu-ilr-hydro/odmfclient)
[![PyPI](https://img.shields.io/pypi/v/odmfclient?logo=pypi)](https://pypi.org/project/odmfclient/)

### Python example

The following example shows how to a dataframe with crap data to two **existing** datasets 9998 and 9999

~~~~~~~~~~~~~~~~~~~~~~.py
from odmfclient import login
import pandas as pd

# create dataframe with crap data
 pd.DataFrame({'dataset': [9998, 9999]*100, 'time': [pd.to_datetime('2026-02-23')]*200, 'value':[1,2]*100})

# send the dataframe to ODMF, see https://github.com/jlu-ilr-hydro/odmfclient for more information
with login('https://path/to/odmf', 'user', 'password') as api:
    api.dataset.add_records_parquet(df)

~~~~~~~~~~~~~~~~~~~~~~

