from odmf.config import conf
from odmf.tools import Path
from odmf import db


import contextlib

import odmf.dataimport.base as b
import time

@contextlib.contextmanager
def timeit(name='action'):
    tstart = time.time()
    yield
    d = time.time() - tstart
    print(f'------------ {name} took {d:0.3f} seconds')

with timeit('get session'):
    session = db.Session()

fn = Path('soil-moisture/ArableLand_25/EM9767 11Nov20-1247.xlsx')

with timeit('load data frame'):
    if not fn.exists():
        raise IOError(f'{fn} does not exist')
    idescr = b.ImportDescription.from_file(fn.absolute)
    from odmf.dataimport import pandas_import as pi
    df, warning = pi.load_dataframe(idescr, fn)

print()
print(f'{len(warning)} warnings:')
print('\n'.join(warning))
print()
print(df.describe())

with timeit('make datasets'):
    datasets = pi._new_datasets_from_descr(session, idescr, 'philipp', 25, fn, df.time.min().to_pydatetime(), df.time.max().to_pydatetime())

print(datasets)

session.rollback()