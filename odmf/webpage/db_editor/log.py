import cherrypy

from .. import lib as web
from ..auth import Level, expose_for
from ...config import conf
from ... import db

from datetime import datetime, timedelta


@cherrypy.popargs('logid')
@web.show_in_nav_for(1, 'tags')
class LogPage:

    def filter_logs(self, session, **kwargs):
        sites = web.to_list(kwargs.get('sites[]'), int)
        types = web.to_list(kwargs.get('types[]'))
        fulltext = kwargs.get('fulltext')
        logs = db.sql.select(db.Log)
        if sites:
            logs = logs.where(db.Log._site.in_(sites))
        if types:
            logs = logs.where(db.Log.type.in_(types))
        if fulltext:
            logs = logs.where(db.Log.message.icontains(fulltext))

        log_count = db.count(session, logs)
        return logs, log_count, sites, types, fulltext

    def export(self, session, logs):
        import pandas as pd
        from ...tools.exportdatasets import serve_dataframe
        df = pd.read_sql_query(logs, session.connection(), index_col='id')
        return serve_dataframe(df, 'logs.xlsx', 'id')


    @expose_for(Level.guest)
    @web.method.get
    def index_list(self, **kwargs):
        page = web.conv(int, kwargs.get('page'), 1)
        limit = web.conv(int, kwargs.get('limit'), 20)
        offset = (page - 1) * limit

        with db.session_scope() as session:
            logs, log_count, sites, types, fulltext = self.filter_logs(session, **kwargs)
            logs = logs.order_by(db.Log.time.desc()).limit(limit).offset(offset)

            if 'export' in kwargs:
                return self.export(session, logs)

            pages = log_count // limit + 1


            all_types = db.sql.select(db.Log.type).where(db.Log.type.isnot(None)).distinct()
            all_sites = db.sql.select(db.Site).order_by(db.Site.id)

            return web.render(
                'log-list.html',
                logs=session.scalars(logs),
                types=sorted(session.scalars(all_types)),
                types_selected=types,
                sites=session.scalars(all_sites),
                sites_selected=sites,
                fulltext=fulltext,
                log_count=log_count,
                pages=pages,
                page=page,
                limit=limit,
            ).render()

    @staticmethod
    def save(session, logid, **kwargs):
        log = session.get(db.Log, logid)
        if not log:
            logid=db.newid(db.Log, session)
            log = db.Log(id=logid)
            session.add(log)
            session.flush()
        
        if kwargs.get('date'):
            log.time = web.parsedate(kwargs['date'])
        
        log.message = kwargs.get('message')
        log.user = session.get(db.Person, kwargs.get('user'))
        log.site = session.get(db.Site, kwargs.get('site'))
        log.type = kwargs.get('type')
        return 'Saved log book item', log.id

    @staticmethod
    def remove(session, logid, **kwargs):
        log = session.get(db.Log, logid)
        if log:
            session.delete(log)
            session.commit()
            return f'Removed log {logid}', '.'
        else:
            return None, logid

    @expose_for(Level.guest)
    def index(self, logid=None, **kwargs):
        if cherrypy.request.method == 'GET':
            if not logid:
                return self.index_list(**kwargs)

            with db.session_scope() as session:
                if logid == 'new':
                    log = self.make_new(session, **kwargs)
                else:
                    logid = web.conv(int, logid)
                    log = session.get(db.Log, logid)

                sitelist = session.query(db.Site).order_by(db.sql.asc(db.Site.id))
                personlist = session.query(db.Person).order_by(db.Person.access_level.desc(), db.Person.surname)
                typelist = db.sql.select(db.Log.type).where(db.Log.type.isnot(None)).distinct()

                return web.render(
                    'log.html', actuallog=log,
                    types=sorted(session.scalars(typelist)),
                    sites=sitelist,
                    persons=personlist
                ).render()

        elif cherrypy.request.method == 'POST':
            logid = web.conv(int, logid)
            with db.session_scope() as session:
                if 'save' in kwargs:
                    success, logid = self.save(session, logid, **kwargs)
                elif 'remove' in kwargs:
                    success, logid = self.remove(session, logid, **kwargs)
            raise web.redirect(conf.url('log', logid), success=success)
    
    @staticmethod
    def make_new(session, site=None, type=None, message=None, **kwargs):
        log = db.Log(time=datetime.today())
        user = web.user()
        if user:
            log.user = session.get(db.Person, user)
        if site:
            log.site = session.get(db.Site, int(site))
        if type:
            log.type = type
        if message:
            log.message = message
        log.time = datetime.today()
        return log


    @expose_for(Level.logger)
    @web.mime.json
    @web.method.get
    def json(self, siteid=None, user=None, old=None, until=None, days=None,
             _=None, keywords=None):
        with db.session_scope() as session:

            logs = session.query(db.Log).order_by(db.sql.desc(db.Log.time))

            if siteid:
                if siteid.isdigit():
                    logs = logs.filter_by(_site=int(siteid))
            if user:
                logs = logs.filter_by(_user=user)
            if until:
                until = web.parsedate(until)
                logs = logs.filter(db.Log.time <= until)
            if keywords:
                keywords = keywords.strip().split(" ")
                for keyword in keywords:
                    logs = logs.filter(db.Log.message.like("%%%s%%" % keyword))
            if old:
                old = web.parsedate(old)
                logs = logs.filter(db.Log.time >= old)
            elif days:
                days = int(days)
                if until:
                    old = until - timedelta(days=days)
                else:
                    old = datetime.today() - timedelta(days=days)
                logs = logs.filter(db.Log.time >= old)

            return web.json_out(logs.all())




