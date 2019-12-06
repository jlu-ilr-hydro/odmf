
from .. import lib as web
from ..auth import expose_for

from ... import db
from datetime import datetime, timedelta


class CalendarPage(object):

    exposed = True

    @expose_for()
    def index(self, **kwargs):
        return web.render('calendar.html').render()

    @expose_for()
    @web.mime.json
    def jobs_json(self, start=None, end=None, responsible=None, author=None, onlyactive=False, dueafter=None):
        with db.session_scope() as session:
            jobs = session.query(db.Job).order_by(db.Job.done, db.Job.due.desc())
            if responsible != 'all':
                if not responsible:
                    responsible = web.user()
                jobs = jobs.filter(db.Job._responsible == responsible)
            if onlyactive:
                jobs = jobs.filter(~db.Job.done)
            if author:
                jobs = jobs.filter(db.Job.author == author)
            try:
                jobs = jobs.filter(db.Job.due > web.parsedate(dueafter))
            except:
                pass
            events = [dict(id=j.id,
                           url='/job/%i' % j.id,
                           title=str(j),
                           start=j.due,
                           end=j.done if j.done else j.due,
                           color='#AAA' if j.done else '',
                           allDay=True) for j in jobs]
            return web.json_out(events)


    @expose_for()
    @web.mime.json
    def logs_json(self, start=None, end=None, site=None, type=None):
        with db.session_scope() as session:

            logs = session.query(db.Log).order_by(db.Log.time)
            if start:
                logs = logs.filter(db.Log.time >= datetime(
                    1970, 1, 1, 1) + timedelta(seconds=int(start)))
            if end:
                logs = logs.filter(db.Log.time <= datetime(
                    1970, 1, 1, 1) + timedelta(seconds=int(end)))
            if site:
                logs = logs.filter_by(_site=int(site))
            if type:
                logs = logs.filter_by(type=type)
            events = [dict(id=l.id,
                           url='/log/%i' % l.id,
                           title=str(l),
                           start=l.time,
                           end=l.time + timedelta(hours=1),
                           allDay=False) for l in logs]
            return web.json_out(events)
