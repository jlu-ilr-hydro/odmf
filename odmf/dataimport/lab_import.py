"""
Reads a table with lab data using a configuration file (in yaml format)

Example config file:
"""
example="""
config: lab
glob: *.xls? 
worksheet: Table 1       # Optional, only for Excel files, default is first sheet
header row: 5            # Row number of the headers- Optional, default 1
columns:                 # Description of each column, use the column name as object name
    Sample:              # Name of the sample column, in this case Sample
        type: sample     # Necessary to understand column as sample names
        pattern: (\w+?)_([0-9\.]+_[0-9]+\:[0-9]+)_?(?:[-+]?[0-9\.]+)
        site:
            group: 1
            map:
                F1: 137
                F2: 147
                F3: 201
                B1: 123
                B2: 138
                B3: 203
        date:
            group: 2
            format: "%d%m%y_%H:%M"
        level:
            group: 3
    N_NO3:  # The name
        type: value
        factor: 1.0
        valuetype: 3
    N_NH4:
        type: value
        factor: 14.3
        valuetype: 4
"""
import pandas as pd
import yaml
from glob import glob
from ..config import conf
from .. import db
from ..tools import Path
from .sample_parser import SampleParser

def find_dataset(session: db.Session, date=None, site=None, level=None, valuetype=None, instrument=None, dataset=None):
    """
    Finds a dataset, from a rough description.
    - if the dataset id is given, the dataset is returned
    - if other filters are given, they are used. If no dataset exists at the given date, the next earlier dataset fitting the other filters is returned
    - if multiple datasets match the date, an error is raised
    """
    if dataset:
        dataset = int(dataset)
        if ds := session.get(db.Dataset, dataset):
            return ds
        else:
            raise ValueError(f"Dataset {dataset} not found")
    else:
        candidates = db.Dataset.filter(session=session, date=date, valuetype=valuetype, instrument=instrument, level=level, site=site)
        ccount = candidates.count()
        if ccount == 1:
            return candidates.first()
        elif ccount == 0:
            candidate: db.Dataset = (
                db.Dataset.filter(session=session, date=None, valuetype=valuetype, instrument=instrument, level=level, site=site)
                .filter(db.Dataset.end < date)
                .order_by(db.Dataset.desc())
                .limit(1)
            ).first()
            if candidate:
                # check if candidate is unique
                if db.Dataset.filter(session=session, date=candidate.end, valuetype=valuetype, instrument=instrument, level=level, site=site).count() == 1:
                    return candidate
                else:
                    raise ValueError(f"Dataset filter not unique, found multiple fitting datasets with the same end date")
            else:
                raise ValueError(f"No dataset found")
        else: #  Found more datasets with filter at date
            raise ValueError(f"Dataset filter not unique at given date and filter")


def read_file(filename: str, config: dict):

    if filename.endswith(".csv"):
        return pd.read_csv(filename, skiprows=config.get('header row', 1) - 1)
    elif 'xls' in filename.split('.')[-1]:
        return pd.read_excel(
            filename,
            skiprows=config.get('header row', 1) - 1,
            sheet_name=config.get('sheet name', None)
        )

def parse_sample(series: pd.Series, sample_column: dict):
    """
    Parses the sample column
    :param series: The table column with the sample names
    :param sample_column: the config description of the sample column
    :return: a dataframe with parsed columns, a subset of time, site, dataset, level
    """
    sample_column.pop('type')
    sampler = SampleParser(sample_column)

    parsed = pd.DataFrame([
        sampler(v) for v in series
    ],
        index=series.index()
    )
    parsed.dropna(axis=1, how='all', inplace=True)
    return parsed




def labimport():
    """
    Steps to do
    - find config
    - read file
    - check column names
    - aggregate by sample name (`df.groupby('sample_name').mean()`)
    - parse sample
    - assign value types to value columns
    - melt dataframe
    - find datasets and apply to each row
    - drop filter values like site / level / valuetype etc
    - result table has record schema (dataset, id, value, is_error) -> import
    :return:
    """
    ...