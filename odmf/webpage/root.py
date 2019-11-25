import cherrypy
import json
import inspect


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


def resource_walker(obj, only_navigatable=False, recursive=True, for_level=0) -> dict:
    """
    Builds a recursive tree of exposed cherrypy endpoints

    How to call for a tree of the complete app:
    ::
        resource_tree = resource_walker(root)

    How to call for a branch in the app (eg. the site page)
    ::
        resource_subtree = resource_walker(root, site)

    :param obj: The cherrypy object (type or function) to investigate
    :return: A dictionary containing either a dictionary for the next deeper address level or a
            docstring of an endpoint
    """
    def has_attr(obj, attr: str) -> bool:
        return hasattr(obj, attr) or hasattr(type(obj), attr)

    def navigatable(obj):
        try:
            return has_attr(obj, 'exposed') and obj.exposed and (
                    (not only_navigatable) or has_attr(obj, 'show_in_nav') and obj.show_in_nav <= for_level
            )
        except TypeError:
            raise

    def getdoc(obj):
        """Returns inspect.getdoc if available, else checks for an index method and returns the getdoc of that"""
        return inspect.getdoc(obj) or \
               (getattr(obj, 'index', None) and inspect.getdoc(obj.index)) or \
               (getattr(obj, 'default', None) and inspect.getdoc(obj.default))

    p_vars = dict((k, getattr(obj, k)) for k in dir(obj))
    p_vars = {k: v for k, v in p_vars.items() if not k.startswith('_') and navigatable(v)}
    if recursive:
        res = {
            k: resource_walker(v, only_navigatable)
            for k, v in p_vars.items()
            if navigatable(v)
        }
    else:
        res = {
            k: getdoc(v)
            for k, v in p_vars.items()
            if navigatable(v)
        }

    if getdoc(obj):
        if res:
            res['__doc__'] = getdoc(obj)
        else:
            res = getdoc(obj)
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
        from .lib.render import navigation
        return navigation()

    @expose_for()
    @web.show_in_nav_for()
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
    @web.mime.json
    def showjson(self, **kwargs):
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
                         error='').render('html', doctype='html')
        return res.replace('<!--content goes here-->', web.markdown(content))

    @expose_for()
    @web.mime.plain
    def robots_txt(self):
        return "User-agent: *\nDisallow: /\n"

    @expose_for()
    @web.mime.json
    def actualclimate_json(self, site=47):
        session = db.Session()
        now = datetime.now()
        yesterday = now - timedelta(hours=24)
        res = {'time': now}
        for dsid in range(1493, 1502):
            ds = session.query(db.Timeseries).get(dsid)
            t, v = ds.asarray(start=yesterday)
            res[ds.name.split(',')[0].strip().replace(' ', '_')] = {
                'min': v.min(), 'max': v.max(), 'mean': v.mean()}
        return web.as_json(res)

    @expose_for()
    @web.mime.html
    def actualclimate_html(self):
        with db.session_scope() as session:
            ds = session.query(db.Dataset).filter(
                db.Dataset.id.in_(list(range(1493, 1502))))
            return web.render('actualclimate.html', ds=ds, db=db).render('html', doctype='html')

    @expose_for()
    @web.mime.json
    def resources(self, only_navigatable=False, recursive=True, for_level=users.current.level):
        """
        Returns a json object representing all resources of this cherrypy web-application
        """
        res = resource_walker(self, only_navigatable, recursive, int(for_level))
        return json.dumps(res).encode('utf-8')

