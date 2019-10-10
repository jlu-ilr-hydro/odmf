# -*- coding: utf-8 -*-
import cherrypy

from . import lib as web
from .auth import users, group, expose_for, hashpw, is_self, get_levels
from .upload import write_to_file

from .. import db
import sys
import os
from traceback import format_exc as traceback
from datetime import datetime, timedelta

from .upload import DownloadPage
from .map import MapPage
from .site import SitePage
from .datasetpage import DatasetPage
from .preferences import Preferences
from .plot import PlotPage



MEDIA_PATH = {
    'logo': '/media/schwingbachlogo.png',
    'banner-left': '/media/navigation-background.jpg'
}


class PersonPage:
    exposed = True

    @expose_for(group.guest)
    def default(self, act_user=None):
        session = db.Session()
        persons = session.query(db.Person).order_by(
            db.sql.desc(db.Person.can_supervise), db.Person.surname)

        # 'guest' user can't see himself in the user list
        if users.current.name == 'guest':
            persons = persons.filter(db.Person.access_level != 0)
            # TODO: url "host/guest" shouldn't be accessible for the guest user

        supervisors = persons.filter(db.Person.can_supervise == True)
        error = ''
        jobs = []
        act_user = act_user or users.current.name
        if act_user == 'new':
            p_act = db.Person(active=True)
        else:
            try:
                p_act = session.query(db.Person).get(act_user)
                if p_act is None:
                    raise ValueError(
                        "There is no user with the name '%s'" % act_user)
                jobs = p_act.jobs.order_by(db.sql.asc(
                    db.Job.done), db.sql.asc(db.Job.due))
            except:
                p_act = session.query(db.Person).get(users.current.name)
                error = traceback()
        result = web.render('person.html', persons=persons, active_person=p_act, supervisors=supervisors, error=error,
                            jobs=jobs, act_user=act_user, levels=get_levels, is_self=is_self)\
            .render('html', doctype='html')
        session.close()
        return result

    @expose_for(group.supervisor)
    def saveitem(self, **kwargs):
        username = kwargs.get('username')
        if 'save' in kwargs and username:
            session = db.Session()
            p_act = session.query(db.Person).filter_by(
                username=username).first()
            if not p_act:
                p_act = db.Person(username=username)
                session.add(p_act)
            p_act.email = kwargs.get('email')
            p_act.firstname = kwargs.get('firstname')
            p_act.surname = kwargs.get('surname')
            p_act.supervisor = session.query(
                db.Person).get(kwargs.get('supervisor'))
            # p_act.can_supervise=kwargs.get('can_supervise')
            p_act.car_available = kwargs.get('car_available')
            p_act.telephone = kwargs.get('telephone')
            p_act.mobile = kwargs.get('mobile')
            p_act.comment = kwargs.get('comment')
            if kwargs.get('status') == 'on':
                p_act.active = True
            else:
                p_act.active = False

            # Simple Validation
            if kwargs.get('password') is not None:
                if kwargs.get('password') == kwargs.get('password_verify'):
                    p_act.password = hashpw(kwargs.get('password'))
            # Simple Validation
            # if users.current.level == ACCESS_LEVELS['Supervisor']:
            p_act.access_level = int(kwargs.get('access_level'))

            session.commit()
            session.close()
        raise web.HTTPRedirect('./' + username)

    @expose_for()
    def json(self, supervisors=False):
        session = db.Session()
        web.setmime('application/json')
        persons = session.query(db.Person).order_by(
            db.sql.desc(db.Person.can_supervise), db.Person.surname)
        if supervisors:
            persons = persons.filter(db.Person.can_supervise == True)
        res = web.as_json(persons.all())
        session.close()
        return res

    @expose_for(group.logger)
    def changepassword(self, username=None):
        """
        Form request
        """
        session = db.Session()
        changing_user_level = session.query(db.Person).filter(
            db.Person.username == username).first().access_level

        # cast from unicode to int
        changing_user_level = int(changing_user_level)

        if changing_user_level > users.current.level:
            raise cherrypy.HTTPRedirect(
                "/login?error=You are missing privileges to do what you liked to do.&frompage=" + cherrypy.request.path_info)
        else:
            error = ''
            result = web.render('passwordchange.html',
                                error=error, username=username).render('html', doctype='html')

        session.close()

        return result

    @expose_for(group.logger)
    def savepassword(self, **kwargs):
        """
        Save to database
        """
        password = kwargs.get('password')
        password_repeat = kwargs.get('password_repeat')
        username = kwargs.get('username')

        if password is None or password_repeat is None or username is None:
            raise IOError

        # if password != password_repeat:
        #    error = 'Error: Password don\'t match'
        #    result = web.render('passwordchange.html', error=error, username=username)\
        #        .render('html', doctype='html')

        # Password encryption and db saving
        session = db.Session()

        p_act = session.query(db.Person).filter_by(username=username).first()
        p_act.password = hashpw(password)

        session.commit()
        session.close()

        raise web.HTTPRedirect('./' + username)


