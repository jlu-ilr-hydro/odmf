body_no_data = """
Dear {user},

an account to the field data platform ODMF (https://lfe-data.fb09.uni-giessen.de) has been created for you - either on your request or because you 
are / were part of a research project. You have not logged yourself in since at least 90 days, your account will be deleted in 14 days or later. If you
agree with the deletion, no further action is required.

To prevent the deletion of your account, please log into the website with your username and password. If you are not in a network at JLU, Uni Kassel Campus Witzenhausen or ZALF, you will need 
use a different username / password pair first to access the website. For this first challenge, before the web site shows the username is "lfe" and the password 
"OEJYVyo6RrO6xs2eAk". Afterwards log in on the website with your personal username (usually firstname.lastname) and password. If you forgot your credentials, please
write an email to philipp.kraft@umwelt.uni-giessen.de to retrieve a new password. If you want to create a new account, please write me also stating to which project you do belong.

Best regards,

Philipp Kraft

Developer and Administrator of ODMF
"""


from pathlib import Path
import datetime
from odmf import db




def main():
    """
    Loops through the users, checks if the user is stale (last login more than 90 days ago or None) and if the stale user is a data owner
    """

    with db.session_scope() as session:
        
        q = db.sql.select(db.Person).where(db.sql.or_(db.Person.last_login < datetime.datetime(2026,8,1), db.Person.last_login.is_(None)))
        stale_users_no_data = []
        stale_users_with_data = []
        for user in session.scalars(q):
            datasets = session.scalars(db.sql.select(db.Dataset.id).where(db.Dataset.measured_by == user)).all()
            n_records = session.scalar(db.sql.select(db.sql.func.count(db.Record.id)).where(db.Record._dataset.in_(datasets)))
            n_logs = session.scalar(db.sql.select(db.sql.func.count(db.Log.id)).where(db.Log.user == user))
            owned_directories = [
                of.parent
                for of in Path('datafiles/').rglob('.owner')
                if user.username in of.read_text()
            ]
            n_files = sum(
                len([*p.rglob('*')])
                for p in owned_directories
            )

            if not any((len(datasets), n_logs, n_files)):
                stale_users_no_data.append(user)
                print(user, 'no data')
            else:
                stale_users_with_data.append(user)
                print(user, f'{len(datasets)} datasets, {n_records} records, {n_logs} logs, {n_files} files')




