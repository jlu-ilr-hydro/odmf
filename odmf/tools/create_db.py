from getpass import getpass
import logging

import sys

from typing import List

logger = logging.getLogger(__name__)




def create_all_tables() -> List[str]:
    """
    Creates all database table necessary for the database from the codebase
    :return: A list of
    """
    from odmf import db
    db.Base.metadata.create_all(db.engine)
    return list(db.Base.metadata.tables)



def add_admin(password=None):
    """
    Add an odmf.admin role to the person table
    :param password: The password of the admin. If missing you will be prompted
    :return:
    """
    from odmf import db
    from odmf.tools import hashpw
    password = password or getpass("Enter admin password:")
    with db.session_scope() as session:
        if session.query(db.Person).get('odmf.admin'):
            logger.info('odmf.admin exists already')
        else:
            user = db.Person(username='odmf.admin', firstname='odmf', surname='admin',
                             access_level=4)
            user.password = hashpw(password)
            session.add(user)
            logger.info('odmf.admin user created')


def add_quality_data(data):
    """
    Adds the data quality items to the Quality Table
    :param data: A list of dicts (quality_data below)
    """
    from odmf import db
    with db.session_scope() as session:

        for q in data:
            if not session.query(db.Quality).get(q['id']):
                session.add(db.Quality(**q))
                logger.debug(f'Added quality level {q["id"]}')
        session.commit()


quality_data = [
    {
        "comment": "Raw, unprocessed data",
        "name": "raw",
        "id": 0
    },
    {
        "comment": "Raw data, but with adjustments to the data format (eg. date and timestamps corrected, NoData changed to Null)",
        "name": "formal checked",
        "id": 1
    },
    {
        "comment": "Checked and recommended for further processing",
        "name": "quality checked ok",
        "id": 2
    },
    {
        "comment": "Calculated value",
        "name": "derived value",
        "id": 10
    },
    {
        "comment": "Dataset is calibrated against manual measurements",
        "name": "calibrated",
        "id": 3
    }
]

def wait_for_db(database_url: str, wait_time: float=20):
    """
    Tries repeatly to connect to the database until the wait_time is running up
    """
    import time
    from sqlalchemy import create_engine
    start = time.time()
    i = 1
    exc = None
    while time.time() - start < wait_time:
        try:
            time.sleep(0.25)
            logger.debug(f'try to connect to database {i}')
            engine = create_engine(database_url, encoding='utf-8')
            with engine.connect():
                ...
        except Exception as e:
            i += 1
            exc = e
        else:
            break
    else:
        logger.critical(f'No connection to {database_url} after {wait_time}s and {i} tries\n')
        logger.critical(f'{exc}\n')
        exit(100)



def init_db(admin_password: str, wait_time=20):
    """
    Creates in the database: all tables, a user odmf.admin
    and fills the data-quality table with some usable input
    """
    from ..config import conf
    logging.info('wait for database')
    wait_for_db(conf.database_url, wait_time)
    logger.info('create tables')
    tables = create_all_tables()
    add_admin(admin_password)
    logger.info('created admin user odmf.admin')
    add_quality_data(quality_data)
    logger.info('added quality levels')
    return tables