class VTPage:
    exposed = True

    @expose_for(group.guest)
    def default(self, vt_id='new'):
        session = db.Session()
        valuetypes = session.query(
            db.ValueType).order_by(db.ValueType.id).all()
        error = ''
        if vt_id == 'new':
            id = db.newid(db.ValueType, session)
            vt = db.ValueType(id=id,
                              name='<Name>')
        else:
            try:
                vt = session.query(db.ValueType).get(int(vt_id))
                # image=b64encode(self.sitemap.draw([actualsite]))
            except:
                error = traceback()
                # image=b64encode(self.sitemap.draw(sites.all()))
                vt = None

        result = web.render('valuetype.html', valuetypes=valuetypes,
                            actualvaluetype=vt, error=error).render('html', doctype='html')
        session.close()
        return result

    @expose_for(group.supervisor)
    def saveitem(self, **kwargs):
        try:
            id = web.conv(int, kwargs.get('id'), '')
        except:
            return web.render(error=traceback(), title='valuetype #%s' % kwargs.get('id'))
        if 'save' in kwargs:
            try:
                session = db.Session()
                vt = session.query(db.ValueType).get(int(id))
                if not vt:
                    vt = db.ValueType(id=id)
                    session.add(vt)
                vt.name = kwargs.get('name')
                vt.unit = kwargs.get('unit')
                vt.minvalue = web.conv(float, kwargs.get('minvalue'))
                vt.maxvalue = web.conv(float, kwargs.get('maxvalue'))
                vt.comment = kwargs.get('comment')
                session.commit()
                session.close()
            except:
                return web.render('empty.html', error=traceback(), title='valuetype #%s' % id
                                  ).render('html', doctype='html')
        raise web.HTTPRedirect('./%s' % id)

    @expose_for(group.guest)
    def json(self):
        session = db.Session()
        web.setmime('application/json')
        dump = web.as_json(session.query(db.ValueType).all())
        session.close()
        return dump


class DatasourcePage:
    exposed = True

    @expose_for(group.guest)
    def default(self, id='new'):
        session = db.Session()
        instruments = session.query(db.Datasource).order_by(db.Datasource.id)
        error = ''
        if id == 'new':
            newid = db.newid(db.Datasource, session)
            inst = db.Datasource(id=newid,
                                 name='<Name>')
        else:
            try:
                inst = session.query(db.Datasource).get(int(id))
            except:
                error = traceback()
                inst = None

        result = web.render('instrument.html', instruments=instruments,
                            actualinstrument=inst, error=error).render('html', doctype='html')
        session.close()
        return result

    @expose_for(group.editor)
    def saveitem(self, **kwargs):
        try:
            id = web.conv(int, kwargs.get('id'), '')
        except:
            return web.render(error=traceback(), title='Datasource #%s' % kwargs.get('id'))
        if 'save' in kwargs:
            try:
                session = db.Session()
                inst = session.query(db.Datasource).get(int(id))
                if not inst:
                    inst = db.Datasource(id=id)
                    session.add(inst)
                inst.name = kwargs.get('name')
                inst.sourcetype = kwargs.get('sourcetype')
                inst.comment = kwargs.get('comment')
                inst.manuallink = kwargs.get('manuallink')
                session.commit()
                session.close()
            except:
                return web.render('empty.html', error=traceback(), title='valuetype #%s' % id
                                  ).render('html', doctype='html')
        raise web.HTTPRedirect('./%s' % id)

    @expose_for()
    def json(self):
        session = db.Session()
        web.setmime('application/json')
        dump = web.as_json(session.query(db.Datasource).all())
        session.close()
        return dump


