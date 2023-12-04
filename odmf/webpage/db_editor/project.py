import cherrypy

from .. import lib as web
from ..auth import group, expose_for, users, Level

from ... import db
from ...config import conf

@cherrypy.popargs('project_id')
@web.show_in_nav_for(1, 'user-friends')
class ProjectPage:

    @expose_for()
    def index(self, project_id=None, error=None, msg=None):

        with db.session_scope() as session:
            projects = db.ObjectGetter(db.Project, session)
            persons = db.ObjectGetter(db.Person, session)
            supervisors = persons.q.filter(db.Person.access_level >= 3)

            if project_id == 'new':
                project_from_id = db.Project()

            elif project_id is None:
                project_from_id = None
            else:
                project_from_id = projects[int(project_id)]

            return web.render('project.html',
                              projects=projects.q.order_by(db.Project.id),
                              actproject=project_from_id,
                              supervisors=supervisors,
                              persons=persons, error=error, msg=msg) \
                .render()


    @expose_for()
    @web.method.post
    def save(self, project_id:str, name:str, person:str, comment: str, sourcelink: str, organization: str):
        error = ''

        project_id = int(project_id)
        if Level.my(project_id) >= Level.admin:
            try:
                with db.session_scope() as session:
                    if project_id:
                        project = db.Project.get(session, project_id)
                    else:
                        project = db.Project()
                        session.add(project)

                    person = session.query(db.Person).get(person)
                    project.name = name
                    project.comment = comment
                    project.sourcelink = sourcelink
                    project.organization = organization
                    project.person_responsible = person
                    if person is None:
                        raise RuntimeError('Spokesperson not found')
            except RuntimeError as e:
                error = f'Save failed: {e}'
            users.load()
        else:
            error = 'Not enough privileges to edit this project'
        raise web.redirect(f'/{conf.root_url}project/{project_id}', error=error, msg=f'{name} updated' if not error else None)


    @expose_for(group.supervisor)
    @web.method.post
    def add_member(self, project_id, member_name, access_level):
        error = None
        try:
            with db.session_scope() as session:
                project = db.Project.get(session, project_id)
                project.add_member(member_name, int(access_level))
        except (RuntimeError, ValueError) as e:
            error = f'### Save failed: \n\n{e}'
        users.load()
        raise web.redirect(f'/{conf.root_url}project/{project_id}', error=error, msg=f'{member_name} added' if not error else None)

    @expose_for(group.supervisor)
    @web.method.post
    def remove_member(self, project_id, member_name):
        error = None
        try:
            with db.session_scope() as session:
                project = db.Project.get(session, project_id)
                project.remove_member(member_name)
        except RuntimeError as e:
            error = f'Save failed: {e}'
        users.load()
        raise web.redirect(f'/{conf.root_url}project/{project_id}', error=error, msg=f'{member_name} removed' if not error else None)


