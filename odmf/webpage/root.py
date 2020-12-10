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
from .filemanager import upload
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

    map = map.MapPage()
    site = dbe.SitePage()
    plot = plot.PlotPage()
    download = upload.DownloadPage()
    dataset = dbe.DatasetPage()
    picture = dbe.PicturePage()
    job = dbe.JobPage()
    log = dbe.LogPage()

    valuetype = dbe.VTPage()
    project = dbe.ProjectPage()
    instrument = dbe.DatasourcePage()
    wiki = cll.Wiki()
    user = dbe.PersonPage()
    admin = cll.AdminPage()
    api = api.API()

    preferences = Preferences()
    media = static.StaticServer('media', True)
    datafiles = static.StaticServer('datafiles', True)

    @expose_for()
    def index(self):
        """
        Root home: Shows the map page if the current user has no urgent jobs.
        """
        if web.user():
            session = db.Session()
            user = session.query(db.Person).get(web.user())
            if user and user.jobs.filter(db.Job.done == False, db.Job.due - datetime.now() < timedelta(days=7)).count():
                raise web.redirect(conf.root_url + '/job')
        return self.map.index()


    @expose_for()
    @web.show_in_nav_for(icon='key')
    def login(self, frompage=None, username=None, password=None, error='', logout=None):
        """
        Enter here your username and password to get access to restricted data or to change data
        """
        if logout:
            users.logout()
            if frompage:
                raise web.HTTPRedirect(frompage or conf.root_url)
            else:
                return web.render('login.html', error=error, frompage=frompage).render()

        elif username and password:
            error = users.login(username, password)

            if error:
                return web.redirect('login.html', error=error, frompage=frompage)

            elif frompage:
                if 'login' in frompage:
                    return web.render('login.html', error=error, frompage=frompage).render()
                else:
                    raise web.HTTPRedirect(frompage)
            else:
                return web.render('login.html', error=error, frompage=frompage).render()
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
    def resources(self):
        """
        Returns a json object representing all resources of this cherrypy web-application
        """
        from .auth import is_member
        root = web.Resource('/', self).create_tree()

        return web.json_out(
            {
                r.uri: [r.level, r.doc]
                for r in root.walk()
                if not r.level or is_member(r.level)
            }
        )

    def __init__(self):
        web.render.set_root(self)