class JobPage:
    exposed = True

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
            jobs = jobs.filter(~db.Job.done)
        result = web.render('job.html', jobs=jobs, job=job, error=error, db=db,
                            username=user, onlyactive=onlyactive, **queries
                            ).render('html', doctype='html')
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
                              ).render('html', doctype='html')
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
                return web.render('empty.html', error=('\n'.join('%s: %s' % it for it in kwargs.items())) + '\n' + traceback(),
                                  title='Job #%s' % id
                                  ).render('html', doctype='html')

    @expose_for(group.logger)
    def json(self, responsible=None, author=None, onlyactive=False, dueafter=None):
        session = db.Session()
        jobs = session.query(db.Job).order_by(db.Job.done ,db.Job.due.desc())
        web.setmime(web.mime.json)
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
        res = web.as_json(jobs.all())
        session.close()
        return res


class LogPage:
    exposed = True

    @expose_for(group.guest)
    def default(self, logid=None, siteid=None, lastlogdate=None, days=None):
        session = db.Session()
        error = ''
        queries = dict(
            persons=session.query(db.Person).order_by(db.Person.can_supervise.desc(), db.Person.surname).all(),
        )

        if logid == 'new':
            log = db.Log(id=db.newid(db.Log, session),
                         message='<Log-Beschreibung>', time=datetime.today())
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
                                                   days=days))\
            .order_by(db.sql.desc(db.Log.time))

        sitelist = session.query(db.Site).order_by(db.sql.asc(db.Site.id))

        result = web.render('log.html', actuallog=log, error=error, db=db,
                            loglist=loglist, sites=sitelist, **queries
                            ).render('html', doctype='html')

        session.close()
        return result

    @expose_for(group.logger)
    def saveitem(self, **kwargs):
        try:
            id = web.conv(int, kwargs.get('id'), '')
        except:
            return web.render(error=str(kwargs) + '\n' + traceback(), title='Job %s' % kwargs.get('id')
                              ).render('html', doctype='html')
        if 'save' in kwargs:
            try:
                session = db.Session()
                log = session.query(db.Log).get(id)
                if not log:
                    log = db.Log(id=id)
                if kwargs.get('date'):
                    log.time = datetime.strptime(kwargs['date'], '%d.%m.%Y')
                log.message = kwargs.get('message')
                log.user = session.query(db.Person).get(kwargs.get('user'))
                log.site = session.query(db.Site).get(kwargs.get('site'))
                session.commit()
                session.close()
            except:
                return web.render('empty.html', error=('\n'.join('%s: %s' % it for it in kwargs.items())) + '\n' + traceback(),
                                  title='Log #%s' % id
                                  ).render('html', doctype='html')
        elif 'new' in kwargs:
            id = 'new'
        raise web.HTTPRedirect('./%s' % id)

    @expose_for(group.supervisor)
    def remove(self, id):
        session = db.Session()
        log = session.query(db.Log).get(id)
        if log:
            session.delete(log)
            session.commit()
        raise web.HTTPRedirect('/log')

    @expose_for(group.logger)
    def json(self, siteid=None, user=None, old=None, until=None, days=None,
             _=None, keywords=None):
        session = db.Session()
        web.setmime('application/json')

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

        res = web.as_json(logs.all())

        print("Res ", res)

        session.close()
        return res

    @expose_for()
    def data(self, siteid=None, user=None, old=None, until=None, days=None,
             _=None):

        session = db.Session()

        web.setmime('application/json')

        logs = session.query(db.Log, db.Person).filter(db.Log._user
                                                       == db.Person.username)

        if until:
            until = web.parsedate(until)
            logs = logs.filter(db.Log.time <= until)

        res = web.as_json(logs.all())

        # logs = logs.values(db.Log.id, db.Log.message, db.Log.time, db.Log._user,
        #            db.Person.email)

        #res = web.log_as_array_str(logs)

        session.close()
        return res

    @expose_for(group.logger)
    def fromclipboard(self, paste):
        web.setmime('text/html')
        lines = paste.splitlines()
        session = db.Session()

        def _raise(line, errormsg):
            raise RuntimeError(
                "Could not create log from:\n'%s'\nReason:%s" % (line, errormsg))

        def parseline(line):
            line = line.replace('\t', '|')
            ls = line.split('|')
            if len(ls) < 2:
                _raise(
                    line, "At least a message and a siteid, seperated by a tab or | are needed to create a log")
            msg = ls[0]
            try:
                siteid = int(ls[1])
                site = session.query(db.Site).get(siteid)
                if not site:
                    raise RuntimeError()
            except:
                _raise(line, "%s is not a site id" % ls[1])
            if len(ls) > 2:
                date = web.parsedate(ls[2])
            else:
                date = datetime.today()
            if len(ls) > 3:
                user = session.query(db.Person).get(ls[3])
                if not user:
                    _raise(line, "Username '%s' is not in the database" %
                           ls[3])
            else:
                user = session.query(db.Person).get(web.user())
            logid = db.newid(db.Log, session)
            return db.Log(id=logid, site=site, user=user, message=msg, time=date)
        errors = []
        logs = []
        for l in lines:
            try:
                log = parseline(l)
                logs.append(log)
            except Exception as e:
                errors.append(e.message)
        if errors:
            res = 'Import logs from Clipboard failed with the following errors:<ol>'
            li = ''.join('<li>%s</li>' % e for e in errors)
            return res + li + '</ol>'
        else:
            session.add_all(logs)
            session.commit()


