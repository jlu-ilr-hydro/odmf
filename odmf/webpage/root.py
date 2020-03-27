import cherrypy
import json

from .. import prefix
from . import lib as web
from .auth import users, group, expose_for

from .. import db
from ..config import conf
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
    """
    The root of the odmf webpage
    """
    _cp_config = {'tools.sessions.on': True,
                  'tools.sessions.timeout': 24 * 60,  # One day
                  'tools.sessions.storage_type': 'file',
                  'tools.sessions.storage_path': prefix + '/sessions',
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
    media = static.StaticServer('media', True)
    datafiles = static.StaticServer('datafiles', True)

    @expose_for()
    @web.show_in_nav_for()
    def index(self):
        """
        Root home: Shows the map page if the current user has no urgent jobs.
        """
        if web.user():
            session = db.Session()
            user = session.query(db.Person).get(web.user())
            if user and user.jobs.filter(db.Job.done == False, db.Job.due - datetime.now() < timedelta(days=7)).count():
                raise web.HTTPRedirect('/job')
        return self.map.index()

    @expose_for()
    def navigation(self):
        """
        The bare navigation page, usually embedded in other pages
        :return:
        """
        from .lib.renderer import get_nav_entries, render
        return render(
                'bootstrap_navigation.html',
                title='bootstrap@odmf',
                background_image=conf.nav_background,
                left_logo=conf.nav_left_logo,
                resources=get_nav_entries().items(),
            ).render()

    @expose_for()
    @web.show_in_nav_for()
    def login(self, frompage=None, username=None, password=None, error='', logout=None):
        """
        Enter here your username and password to get access to restricted data or to change data
        """
        if logout:
            users.logout()
            raise web.HTTPRedirect(frompage or conf.root_url)
        elif username and password:
            error = users.login(username, password)
            if error:
                cherrypy.response.status = 401
                return web.render('login.html', error=error, frompage=frompage).render()
            else:
                raise web.HTTPRedirect(frompage or conf.root_url)
        else:
            return web.render('login.html', error=error, frompage=frompage).render()

    @expose_for(group.admin)
    @web.mime.json
    def showjson(self, **kwargs):
        return web.json_out(kwargs)

    @expose_for(group.editor)
    def datastatus(self):
        with db.session_scope() as session:
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
        fn = conf.abspath(fn)
        if os.path.exists(fn):
            return web.markdown(open(fn).read())
        else:
            return ''

    def markdownpage(self, content, title=''):
        """
        Returns a fully rendered page with navigation including the rendered markdown content
        """
        res = web.render('empty.html', title=title,
                         error='').render()
        return res.replace('<!--content goes here-->', web.markdown(content))

    @expose_for()
    @web.mime.plain
    def robots_txt(self):
        return "User-agent: *\nDisallow: /\n"

    @expose_for()
    @web.mime.json
    def actualclimate_json(self, site=47):
        """
        Returns the last climate measurement from a specific site
        """
        with db.session_scope() as session:
            now = datetime.now()
            yesterday = now - timedelta(hours=24)
            res = {'time': now}
            for dsid in range(1493, 1502):
                ds = session.query(db.Timeseries).get(dsid)
                t, v = ds.asarray(start=yesterday)
                res[ds.name.split(',')[0].strip().replace(' ', '_')] = {
                    'min': v.min(), 'max': v.max(), 'mean': v.mean()}
        return web.json_out(res)

    @expose_for()
    @web.mime.html
    def actualclimate_html(self):
        with db.session_scope() as session:
            ds = session.query(db.Dataset).filter(
                db.Dataset.id.in_(list(range(1493, 1502))))
            return web.render('actualclimate.html', ds=ds, db=db).render()

    @expose_for()
    @web.mime.json
    def resources(self, only_navigatable=False, recursive=True, for_level=users.current.level):
        """
        Returns a json object representing all resources of this cherrypy web-application
        """
        return web.json_out(web.resource_walker(self, only_navigatable, recursive, int(for_level)))

    def __init__(self):
        web.render.set_root(self)

