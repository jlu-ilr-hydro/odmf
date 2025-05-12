import cherrypy

from ...config import conf
from .. import lib as web
from ..auth import users, Level, expose_for

from ... import db

from datetime import datetime, timedelta

@cherrypy.popargs('jobid')
@web.show_in_nav_for(1, 'tasks')
class JobPage:

    def can_edit(self, job: db.Job):
        return job._responsible == web.user() or job._author == web.user() or Level.my() >= Level.admin


    def index_post(self, jobid, **kwargs):
        """Save a job with new properties. Called by index POST"""
        error = msg = ''
        with db. session_scope() as session:
            job = session.get(db.Job, web.conv(int, jobid))
            if not job:
                job = db.Job(_author=web.user())
                session.add(job)
                session.flush()
            elif not self.can_edit(job):
                error = 'Only author and responsible person can edit a job'
                raise web.redirect(conf.url('job', job.id), error=error)
            elif kwargs.get('save') == 'delete':
                session.delete(job)
                session.commit()
                raise web.redirect(conf.url('job'))

            if kwargs.get('due'):
                job.due = web.parsedate(kwargs['due'])
            if job.due is None:
                raise web.redirect(conf.url('job', jobid), error='No due date')
            job.name = kwargs.get('name')
            job.description = kwargs.get('description')
            job.responsible = session.query(
                db.Person).get(kwargs.get('responsible'))
            job.link = kwargs.get('link')
            job.duration = web.conv(int, kwargs.get('duration'))
            job.repeat = web.conv(int, kwargs.get('repeat'))
            job.type = kwargs.get('type')

            reminder = web.to_list(kwargs.get('reminder[]'))
            topics = web.to_list(kwargs.get('topics[]'))
            msgwhen = web.to_list(kwargs.get('msgdates[]'))
            if any((reminder, topics, msgwhen)):
                job.mailer = {
                    'topics': topics or None,
                    'when': [web.conv(int, s, s) for s in msgwhen] or None,
                    'reminder': reminder or None
                }
            else:
                job.mailer = None

            logsites = web.to_list(kwargs.get('sites[]'))
            if any((logsites, kwargs.get('logmsg'))):
                job.log = {
                    'sites': [web.conv(int, sid) for sid in logsites] or None,
                    'message' : kwargs.get('logmsg')
                }
            else:
                job.log = None

            if kwargs['save'] == 'own':
                p_user = session.get(db.Person, web.user())
                job.author = p_user
                msg = f'{job.name} is now yours'

            elif kwargs['save'] == 'done':
                job.make_done(users.current.name)
                msg = f'{job} is done'
                redirect = conf.url('job')
            elif kwargs['save'] == 'send':
                cherrypy.session['new-message'] = job.as_message(web.user()).__jdict__()
                msg = f'{job} sents new message'
                redirect = conf.url('message')
            else:
                msg = f'{job} saved'
                redirect = conf.url('job', job.id)


        raise web.redirect(redirect, error=error, success=msg)


    @expose_for(Level.logger)
    def index_get(self, jobid, error=None, success=None, copy=None):
        """Shows a single job, called by self.index"""
        with db.session_scope() as session:
            if jobid == 'new':
                author = session.get(db.Person, web.user())
                job = db.Job(id=db.newid(db.Job, session),
                             name='name of new job', author=author, _author=author.username)
                oldjob = session.query(db.Job).get(copy)
                if oldjob:
                    job.log = oldjob.log
                    job.description = oldjob.description
                    job.name = oldjob.name
                    job.type = oldjob.type
                    job.duration = oldjob.duration
                    job.repeat = oldjob.repeat
                    job.responsible = oldjob.responsible
                    job.link = oldjob.link
                    job.mailer = oldjob.mailer

                session.flush()
            else:
                job = session.get(db.Job, web.conv(int, jobid))
                if not job:
                    raise web.redirect(conf.url('job'), error=f'Job {jobid} not found')

            return web.render(
                'job.html', job=job, can_edit=self.can_edit(job),
                error=error, success=success, db=db,
                me=session.get(db.Person, web.user()),
                username=users.current, now=datetime.now(),
                persons=session.query(db.Person).order_by(db.Person.can_supervise.desc(), db.Person.surname).all(),
                jobtypes=session.query(db.Job.type).order_by(db.Job.type).distinct().all(),
                my_jobs=session.query(db.Job).filter(db.Job._responsible == web.user(), ~db.Job.done).order_by(db.Job.due).all(),
                my_jobs_author=session.query(db.Job).filter(db.Job._author == web.user(), ~db.Job.done).order_by(db.Job.due).all(),
                sites=session.query(db.Site).order_by(db.Site.name),
                topics=session.scalars(db.sql.select(db.message.Topic)).all()
            ).render()

    def list_jobs(self, **kwargs):
        """Renders the job-list.html pagge"""
        with db.session_scope() as session:
            jobtypes=session.query(db.Job.type).order_by(db.Job.type).where(db.Job.type.isnot(None)).distinct()
            persons = set()
            sites = set()
            for j in session.query(db.Job):
                persons.update((j.responsible, j.author))
                if j.log and j.log.get('sites'):
                    sites.update(j.log.get('sites') )
            persons -= {None}
            sites = session.query(db.Site).filter(db.Site.id.in_(sites)).order_by(db.Site.id)
            return web.render(
                'job-list.html',
                jobtypes=sorted(jobtypes),
                persons=sorted(persons),
                sites=sites,
                topics=session.scalars(db.sql.select(db.message.Topic)).all(),
            ).render()


    @expose_for(Level.logger)
    def index(self, jobid=None, error=None, success=None, **kwargs):
        if cherrypy.request.method == 'GET':
            if jobid:
                return self.index_get(jobid, error, success, copy=kwargs.get('copy'))
            else:
                return self.list_jobs()
        elif cherrypy.request.method == 'POST':
            return self.index_post(jobid, **kwargs)
        else:
            raise web.HTTPError(405, message='Method not allowed')

    @expose_for(Level.logger)
    @web.method.post
    def done(self, jobid, time=None):
        with db.session_scope() as session:
            job = session.get(db.Job, int(jobid))
            if time:
                time = web.parsedate(time)
            return job.make_done(users.current.name, time)

    @expose_for(Level.logger)
    @web.method.post
    def comment(self, jobid, text: str):
        if len(text)>10:
            with db.session_scope() as session:
                job = session.get(db.Job, int(jobid))
                comment = db.job.JobComment(job=job, _user=web.user(), text=text, date=datetime.now())
                session.add(comment)
            raise web.redirect(conf.url('job', jobid), success=f'Comment added')
        else:
            raise web.redirect(conf.url('job', jobid), error=f'Comment to short')



    @expose_for(Level.logger)
    @web.mime.json
    def json(self, start=None, end=None, persons=None, types=None, sites=None, onlyactive=False, fulltext=None, topics=None, **kwargs):
        """Returns the filtered jobs as fullcalendar events"""
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
                jobs = jobs.filter(db.sql.not_(db.Job.done))
            if fulltext:
                jobs = jobs.filter(
                    db.sql.or_(
                        db.Job.name.icontains(fulltext),
                        db.Job.description.icontains(fulltext)
                    )
                )
            jobs = jobs.all()
            if sites:
                sites = set(int(s) for s in sites.split(','))
                jobs = [j for j in jobs if sites & set(db.flex_get(j.log, 'sites', default=[]))]
            if topics:
                topics = set(s for s in topics.split(','))
                jobs = [j for j in jobs if topics & set(db.flex_get(j.mailer,'topics', default=[]))]

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