class HeapyPage(object):
    exposed = True

    def __init__(self, hp):
        self.hp = hp

    @expose_for(group.admin)
    def index(self):
        web.setmime('text/plain')
        h = self.hp.heap()
        return str(h).encode('utf-8')


class PicturePage(object):
    """
    Displaying all images and providing image/thumbnail

    See memoryview doc for python3 tobytes
    """
    exposed = True

    @expose_for()
    def image(self, id):
        with db.session_scope() as session:
            img = db.Image.get(session, int(id))

            if img:
                web.setmime(img.mime)
                res = img.image
                return res
            else:
                raise cherrypy.HTTPError(404)

    @expose_for()
    def thumbnail(self, id):
        with db.session_scope() as session:
            img = db.Image.get(session, int(id))

            if img:
                web.setmime(img.mime)
                res = img.thumbnail
                return res
            else:
                raise cherrypy.HTTPError(404)

    @expose_for()
    def imagelist_json(self, site=None, by=None):
        session = db.Session()
        imagelist = session.query(db.Image).order_by(
            db.Image._site, db.Image.time)
        if site:
            imagelist.filter(db.Image._site == site)
        if by:
            imagelist.filter(db.Image._by == by)
        res = web.as_json(imagelist.all())
        session.close()
        return bytearray(res)

    @expose_for()
    def index(self, id='', site='', by=''):
        session = db.Session()
        error = ''
        img = imagelist = None
        if id:
            img = db.Image.get(session, int(id))
            if not img:
                error = "No image with id=%s found" % id
        else:
            imagelist = session.query(db.Image).order_by(
                db.Image._site, db.Image.time)
            if site:
                imagelist = imagelist.filter_by(_site=site)
            if by:
                imagelist = imagelist.filter_by(_by = by)
        res = web.render('picture.html', image=img, error=error,
                         images=imagelist, site=site, by=by).render('html')
        session.close()
        print('Image:Index(%s, %s, %s)' % (id, site, by))
        return res

    @expose_for(group.logger)
    def upload(self, imgfile, siteid, user):
        session = db.Session()
        site = db.Site.get(session, int(siteid)) if siteid else None
        by = db.Person.get(session, user) if user else None
        #io = StringIO()
        # for l in imgfile:
        #    io.write(l)
        # io.seek(0)
        img = db.Image(site=site, by=by, imagefile=imgfile.file)
        session.add(img)
        session.commit()
        imgid = img.id
        session.close()
        raise web.HTTPRedirect('/picture?id=%i' % imgid)


class CalendarPage(object):
    exposed = True

    @expose_for()
    def index(self, **kwargs):
        return web.render('calendar.html').render('html', doctype='html')

    @expose_for()
    def jobs_json(self, start=None, end=None, responsible=None, author=None, onlyactive=False, dueafter=None):
        web.setmime(web.mime.json)
        session = db.Session()
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
        res = web.as_json(events)
        session.close()
        return res

    @expose_for()
    def logs_json(self, start=None, end=None, site=None, type=None):
        web.setmime(web.mime.json)
        session = db.Session()
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
        res = web.as_json(events)
        session.close()
        return res


