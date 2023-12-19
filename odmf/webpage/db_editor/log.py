
from .. import lib as web
from ..auth import group, expose_for
from ...config import conf
from ... import db

from traceback import format_exc as traceback
from datetime import datetime, timedelta


@web.show_in_nav_for(1, 'tags')
class LogPage:

    @expose_for(group.guest)
    def default(self, logid=None, siteid=None, lastlogdate=None, days=None, error=''):
        with db.session_scope() as session:

            if logid == 'new':
                log = db.Log(id=db.newid(db.Log, session),
                             message='<Log Message>', time=datetime.today())
                user = web.user()
                if user:
                    log.user = session.query(db.Person).get(user)
                if siteid:
                    log.site = session.query(db.Site).get(int(siteid))
                log.time = datetime.today()
            elif logid is None:
                log = session.query(db.Log).order_by(
                    db.sql.desc(db.Log.time)).first()
            else:
                try:
                    log = session.query(db.Log).get(int(logid))
                except:
                    error = traceback()
                    log = None
            if lastlogdate:
                until = web.parsedate(lastlogdate)
            else:
                until = datetime.today()
            days = web.conv(int, days, 30)
            loglist = session.query(db.Log).filter(db.Log.time <= until,
                                                   db.Log.time >= until - timedelta(
                                                       days=days)) \
                .order_by(db.sql.desc(db.Log.time))

            sitelist = session.query(db.Site).order_by(db.sql.asc(db.Site.id))
            personlist = session.query(db.Person).order_by(db.Person.can_supervise.desc(), db.Person.surname)
            return web.render(
                'log.html', actuallog=log, error=error, db=db,
                loglist=loglist, sites=sitelist,
                persons=personlist
            ).render()


    @expose_for(group.logger)
    @web.method.post_or_put
    def saveitem(self, **kwargs):
        try:
            id = web.conv(int, kwargs.get('id'), '')
        except:
            raise web.redirect('./', error=str(kwargs)).render()
        if 'save' in kwargs:
            with db.session_scope() as session:
                try:
                    log = session.query(db.Log).get(id)
                    if not log:
                        log = db.Log(id=id)
                    if kwargs.get('date'):
                        log.time = web.parsedate(kwargs['date'])
                    log.message = kwargs.get('message')
                    log.user = session.query(db.Person).get(kwargs.get('user'))
                    log.site = session.query(db.Site).get(kwargs.get('site'))
                except:
                    raise web.redirect(conf.root_url + '/log/' + str(id),
                                      error=('\n'.join('%s: %s' % it for it in kwargs.items())) + '\n' + traceback(),
                                      title='Log #%s' % id
                                      ).render()
        elif 'new' in kwargs:
            id = 'new'
        raise web.redirect(conf.root_url + '/log/' + str(id))

    @expose_for(group.supervisor)
    @web.method.post_or_put
    def remove(self, id):
        with db.session_scope() as session:
            log = session.query(db.Log).get(id)
            if log:
                session.delete(log)
                session.commit()
            raise web.redirect('.')

    @expose_for(group.logger)
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


    @expose_for(group.logger)
    @web.mime.html
    def fromclipboard(self, paste):
        lines = paste.splitlines()
        class LogFromClipboardError(RuntimeError):
            def __init__(self, line, errormsg):
                super().__init__(f"Could not create log from:\n{line}\nReason:{errormsg}")

        with db.session_scope() as session:


            def parseline(line):
                line = line.replace('\t', '|')
                ls = line.split('|')
                if len(ls) < 2:
                    raise LogFromClipboardError(
                        line, "At least a message and a siteid, seperated by a tab or | are needed to create a log")
                msg = ls[0]
                try:
                    siteid = int(ls[1])
                    site = session.query(db.Site).get(siteid)
                    if not site:
                        raise ValueError()
                except (TypeError, ValueError):
                    raise LogFromClipboardError(line, "%s is not a site id" % ls[1])
                if len(ls) > 2:
                    date = web.parsedate(ls[2])
                else:
                    date = datetime.today()
                if len(ls) > 3:
                    user = session.query(db.Person).get(ls[3])
                    if not user:
                        raise LogFromClipboardError(
                            line, f"Username {ls[3]} is not in the database")
                else:
                    user = session.query(db.Person).get(web.user())
                logid = db.newid(db.Log, session)
                return db.Log(id=logid, site=site, user=user, success=msg, time=date)

            errors = []
            logs = []
            for l in lines:
                try:
                    log = parseline(l)
                    logs.append(log)
                except Exception as e:
                    errors.append(str(e))
            if errors:
                res = 'Import logs from Clipboard failed with the following errors:<ol>'
                li = ''.join('<li>%s</li>' % e for e in errors)
                return res + li + '</ol>'
            else:
                session.add_all(logs)
