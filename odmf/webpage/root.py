import cherrypy

from . import lib as web
from .auth import users, group, expose_for

from .. import db
import sys
import os
from datetime import datetime, timedelta
from . import collaboration as cll
from . import db_editor as dbe
from . import map
from . import upload
from .preferences import Preferences
from . import plot
from . import api
from . import static


class Root(object):
    _cp_config = {'tools.sessions.on': True,
                  'tools.sessions.timeout': 24 * 60,  # One day
                  'tools.sessions.storage_type': 'file',
                  'tools.sessions.storage_path': './sessions',
                  'tools.auth.on': True,
                  'tools.sessions.locking': 'early'}

    api = api.API()
    site = dbe.SitePage()
    user = dbe.PersonPage()
    valuetype = dbe.VTPage()
    dataset = dbe.DatasetPage()
    download = upload.DownloadPage()
    project = dbe.ProjectPage()
    job = dbe.JobPage()
    log = dbe.LogPage()
    map = map.MapPage()
    instrument = dbe.DatasourcePage()
    picture = dbe.PicturePage()
    preferences = Preferences()
    plot = plot.PlotPage()
    calendar = cll.CalendarPage()
    wiki = cll.Wiki()
    admin = cll.AdminPage()
    media = static.StaticServer('*/media', True)

    @expose_for()
    def index(self):
        if web.user():
            session = db.Session()
            user = session.query(db.Person).get(web.user())
            if user and user.jobs.filter(db.Job.done == False, db.Job.due - datetime.now() < timedelta(days=7)).count():
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
                cherrypy.response.status = 401
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