class Wiki(object):
    exposed = True

    def name2path(self, name):
        return web.abspath('datafiles/wiki/' + name + '.wiki')

    @expose_for()
    def external(self, *args):
        from glob import glob
        args = list(args)
        name = '.'.join(args)
        title = ' / '.join(arg.title() for arg in args)
        filename = self.name2path(name.lower())
        content = ''
        related = ''
        pages = sorted([os.path.basename(s)[:-5]
                        for s in glob(web.abspath('datafiles/wiki/%s*.wiki' % name.split('.')[0]))])
        if name in pages:
            pages.remove(name)
        if os.path.exists(filename):
            content = str(open(filename).read())
        elif args:
            if pages:
                content += '\n\n!!! box "Note:"\n    You can write an introduction to this topic with the edit button above.\n'
            else:
                content = '''
                           ## No content on %s

                           !!! box "This page is empty. Please write some meaningful content with the edit button."

                           To get some nice formatting, get wiki:help.
                           ''' % (title)
                content = '\n'.join(l.strip() for l in content.split('\n'))
        else:
            name = 'content'
        res = web.render('wiki_external.html', name=name, error='', wikitext=content, pages=pages).render('html',
                                                                                                          doctype='html')
        return res



    @expose_for()
    def default(self, *args):
        from glob import glob
        args = list(args)
        name = '.'.join(args)
        title = ' / '.join(arg.title() for arg in args)
        filename = self.name2path(name.lower())
        content = ''
        related = ''
        pages = sorted([os.path.basename(s)[:-5]
                        for s in glob(web.abspath('datafiles/wiki/%s*.wiki' % name.split('.')[0]))])
        if name in pages:
            pages.remove(name)
        if os.path.exists(filename):
            content = str(open(filename).read())
        elif args:
            if pages:
                content += '\n\n!!! box "Note:"\n    You can write an introduction to this topic with the edit button above.\n'
            else:
                content = '''
                ## No content on %s

                !!! box "This page is empty. Please write some meaningful content with the edit button."

                To get some nice formatting, get wiki:help.
                ''' % (title)
                content = '\n'.join(l.strip() for l in content.split('\n'))
        else:
            name = 'content'
        res = web.render('wiki.html', name=name, error='',
                         wikitext=content, pages=pages).render('html', doctype='html')
        return res

    @expose_for(group.editor)
    def save(self, name, newtext):
        try:
            fn = self.name2path(name)
            open(fn, 'w').write(newtext)
        except:
            return 'err:' + traceback()

    @expose_for(group.admin)
    def delete(self, name):
        try:
            os.remove(self.name2path(name))
        except:
            return 'err:' + traceback()
        return ''


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

            person = db.Person.get(session, person)

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

        return web.render('projects.html', error=error, projects=projects)\
            .render('html', doctype='html')


class AdminPage(object):
    """
    Displays forms and utilites for runtime configuration of the application, which will be made persistent
    """
    expose = True

    @expose_for(group.admin)
    def default(self, error='', success=''):

        return web.render('admin.html', error=error, success=success, MEDIA_PATH=MEDIA_PATH)\
            .render('html', doctype='html')

    @expose_for(group.admin)
    def upload(self, imgtype, imgfile, **kwargs):

        runtimedir = os.path.realpath('.') + '/'

        fn = runtimedir + 'webpage'

        def _save_to_location(location, file):
            """
            Helper function
            """
            error = ''

            if not os.path.isfile(location):
                cherrypy.log.error('No image present at \'%s\'. Creating it now!')

            try:
                write_to_file(location, imgfile.file)
            except:
                error += '\n' + traceback()
                print(error)

            return error

        # check for image types to determine location
        if imgtype == 'logo':
            # save to logo location
            error = _save_to_location(fn + MEDIA_PATH['logo'], imgfile)

        elif imgtype == 'leftbanner':
            # save to leftbanner location
            error = _save_to_location(fn + MEDIA_PATH['banner-left'], imgfile)

        else:
            cherrypy.log.error('Adminpage form value imgtype is wrong')
            cherrypy.response.status = 400
            raise cherrypy.HTTPError(status=400, message='Bad Request')

        if error is '':
            msg = 'Successfully uploaded image. Reload page to view results'
            raise web.HTTPRedirect('/admin?success=%s' % msg)
        else:
            raise web.HTTPRedirect('/admin/?error=%s' % error)


