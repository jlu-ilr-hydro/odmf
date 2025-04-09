import cherrypy
from ...config import conf
from .. import lib as web
from ..auth import users, expose_for, hashpw, is_self, Level
from ...tools import Path as OPath
from ... import db


@web.show_in_nav_for(1, 'user')
@cherrypy.popargs('username')
class PersonPage:

    @staticmethod
    def index_get(username):
        error = ''
        with db.session_scope() as session:
            persons = session.query(db.Person).order_by(db.Person.surname)
            me: db.Person = session.get(db.Person, users.current.name)
            # 'guest' user can't see himself in the user list
            if users.current.name == 'guest':
                persons = persons.filter(db.Person.access_level != 0)
            jobs = []
            act_user = username or users.current.name
            if act_user == 'new':
                p_act = db.Person(active=True)
            else:
                p_act = session.get(db.Person, act_user)
                if p_act is None:
                    error = "There is no user with the name '%s'" % act_user
                    p_act = me
                jobs = p_act.jobs.order_by(db.sql.asc(
                    db.Job.done), db.sql.asc(db.Job.due))

            user_projects = [p for p, level in p_act.projects()]
            if me.access_level >= Level.admin:
                potential_projects = [p for p in session.query(db.Project).order_by(db.Project.id) if
                                      p not in user_projects]
            else:
                potential_projects = [
                    p for p, level in me.projects()
                    if level >= Level.admin and p not in user_projects
                ]
            has_home = OPath('users', username).exists()
            topics = db.sql.select(db.message.Topic).order_by(db.message.Topic.id)
            return web.render(
                'person.html',
                persons=persons,
                active_person=p_act,
                me=users.current,
                error=error,
                jobs=jobs,
                act_user=act_user,
                potential_projects=potential_projects,
                topics=session.scalars(topics),
                is_self=is_self,
                has_home=has_home,
            ).render()

    @staticmethod
    def index_post(username, **kwargs):
        is_new_user = username == 'new'
        username = kwargs.get('newname', username)
        me =users.current
        error = ''
        msg = ''
        if is_self(username) or users.current.is_admin_of(users.get(username)) or (me.access_level >= Level.supervisor and is_new_user):
            with db.session_scope() as session:
                p_act = session.get(db.Person, username)
                if not p_act and is_new_user:
                    p_act = db.Person(username=username, active=False, access_level=0)
                    session.add(p_act)
                    session.flush()

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
                topics = web.to_list(kwargs.get('topics[]'))
                if topics:
                    p_act.topics = session.scalars(
                        db.sql.select(db.message.Topic)
                        .where(db.message.Topic.id.in_(topics or []))
                    ).all()

                if error:
                    raise web.redirect(conf.url('person', username), error=error)
                msg = f'{username} saved'
                users.load()
        else:
            error = f'As a {users.current.Level.name} user, you may only change your own values'

        raise web.redirect(conf.url('user', username), error=error, success=msg)

    @expose_for(Level.logger)
    def index(self, username=None, **kwargs):
        if cherrypy.request.method == 'GET':
            return self.index_get(username)
        elif cherrypy.request.method == 'POST':
            return self.index_post(username, **kwargs)

    @expose_for(Level.editor)
    @web.method.post
    def addproject(self, username, project, level=0):
        with db.session_scope() as session:
            me: db.Person = session.query(db.Person).get(users.current.name)
            user: db.Person = session.query(db.Person).get(username)
            project: db.Project = session.query(db.Project).get(int(project))
            level = Level(int(level or 0))
            if project.get_access_level(me) >= Level.admin:
                project.add_member(user, level)
                msg = f'Added {user} to {project} as {level.name}'
            else:
                raise web.HTTPError(403, f'You are not an admin of the project {project}, can\'t add members')
        raise web.redirect(conf.url('user', username), success=msg)


    @expose_for()
    @web.mime.json
    def json(self, supervisors=False):
        with db.session_scope() as session:
            persons = session.query(db.Person).order_by(
                db.sql.desc(db.Person.can_supervise), db.Person.surname)
            if supervisors:
                persons = persons.filter(db.Person.can_supervise == True)
            return web.json_out(persons.all())

    @expose_for()
    def home(self, username):
        me = users.current
        other = users.get(username, me)
        p = (OPath('users') / username)
        if cherrypy.request.method == 'POST':
            if me.is_admin_of(other) or is_self(username):
                if not p.exists():
                    pp = p.to_pythonpath()
                    pp.mkdir(parents=True)
                    (pp /'.owner').write_text(username)
                    (pp / '.access.yml').write_text('projects: []\nread: 4\nwrite: 4\n')
                raise web.redirect(conf.url('user', username), success='Created home directory')
            else:
                raise web.HTTPError(403, f'You are not an admin of {username}')

        elif cherrypy.request.method == 'GET':
            if p.exists():
                return p.href.encode('utf-8')
            else:
                raise web.HTTPError(404, f'User directory for {username} does not exist')


