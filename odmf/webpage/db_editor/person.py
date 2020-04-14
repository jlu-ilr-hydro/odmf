import cherrypy

from .. import lib as web
from ..auth import users, group, expose_for, hashpw, is_self, get_levels, HTTPAuthError

from ... import db
from traceback import format_exc as traceback


@web.show_in_nav_for(1, 'user')
class PersonPage:

    @expose_for(group.logger)
    def default(self, act_user=None, error='', msg=''):
        with db.session_scope() as session:
            persons = session.query(db.Person).order_by(
                db.sql.desc(db.Person.can_supervise), db.Person.surname)

            # 'guest' user can't see himself in the user list
            if users.current.name == 'guest':
                persons = persons.filter(db.Person.access_level != 0)
                # TODO: url "host/guest" shouldn't be accessible for the guest user

            supervisors = persons.filter(db.Person.can_supervise == True)
            jobs = []
            act_user = act_user or users.current.name
            if act_user == 'new':
                p_act = db.Person(active=True)
            else:
                try:
                    p_act = session.query(db.Person).get(act_user)
                    if p_act is None:
                        raise ValueError(
                            "There is no user with the name '%s'" % act_user)
                    jobs = p_act.jobs.order_by(db.sql.asc(
                        db.Job.done), db.sql.asc(db.Job.due))
                except:
                    p_act = session.query(db.Person).get(users.current.name)
                    error = traceback()
            return web.render(
                'person.html',
                persons=persons,
                active_person=p_act,
                supervisors=supervisors,
                error=error, message=msg,
                jobs=jobs,
                act_user=act_user,
                levels=get_levels,
                is_self=is_self
            ).render()

    @expose_for(group.supervisor)
    @web.method.post
    def saveitem(self, **kwargs):
        username = kwargs.get('username')
        error = ''
        msg = ''
        if username:
            with db.session_scope() as session:
                p_act = session.query(db.Person).filter_by(
                    username=username).first()
                if not p_act:
                    p_act = db.Person(username=username)
                    session.add(p_act)
                p_act.email = kwargs.get('email')
                p_act.firstname = kwargs.get('firstname')
                p_act.surname = kwargs.get('surname')
                if 'supervisor' in kwargs:
                    p_act.supervisor = session.query(
                        db.Person).get(kwargs.get('supervisor'))
                p_act.telephone = kwargs.get('telephone')
                p_act.comment = kwargs.get('comment')
                if kwargs.get('status') == 'on':
                    p_act.active = True
                else:
                    p_act.active = False

                # Simple Validation
                if 'password' in kwargs and kwargs['password']:
                    if len(kwargs.get('password')) < 8:
                        error = 'Password needs to be at least 8 characters long'
                    elif kwargs.get('password') == kwargs.get('password_verify'):
                        p_act.password = hashpw(kwargs.get('password'))
                    else:
                        error = 'Passwords not equal'
                # Simple Validation
                # if users.current.level == ACCESS_LEVELS['Supervisor']:
                p_act.access_level = int(kwargs.get('access_level'))
                msg = f'{username} saved'
        else:
            error='Missing user name'

        web.redirect(username, error=error, msg=msg)

    @expose_for()
    @web.mime.json
    def json(self, supervisors=False):
        with db.session_scope() as session:
            persons = session.query(db.Person).order_by(
                db.sql.desc(db.Person.can_supervise), db.Person.surname)
            if supervisors:
                persons = persons.filter(db.Person.can_supervise == True)
            return web.json_out(persons.all())

    @expose_for(group.logger)
    def changepassword(self, username=None):
        """
        Form request
        """
        session = db.Session()
        changing_user_level = session.query(db.Person).filter(
            db.Person.username == username).first().access_level

        # cast from unicode to int
        changing_user_level = int(changing_user_level)

        if changing_user_level > users.current.level:
            raise HTTPAuthError()
        else:
            error = ''
            result = web.render('passwordchange.html',
                                error=error, username=username).render()

        session.close()

        return result

    @expose_for(group.logger)
    def savepassword(self, **kwargs):
        """
        Save to database
        """
        password = kwargs.get('password')
        password_repeat = kwargs.get('password_repeat')
        username = kwargs.get('username')

        if password is None or password_repeat is None or username is None:
            raise IOError

        # if password != password_repeat:
        #    error = 'Error: Password don\'t match'
        #    result = web.render('passwordchange.html', error=error, username=username)\
        #        .render()

        # Password encryption and db saving
        session = db.Session()

        p_act = session.query(db.Person).filter_by(username=username).first()
        p_act.password = hashpw(password)

        session.commit()
        session.close()

        raise web.HTTPRedirect('./' + username)

