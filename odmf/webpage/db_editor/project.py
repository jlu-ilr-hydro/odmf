import cherrypy

from .. import lib as web
from ..auth import group, expose_for

from ... import db


class ProjectPage:
    exposed = True

    @expose_for(group.logger)
    def default(self, project_id=None, error=None):

        with db.session_scope() as session:

            if project_id is not None and str(project_id).isdigit():
                project_from_id = session.query(db.Project).get(project_id)

                if project_from_id is None:

                    error = 'Warning: There was an error with the id \'%s\'. ' \
                            'Please choose a project out of the ' \
                            'list!' % project_id
                    res = self.render_projects(session, error)

                else:
                    persons = session.query(db.Person)
                    persons = persons.filter(db.Person.access_level > 3)

                    error = ''

                    res = web.render('project_from_id.html',
                                     project=project_from_id,
                                     persons=persons, error=error) \
                        .render('html', doctype='html')
            elif project_id is None:

                res = self.render_projects(session, error)

            else:
                res = self.render_projects(session)

            return res

    @expose_for(group.supervisor)
    def add(self, error=''):

        with db.session_scope() as session:
            persons = session.query(db.Person)
            persons = persons.filter(db.Person.access_level > 3)

            res = web.render('project_new.html', persons=persons, error=error) \
                .render('html', doctype='html')

            return res

    @expose_for(group.supervisor)
    def save(self, **kwargs):

        name = kwargs.get('name')
        person = kwargs.get('person')
        comment = kwargs.get('comment')

        if name is None or person is None or name is '':
            raise web.HTTPRedirect(
                '/project/add?error=Not all form fields were set')

        with db.session_scope() as session:

            person = session.query(db.Person).get(person)

            if person is None:
                raise RuntimeError(
                    'Server Error. Please contact the Administrator')

            new_project = db.Project(
                name=name, person_responsible=person, comment=comment)

            session.add(new_project)
            session.flush()

            # For the user interface
            persons = session.query(db.Person)
            persons = persons.filter(db.Person.access_level > 3)

            error = ''

            res = web.render('project_from_id.html', project=new_project,
                             persons=persons, error=error).render('html', doctype='html')

        return res

    @expose_for(group.supervisor)
    def change(self, name=None, person=None, comment=None, project_id=None):

        if (project_id is None) or (name is None) or (person is None):
            raise cherrypy.HTTPError(500)

        with db.session_scope() as session:

            if str(project_id).isdigit():

                project = session.query(db.Project).get(project_id)
                person = session.query(db.Person).get(person)

                # Update
                project.name = name
                project.person_responsible = person

                if project.comment is not None:
                    project.comment = comment

                # Render Webpage
                persons = session.query(db.Person)
                persons = persons.filter(db.Person.access_level > 3)

                error = ''

                res = web.render('project_from_id.html', project=project,
                                 persons=persons, error=error).render('html',
                                                                      doctype='html')

            else:

                error = 'There was a problem with the server'

                res = self.render_projects(session, error)

            return res

    @expose_for(group.supervisor)
    def delete(self, project_id=None, force=None):

        session = db.Session()

        if str(force) == 'True':

            project = session.query(db.Project).get(project_id)

            session.delete(project)

            session.commit()
            session.close()

            # Returning to project
            raise web.HTTPRedirect('/project')

        else:
            project = session.query(db.Project).get(project_id)

            error = ''

            res = web.render('project_delete.html', project=project,
                             error=error).render('html', doctype='html')
            session.close()

        return res

    def get_stats(self, project, session=None):

        if session:
            session = db.Session()

        datasets = session.query(db.Dataset.id).filter(
            db.Dataset.project == project.id)

        print(datasets.all())

        return dict(
            dataset=datasets.count(),
            record=session.query(db.Record)
                .filter(db.Record.dataset.in_(datasets.all())).count())

    def render_projects(self, session, error=''):

        session.query(db.Project)

        projects = session.query(db.Project)
        projects = projects.order_by(db.sql.asc(db.Project.id))

        return web.render('projects.html', error=error, projects=projects
                          ).render('html', doctype='html')
