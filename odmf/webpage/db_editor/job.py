import cherrypy

from ...config import conf
from .. import lib as web
from ..auth import users, Level, expose_for

from ... import db

from traceback import format_exc as traceback
from datetime import datetime, timedelta

@cherrypy.popargs('jobid')
@web.show_in_nav_for(1, 'tasks')
class JobPage:

    def can_edit(self, job: db.Job):
        return job._responsible == web.user() or job._author == web.user()


    def save_job(self, jobid, **kwargs):
        """Save a job with new properties. Called by index POST"""
        error = msg = ''
        try:
            id = web.conv(int, kwargs.get('id'), '')
        except (TypeError, ValueError):
            error = 'The job id is not a number'
        else:
            with db. session_scope() as session:
                job = session.get(db.Job, id)
                if not job:
                    job = db.Job(id=id, _author=web.user())
                    session.add(job)
                    session.flush()
                    jobid=job.id
                elif not self.can_edit(job):
                    error = 'Only author and responsible person can edit a job'
                    raise web.redirect(conf.url('job', job.id, error=error))

                if kwargs.get('due'):
                    job.due = web.parsedate(kwargs['due'])
                if job.due is None:
                    raise web.redirect(conf.url('job', jobid, error='No due date'))
                job.name = kwargs.get('name')
                job.description = kwargs.get('description')
                job.responsible = session.query(
                    db.Person).get(kwargs.get('responsible'))
                job.link = kwargs.get('link')
                job.duration = web.conv(int, kwargs.get('duration'))
                job.repeat = web.conv(int, kwargs.get('repeat'))
                job.type = kwargs.get('type')

                if kwargs['save'] == 'own':
                    p_user = session.get(db.Person, web.user())
                    job.author = p_user
                    msg = f'{job.name} is now yours'
                elif kwargs['save'] == 'done':
                    job.make_done(users.current.name)
                    msg = f'{job} is done'
                else:
                    msg = f'{job} saved'

                if logsites:=kwargs.get('sites[]'):
                    if not job.log:
                        job.log = dict()
                    job.log |= {'sites': [web.conv(int, sid) for sid in logsites]}
                    job.log['message'] = kwargs.get('logmsg')
                elif job.log and 'sites' in job.data:
                    job.log = None




        raise web.redirect(conf.url('job', jobid, error=error, success=msg))


    @expose_for(Level.logger)
    def show_job(self, jobid, error=None, success=None):
        """Shows a single job, called by self.index"""
        with db.session_scope() as session:
            if jobid == 'new':
                author = session.get(db.Person, web.user())
                job = db.Job(id=db.newid(db.Job, session),
                             name='name of new job', author=author, _author=author.username)
                session.flush()
            else:
                job = session.get(db.Job, web.conv(int, jobid))
                if not job:
                    raise web.redirect(conf.url('job', error=f'Job {jobid} not found'))

            return web.render(
                'job.html', job=job, can_edit=self.can_edit(job),
                error=error, success=success, db=db,
                username=users.current, now=datetime.now(),
                persons=session.query(db.Person).order_by(db.Person.can_supervise.desc(), db.Person.surname).all(),
                jobtypes=session.query(db.Job.type).order_by(db.Job.type).distinct().all(),
                my_jobs=session.query(db.Job).filter(db.Job._responsible == web.user(), ~db.Job.done).order_by(db.Job.due).all(),
                my_jobs_author=session.query(db.Job).filter(db.Job._author == web.user(), ~db.Job.done).order_by(db.Job.due).all(),
                sites=session.query(db.Site).order_by(db.Site.name),
            ).render()

    def list_jobs(self, **kwargs):
        with db.session_scope() as session:
            jobtypes=session.query(db.Job.type).order_by(db.Job.type).distinct()
            persons = sorted(set([j.responsible for j in session.query(db.Job) if j.responsible] + [j.author for j in session.query(db.Job) if j.author]))

            return web.render('job-list.html', jobtypes=jobtypes, persons=persons).render()


    @expose_for(Level.logger)
    def index(self, jobid=None, error=None, success=None, **kwargs):
        if cherrypy.request.method == 'GET':
            if jobid:
                return self.show_job(jobid, error, success)
            else:
                return self.list_jobs()
        if cherrypy.request.method == 'POST':
            return self.save_job(jobid, **kwargs)


    @expose_for(Level.logger)
    @web.method.post
    def done(self, jobid, time=None):
        with db.session_scope() as session:
            job = session.get(db.Job, int(jobid))
            if time:
                time = web.parsedate(time)
            return job.make_done(users.current.name, time)


    @expose_for(Level.logger)
    @web.mime.json
    def json(self, persons=None, types=None, onlyactive=False,  start=None, end=None):
        with db.session_scope() as session:
            jobs = session.query(db.Job)
            if start:
                start = web.parsedate(start)
                jobs = jobs.filter(db.Job.due >= start)
            if end:
                end = web.parsedate(end)
                jobs = jobs.filter(db.Job.due <= end)
            if persons:
                persons = persons.split(',')
                jobs = jobs.filter(db.sql.or_(db.Job._responsible.in_(persons), db.Job._author.in_(persons)))
            if types:
                types = types.split(',')
                jobs = jobs.filter(db.sql.or_(db.Job.type.in_(types)))

            if onlyactive == 'true':
                jobs = jobs.filter(~db.Job.done)

            events = [self.as_event(job) for job in jobs]
            return web.json_out(events)


    @staticmethod
    def as_event(job: db.Job):
        event = {
            'id': f'job:{job.id}',
            'allDay': True,
            'start': job.due.isoformat(),
            'end': (job.due + timedelta(days=(job.duration or 0))).isoformat(),
            'title': f'{job.type}: {job.name}',
            'url': conf.url('job', job.id)
        }
        if job.done:
            event['className'] = 'text-success alert-success'
        elif job.is_due():
            event['className'] = 'text-white bg-danger'


        return event


