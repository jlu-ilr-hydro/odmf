"""
This is a copy of odmf-docker/start-odmf.py

This script is meant to run in a container, to startup an ODMF-Server from scratch

Steps:

A) Make a config.yml using the following environmental variables:

- DB_TYPE, DB_USER, DB_PASSWORD, DB_NAME
- ODMF_PORT, ODMF_ROOT_URL, ODMF_DATETIME_DEFAULT_TIMEZONE

B) Try to connect to the database described by the config.yml

C) Create the database schema (see tools/create_db.py)

D) Start the server
"""

import os
import sys
from pathlib import Path
import odmf

print('odmf=', odmf.__version__)

config_file = Path('config.yml')
print(config_file.absolute())


def get_config():
    from odmf.config import conf
    conf.database_url = '{DB_TYPE}://{DB_USER}:{DB_PASSWORD}@db:5432/{DB_NAME}'.format(**os.environ)
    conf.server_port = int(os.environ.get('ODMF_PORT', conf.server_port))
    conf.root_url = os.environ.get('ODMF_ROOT_URL', conf.root_url)
    conf.datetime_default_timezone = os.environ.get('ODMF_DATETIME_DEFAULT_TIMEZONE', conf.datetime_default_timezone)
    conf.to_yaml(config_file.open('w', encoding='UTF-8'))
    return conf

def wait_for_db(conf, wait_time=20):
    import time
    from sqlalchemy import create_engine
    start = time.time()
    i = 0
    exc = None
    while time.time() - start < wait_time:
        try:
            time.sleep(0.25)
            engine = create_engine(conf.database_url, encoding='utf-8')
            with engine.connect():
                ...
        except Exception as e:
            i += 1
            exc = e
        else:
            break
    else:
        sys.stderr.write(f'No connection to {conf.database_url} after {wait_time}s and {i} tries\n')
        sys.stderr.write(f'Error: {exc}\n')
        exit(100)

def make_db():
    """
    Creates in the database: all tables, a user odmf.admin
    and fills the data-quality table with some usable input
    """
    from odmf.tools import create_db as cdb
    cdb.create_all_tables()
    print('  - created tables')
    cdb.add_admin(os.environ['ODMF_ADMIN_PW'])
    print('  - created admin user odmf.admin')
    cdb.add_quality_data(cdb.quality_data)
    print('  - added quality levels')


def start():
    from odmf.tools import server
    server.prepare_workdir()
    server.start()


conf = get_config()
print('Connect to:', conf.database_url)
wait_for_db(conf, 10)
print('Create DB schema')
make_db()
print('Start Server')
start()
