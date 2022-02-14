from odmf.config import conf
from odmf.tools import Path
from odmf import db
import pandas as pd
import os
import time
import numpy as np
import time
import contextlib
import time
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)

@contextlib.contextmanager
def timeit(name='action'):
    tstart = time.time()
    yield
    d = time.time() - tstart
    print(f'------------ {name} took {d:0.3f} seconds')

session: db.orm.Session = db.Session()

greeting = """
    Imported modules
    ----------------

    pd, np, conf, db

    Defined symbols
    ---------------
    session: a SQLAlchemy session to load Database objects
    q: a shortcut for session.query
    ds: An ObjectGetter for datasets
    person: An ObjectGetter for persons
    site: An ObjectGetter for sites

    Usage of a ObjectGetters: 

    Get dataset with id=1
    >>>ds_one = ds[1]
    Query sites:
    >>>site.q.filter(db.Site.lat > 50.5).count()        
    """

q = session.query
ds = db.base.ObjectGetter(db.Dataset, session)
person = db.base.ObjectGetter(db.Person, session)
site = db.base.ObjectGetter(db.Site, session)

# Set default user
from odmf.webpage import auth
auth.users.load()
auth.users.set_default('philipp')

print(greeting)
