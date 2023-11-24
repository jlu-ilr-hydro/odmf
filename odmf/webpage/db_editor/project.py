import cherrypy

from .. import lib as web
from ..auth import group, expose_for

from ... import db
from ...config import conf

@web.show_in_nav_for(1, 'user-friends')
class ProjectPage:

    @expose_for(group.logger)
    def default(self, project_id=None, error=None):

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
                              persons=persons, error=error) \
                .render()


    @expose_for(group.supervisor)
    @web.method.post
    def save(self, **kwargs):

        name = kwargs.get('name')
        person = kwargs.get('person')
        comment = kwargs.get('comment')
        project_id = int(kwargs.get('id', 0))

        with db.session_scope() as session:
            if project_id:
                project = db.Project.get(project_id)
            else:
                project = db.Project()
                session.add(project)

            person = session.query(db.Person).get(person)
            project.name = name
            project.comment = comment
            if person is None:
                raise RuntimeError('Spokesperson not found')


    @expose_for(group.supervisor)
    @web.method.post
    def add_member(self, project_id, member_name, access_level):
        with db.session_scope() as session:
            project = db.Project.get(session, project_id)
            project.add_member(member_name, access_level)

    @expose_for(group.supervisor)
    @web.method.post
    def remove_member(self, project_id, member_name):
        with db.session_scope() as session:
            project = db.Project.get(session, project_id)
            project.remove_member(member_name)





    @expose_for(group.supervisor)
    def delete(self, project_id=None, force=None):

        with db.session_scope() as session:

            if str(force) == 'True':

                project = session.query(db.Project).get(project_id)
                session.delete(project)
                # Returning to project
                raise web.redirect(conf.root_url + '/project')

            else:
                project = session.query(db.Project).get(project_id)
                error = ''
                return web.render('project_delete.html', project=project,
                                 error=error).render()


