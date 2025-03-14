import cherrypy

from .. import lib as web
from ..auth import Level, expose_for
from ...config import conf
from ... import db

from traceback import format_exc as traceback
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

    @expose_for(Level.guest)
    def index(self, logid=None, error='', **kwargs):
        if cherrypy.request.method == 'GET':
            if not logid:
                return self.index_list(**kwargs)

        with db.session_scope() as session:
            log = None
            if logid is not None:
                try:
                    log = session.get(db.Log, int(logid))
                except:
                    error = traceback()
            sitelist = session.query(db.Site).order_by(db.sql.asc(db.Site.id))
            personlist = session.query(db.Person).order_by(db.Person.can_supervise.desc(), db.Person.surname)
            typelist = db.sql.select(db.Log.type).where(db.Log.type.isnot(None)).distinct()

            return web.render(
                'log.html', actuallog=log, error=error,
                types=sorted(session.scalars(typelist)),
                sites=sitelist,
                persons=personlist
            ).render()

    @expose_for(Level.logger)
    @web.method.get
    def new(self, siteid=None, type=None, message=None):
        with db.session_scope() as session:
            log = db.Log(id=db.newid(db.Log, session),
                         message='<Log Message>', time=datetime.today())
            user = web.user()
            if user:
                log.user = session.get(db.Person, user)
            if siteid:
                log.site = session.get(db.Site, int(siteid))
            if type:
                log.type = type
            if message:
                log.message = message
            log.time = datetime.today()
            sitelist = session.query(db.Site).order_by(db.sql.asc(db.Site.id))
            personlist = session.query(db.Person).order_by(db.Person.can_supervise.desc(), db.Person.surname)
            typelist = session.scalars(db.sql.select(db.Log.type).distinct())
            return web.render(
                'log.html', actuallog=log,
                types=typelist,
                sites=sitelist,
                persons=personlist
            ).render()


    @expose_for(Level.logger)
    @web.method.post_or_put
    def saveitem(self, **kwargs):
        try:
            id = web.conv(int, kwargs.get('id'), '')
        except:
            raise web.redirect('./', error=str(kwargs)).render()
        if 'save' in kwargs:
            with db.session_scope() as session:
                try:
                    log = session.get(db.Log, id)
                    if not log:
                        log = db.Log(id=id)
                        session.add(log)
                        session.flush()
                    if kwargs.get('date'):
                        log.time = web.parsedate(kwargs['date'])
                    log.message = kwargs.get('message')
                    log.user = session.get(db.Person, kwargs.get('user'))
                    log.site = session.get(db.Site, kwargs.get('site'))
                    log.type = kwargs.get('type')
                except:
                    raise web.redirect(
                        conf.root_url + '/log/' + str(id),
                        error=('\n'.join('%s: %s' % it for it in kwargs.items())) + '\n' + traceback(),
                        title='Log #%s' % id
                    )
        elif 'new' in kwargs:
            id = 'new'
        raise web.redirect(conf.root_url + '/log/' + str(id))

    @expose_for(Level.supervisor)
    @web.method.post_or_put
    def remove(self, id):
        with db.session_scope() as session:
            log = session.get(db.Log, id)
            if log:
                session.delete(log)
                session.commit()
            raise web.redirect('.')

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
                # TODO: Implement pgsql full text search
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



    @expose_for()
    @web.mime.json
    def data(self, siteid=None, user=None, old=None, until=None, days=None,
             _=None):

        with db.session_scope() as session:

            logs = session.query(db.Log, db.Person)\
                .filter(db.Log._user== db.Person.username)

            if until:
                until = web.parsedate(until)
                logs = logs.filter(db.Log.time <= until)

            return web.json_out(logs.all())




