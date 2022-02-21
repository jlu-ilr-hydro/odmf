from odmf import db
from getpass import getpass
from logging import warning
from typing import List


def create_all_tables() -> List[str]:
    """
    Creates all database table necessary for the database from the codebase
    :return: A list of
    """
    db.Base.metadata.create_all(db.engine)
    return list(db.Base.metadata.tables)



def add_admin(password=None):
    """
    Add an odmf.admin role to the person table
    :param password: The password of the admin. If missing you will be prompted
    :return:
    """
    from odmf.tools import hashpw
    password = password or getpass("Enter admin password:")
    with db.session_scope() as session:
        if session.query(db.Person).get('odmf.admin'):
            warning('odmf.admin exists already')
        else:
            user = db.Person(username='odmf.admin', firstname='odmf', surname='admin',
                             access_level=4)
            user.password = hashpw(password)
            session.add(user)


def add_quality_data(data):
    """
    Adds the data quality items to the Quality Table
    :param data: A list of dicts (quality_data below)
    """
    with db.session_scope() as session:

        for q in data:
            if not session.query(db.Quality).get(q['id']):
                session.add(db.Quality(**q))
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


if __name__ == '__main__':
    create_all_tables()
    add_admin()
    add_quality_data(quality_data)

