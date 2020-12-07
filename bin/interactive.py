from odmf.config import conf
from odmf.tools import Path
from odmf import db
import yaml
from odmf.dataimport import pandas_import as pi
import contextlib

import odmf.dataimport.base as b
import time

@contextlib.contextmanager
def timeit(name='action'):
    tstart = time.time()
    yield
    d = time.time() - tstart
    print(f'------------ {name} took {d:0.3f} seconds')

session: db.orm.Session = db.Session()

fn = Path('climate-data/178_upSchwingbach/CR1000_upSchwingbach_Table1_2020_11_10_16_20.dat')
print(fn.absolute)
with timeit('get description'):
    if not fn.exists():
        raise IOError(f'{fn} does not exist')
    idescr = b.ImportDescription.from_file(fn.absolute)
    print(idescr)

with timeit('load data frame'):
    
    df, warning = pi.load_dataframe(idescr, fn)

print()
print(f'{len(warning)} warnings:')
print('\n'.join(warning))
print()
print(df.describe())

with timeit('submit'):
    msg = pi.submit(session, idescr, fn, user='philipp', siteid=25)

print('\n'.join(msg))

dsg = db.DatasetItemGetter(session)
# session.rollback()
