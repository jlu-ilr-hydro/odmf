import cherrypy
import json
from inspect import getdoc


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

def ressource_walker(*path) -> dict:
    """
    Builds a recursive tree of exposed cherrypy endpoints

    How to call for a tree of the complete app:
    >>> ressource_tree = ressource_walker(root)

    How to call for a branch in the app (eg. the site page)
    >>> ressource_subtree = ressource_walker(root, site)

    :param path: The current url in terms of objects enabled for cherrypy dispaching. The last object in the path
                is the current object
    :return: A dictionary containing either a dictionary for the next deeper address level or a
            docstring of an endpoint
    """
    def is_exposed(obj):
        return getattr(obj, 'exposed', False) or getattr(type(obj), 'exposed', False)

    act_p = path[-1]
    p_vars = dict((k, getattr(act_p, k)) for k in dir(act_p))
    p_vars = {k: v for k, v in p_vars.items() if not k.startswith('_') and is_exposed(v)}
    res = {
        k: ressource_walker(*path, v)
        for k, v in p_vars.items()
        if is_exposed(v)
    }

    if getdoc(act_p):
        if res:
            res['__doc__'] = getdoc(act_p)
        else:
            res = getdoc(act_p)
    else:
        res = None

    return res


class Root(object):
    """
    The root of the odmf webpage
    """
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
                raise web.HTTPRedirect('/job')
        return self.map.index()

    @expose_for()
    def navigation(self):
        """
        The bare navigation page, usually embedded in other pages
        :return:
        """
        return web.navigation()

    @expose_for()
    def login(self, frompage='/', username=None, password=None, error='', logout=None):
        """
        The login page

        Parameters
        ----------
        frompage
            Referer to this page - useful to navigate backwards
        username
            Username for login, empty to show the page
        password
            ditto, password
        error
            On authorization errors this page should be shown with an appropriate error message
        logout
            If logout is given, the current user logs out

        """
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

    @expose_for()
    @web.mimetype(web.mime.json)
    def ressources(self):
        """
        Returns a json object representing all ressources of this cherrypy web-application
        """
        res = ressource_walker(self)
        return json.dumps(res).encode('utf-8')

