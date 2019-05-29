import odmf.webpage.auth as auth
import odmf.db as db
import random
import string


with db.session_scope() as session:
    users = session.query(db.Person)
    for user in users:
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        user.password = auth.hashpw(new_password)
        print(user.username, new_password)

    session.rollback()


