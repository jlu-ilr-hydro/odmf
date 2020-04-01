
from .. import lib as web
from ..auth import users, group, expose_for

from ... import db

from traceback import format_exc as traceback
from datetime import datetime


@web.show_in_nav_for(1, 'tasks')
class JobPage:

    @expose_for(group.logger)
    def default(self, jobid=None, user=None, onlyactive='active'):
        session = db.Session()
        error = ''
        if user is None:
            user = web.user()
        if jobid == 'new':
            author = session.query(db.Person).get(web.user())
            job = db.Job(id=db.newid(db.Job, session),
                         name='name of new job', author=author)
            if user:
                p_user = session.query(db.Person).get(user)
                job.responsible = p_user
                job.due = datetime.now()

        elif jobid is None:
            job = session.query(db.Job).filter_by(
                _responsible=web.user(), done=False).order_by(db.Job.due).first()
        else:
            try:
                job = session.query(db.Job).get(int(jobid))
            except:
                error = traceback()
                job = None
        queries = dict(
            persons=session.query(db.Person).order_by(db.Person.can_supervise.desc(), db.Person.surname).all(),
            jobtypes=session.query(db.Job.type).order_by(db.Job.type).distinct().all(),
        )

        jobs = session.query(db.Job).order_by(db.Job.done, db.Job.due.desc())
        if user != 'all':
            jobs = jobs.filter(db.Job._responsible == user)
        if onlyactive:
            jobs = jobs.filter(not db.Job.done)
        result = web.render('job.html', jobs=jobs, job=job, error=error, db=db,
                            username=user, onlyactive=onlyactive, **queries
                            ).render()
        session.close()
        return result

    @expose_for(group.logger)
    def done(self, jobid, time=None):
        session = db.Session()
        job = session.query(db.Job).get(int(jobid))
        if time:
            time = web.parsedate(time)
        msg = job.make_done(users.current.name, time)

        session.commit()
        session.close()
        return msg

    @expose_for(group.editor)
    def saveitem(self, **kwargs):
        try:
            id = web.conv(int, kwargs.get('id'), '')
        except:
            return web.render(error=str(kwargs) + '\n' + traceback(), title='Job %s' % kwargs.get('id')
                              ).render()
        if 'save' in kwargs:
            try:
                session = db.Session()
                job = session.query(db.Job).get(id)
                if not job:
                    job = db.Job(id=id, _author=web.user())
                if kwargs.get('due'):
                    job.due = web.parsedate(kwargs['due'])
                job.name = kwargs.get('name')
                job.description = kwargs.get('description')
                job.responsible = session.query(
                    db.Person).get(kwargs.get('responsible'))
                job.link = kwargs.get('link')
                job.repeat = web.conv(int, kwargs.get('repeat'))
                job.type = kwargs.get('type')

                if kwargs['save'] == 'own':
                    p_user = session.query(db.Person).get(web.user())
                    job.author = p_user
                elif kwargs['save'] == 'done':
                    job.make_done(users.current.name)
                session.commit()
                session.close()
            except:
                return web.render(
                    'empty.html',
                    error=('\n'.join('%s: %s' % it for it in kwargs.items())) + '\n' + traceback(),
                    title='Job #%s' % id
                ).render()

    @expose_for(group.logger)
    @web.mime.json
    def json(self, responsible=None, author=None, onlyactive=False, dueafter=None):
        with db.session_scope() as session:

            jobs = session.query(db.Job).order_by(db.Job.done ,db.Job.due.desc())
            if responsible != 'all':
                if not responsible:
                    responsible = users.current.name
                jobs = jobs.filter(db.Job._responsible == responsible)
            if onlyactive:
                jobs = jobs.filter(~db.Job.done)
            if author:
                jobs = jobs.filter(db.Job.author == author)
            try:
                jobs = jobs.filter(db.Job.due > web.parsedate(dueafter))
            except:
                pass
            return web.json_out(jobs.all())

