import cherrypy

from .. import lib as web
from ..auth import users, expose_for, hashpw, is_self, Level

from ... import db
from traceback import format_exc as traceback


@web.show_in_nav_for(1, 'user')
# @cherrypy.popargs('username')
class PersonPage:

    def index_get(self, username, error=None, msg=None):
        ...

    def index_post(self, username, **kwargs):
        ...

    @expose_for(Level.logger)
    def default(self, act_user=None, error='', msg=''):
        with db.session_scope() as session:
            persons = session.query(db.Person).order_by(
                db.sql.desc(db.Person.can_supervise), db.Person.surname)
            me: db.Person = session.query(db.Person).get(users.current.name)
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
                    p_act = session.get(db.Person, act_user)
                    if p_act is None:
                        raise ValueError(
                            "There is no user with the name '%s'" % act_user)
                    jobs = p_act.jobs.order_by(db.sql.asc(
                        db.Job.done), db.sql.asc(db.Job.due))
                except:
                    p_act = session.get(db.Person, users.current.name)
                    error = traceback()
            user_projects = [p for p, level in p_act.projects()]
            if me.access_level >= Level.admin:
                potential_projects = [p for p in session.query(db.Project).order_by(db.Project.id) if p not in user_projects]
            else:
                potential_projects = [
                    p for p, level in me.projects()
                    if level >= Level.admin and p not in user_projects
                ]
            topics = db.sql.select(db.message.Topic).order_by(db.message.Topic.id)
            return web.render(
                'person.html',
                persons=persons,
                active_person=p_act,
                supervisors=supervisors,
                error=error, success=msg,
                jobs=jobs,
                act_user=act_user,
                potential_projects=potential_projects,
                topics = session.scalars(topics),
                is_self=is_self
            ).render()

    @expose_for(Level.logger)
    @web.method.post
    def saveitem(self, **kwargs):
        username = kwargs.get('username')
        error = ''
        msg = ''
        if is_self(username) or users.current.level >= Level.admin:
            with db.session_scope() as session:
                p_act = session.query(db.Person).filter_by(
                    username=username).first()
                if not p_act:
                    p_act = db.Person(username=username, active=False, access_level=0)
                    session.add(p_act)
                p_act.email = kwargs.get('email')
                p_act.firstname = kwargs.get('firstname')
                p_act.surname = kwargs.get('surname')
                p_act.telephone = kwargs.get('telephone')
                p_act.comment = kwargs.get('comment')
                if kwargs.get('status') == 'on' or is_self(username):
                    p_act.active = True
                else:
                    p_act.active = False

                # Simple Validation
                if kwargs.get('password') and (users.current.is_member(Level.admin) or is_self(username)):
                    pw = kwargs['password']
                    pw2 = kwargs.get('password_verify')
                    if len(pw) < 8:
                        error = 'Password needs to be at least 8 characters long'
                    elif pw == pw2:
                        p_act.password = hashpw(pw)
                    else:
                        error = 'Passwords not equal'

                # Simple Validation
                acl = web.conv(int, kwargs.get('access_level'))
                if acl and acl <= users.current.level:
                    p_act.access_level = acl

                #topics
                topics = kwargs.get('topics[]')
                if type(topics) is str: topics = [topics]
                p_act.topics = session.scalars(
                    db.sql.select(db.message.Topic)
                    .where(db.message.Topic.id.in_(topics or []))
                ).all()


                if error:
                    raise web.redirect(username, error=error)
                msg = f'{username} saved'
        else:
            error=f'As a {users.current.Level.name} user, you may only change your own values'

        raise web.redirect(username, error=error, msg=msg)

    @expose_for(Level.editor)
    @web.method.post
    def addproject(self, username, project, level):
        with db.session_scope() as session:
            me: db.Person = session.query(db.Person).get(users.current.name)
            user: db.Person = session.query(db.Person).get(username)
            project: db.Project = session.query(db.Project).get(int(project))
            level = Level(int(level))
            if project.get_access_level(me) >= Level.admin:
                project.add_member(user, level)
                msg = f'Added {user} to {project} as {level.name}'
            else:
                raise web.HTTPError(403, f'You are not an admin of the project {project}, can\'t add members')
        raise web.redirect(username, msg=msg)


    @expose_for()
    @web.mime.json
    def json(self, supervisors=False):
        with db.session_scope() as session:
            persons = session.query(db.Person).order_by(
                db.sql.desc(db.Person.can_supervise), db.Person.surname)
            if supervisors:
                persons = persons.filter(db.Person.can_supervise == True)
            return web.json_out(persons.all())