class Root(object):
    _cp_config = {'tools.sessions.on': True,
                  'tools.sessions.timeout': 24 * 60, # One day
                  'tools.sessions.locking': 'early',
                  'tools.sessions.storage_type': 'file',
                  'tools.sessions.storage_path': web.abspath('sessions'),
                  'tools.auth.on': True,
                  'tools.sessions.locking': 'early'}

    site = SitePage()
    user = PersonPage()
    valuetype = VTPage()
    dataset = DatasetPage()
    download = DownloadPage()
    project = ProjectPage()
    job = JobPage()
    log = LogPage()
    map = MapPage()
    instrument = DatasourcePage()
    picture = PicturePage()
    preferences = Preferences()
    plot = PlotPage()
    calendar = CalendarPage()
    wiki = Wiki()
    admin = AdminPage()

    @expose_for()
    def index(self):
        if web.user():
            session = db.Session()
            user = session.query(db.Person).get(web.user())
            if user.jobs.filter(db.Job.done == False, db.Job.due - datetime.now() < timedelta(days=7)).count():
                raise web.HTTPRedirect('/job')
        return self.map.index()

    @expose_for()
    def navigation(self):
        return web.navigation()

    @expose_for()
    def login(self, frompage='/', username=None, password=None, error='', logout=None):
        if logout:
            users.logout()
            raise web.HTTPRedirect(frompage or '/')
        elif username and password:
            error = users.login(username, password)
            if error:
                return web.render('login.html', error=error, frompage=frompage).render('html', doctype='html')
            else:
                raise web.HTTPRedirect(frompage or '/')
        else:
            return web.render('login.html', error=error, frompage=frompage).render('html', doctype='html')

    @expose_for(group.admin)
    def showjson(self, **kwargs):
        web.setmime('application/json')
        import json
        return json.dumps(kwargs, indent=4)

    @expose_for(group.editor)
    def datastatus(self):
        session = db.Session()
        func = db.sql.func
        q = session.query(db.Datasource.name, db.Dataset._site, func.count(db.Dataset.id),
                          func.min(db.Dataset.start), func.max(db.Dataset.end)
                          ).join(db.Dataset.source).group_by(db.Datasource.name, db.Dataset._site)
        for r in q:
            yield str(r) + '\n'

    @expose_for()
    def markdown(self, fn):
        """
        A simple markdown API access. Can be used for text files
        """
        fn = web.abspath(fn)
        if os.path.exists(fn):
            return web.markdown(open(fn).read())
        else:
            return ''

    def markdownpage(self, content, title=''):
        """
        Returns a fully rendered page with navigation including the rendered markdown content
        """
        res = web.render('empty.html', title=title,
                         error='').render('html', doctype='html')
        return res.replace('<!--content goes here-->', web.markdown(content))

    @expose_for()
    def robots_txt(self):
        web.setmime(web.mime.plain)
        return "User-agent: *\nDisallow: /\n"

    @expose_for(group.admin)
    def freemem(self):
        web.setmime(web.mime.plain)
        import subprocess
        if sys.platform == 'linux2':
            return subprocess.Popen(['free', '-m'], stdout=subprocess.PIPE).communicate()[0]
        else:
            return 'Memory storage information is not available at your platform'

    @expose_for()
    def actualclimate_json(self, site=47):
        session = db.Session()
        web.setmime(web.mime.json)
        now = datetime.now()
        yesterday = now - timedelta(hours=24)
        res = {'time': now}
        for dsid in range(1493, 1502):
            ds = db.Timeseries.get(session, dsid)
            t, v = ds.asarray(start=yesterday)
            res[ds.name.split(',')[0].strip().replace(' ', '_')] = {
                'min': v.min(), 'max': v.max(), 'mean': v.mean()}
        return web.as_json(res)

    @expose_for()
    @web.mimetype(web.mime.html)
    def actualclimate_html(self):
        with db.session_scope() as session:
            ds = session.query(db.Dataset).filter(
                db.Dataset.id.in_(list(range(1493, 1502))))
            return web.render('actualclimate.html', ds=ds, db=db).render('html', doctype='html')

# if __name__=='__main__':
#    web.start_server(Root(), autoreload=False, port=8081)
