import cherrypy.lib.sessions

from .. import prefix
from . import lib as web
from .lib.errors import errorhandler
from .auth import users, Level, expose_for, HTTPAuthError

from .. import db
from ..config import conf
from datetime import datetime, timedelta
from . import db_editor as dbe
from . import map
from .filemanager import upload
from . import plot
from . import api
from . import static


class Root(object):
    """
    The root of the odmf webpage
    """
    _cp_config = {
        'tools.sessions.on': True,
        'tools.sessions.timeout': 24 * 60 * 60,  # 2 Months
        'tools.sessions.storage_class': cherrypy.lib.sessions.FileSession,
        'tools.sessions.storage_path': prefix + '/sessions',
        'tools.proxy.on': True,
        'tools.auth.on': True,
        'tools.sessions.locking': 'early',
    } | errorhandler.html

    map = map.MapPage()
    download = upload.DownloadPage()
    plot = plot.PlotPage()
    site = dbe.SitePage()
    dataset = dbe.DatasetPage()
    # picture = dbe.PicturePage()
    log = dbe.LogPage()
    valuetype = dbe.VTPage()
    instrument = dbe.DatasourcePage()
    project = dbe.ProjectPage()
    user = dbe.PersonPage()
    job = dbe.JobPage()
    message = dbe.MessagePage()
    topic = dbe.TopicPage()
    help = static.Help()
    api = api.API()

    media = static.StaticServer('media', listdir=True)
    datafiles = static.StaticServer(conf.datafiles, listdir=True)
    node_modules = static.StaticServer('node_modules', listdir=True)

    @expose_for()
    @web.method.get
    def index(self):
        """
        Root home: Shows the map page if the current user has no urgent jobs.
        """
        if web.user():
            with db.session_scope() as session:
                user = session.get(db.Person, web.user())
                if user and user.jobs.filter(~db.Job.done, db.Job.due - datetime.now() < timedelta(days=7)).count():
                    raise web.redirect(conf.url('/job'))
        return self.map.index()

    @expose_for(Level.supervisor)
    def bulkimport(self,undo=None, table=None, file=None):
        """
        GET returns the list of formaer imports for undo. Use undo-Attribute (undo-filename) to show details of an undo
        POST with undo-Attribute (undo-filename): Perform undo-action
        POST with table and file attribute: table is a tablename (site, datasets, log) and file is a file upload object
            that contains the tabular data as excel, parquet etc

        """
        from ..tools import import_objects as impo
        from pathlib import Path
        undo_path = Path(conf.home + '/sessions/undo')
        result = None
        success = None
        error = None
        if cherrypy.request.method == 'POST':
            if undo:
                try:
                    result = impo.load_undo_file(undo_path / undo)
                    with db.session_scope() as session:
                        result.undo(session)
                    (undo_path / undo).unlink()
                except Exception as e:
                    error = str(e)
                else:
                    success = str(result) + ' undone'
                    result = None
            elif table and file:
                try:
                    with db.session_scope() as session:
                        result = impo.import_objects(session, table, file.filename, file.file, web.user())
                except Exception as e:
                    error = str(e)
                    result = None
                else:
                    success = str(result) + ' imported'
                    undo_path.mkdir(parents=True, exist_ok=True)
                    result.save(undo_path)
        elif undo:
            result = impo.load_undo_file(undo_path / undo)

        # Get all undo-files and show results
        if users.current.level >= Level.admin:
            user = '*'
        else:
            user = web.user()
        undos = list(reversed(sorted([
            impo.load_undo_file(p) for p in
            impo.list_undo_files(undo_path, '*', user)
        ], key=lambda undo: undo.time)))
        return web.render('import/bulkimport.html', title='bulk import', undos=undos, result=result, error=error, success=success).render()

    @expose_for()
    @web.show_in_nav_for(icon='key')
    def login(self, frompage=None, username=None, password=None, error='', logout=None):
        """
        Enter here your username and password to get access to restricted data or to change data
        """

        if cherrypy.request.method != 'POST':
            with db.session_scope() as session:
                admins = session.scalars(db.sql.select(db.Person).where(db.Person.access_level>=4, db.Person.active==True))
                return web.render('login.html', error=error, frompage=frompage, admins=admins).render()

        elif logout:
            users.logout()
            return web.render('login.html', error=error, frompage=frompage).render()

        elif username and password:
            # Try the login
            error = users.login(username, password)
            frompage = frompage or conf.root_url + '/login'
            if error:
                raise HTTPAuthError(referrer=frompage)
            else:
                raise web.redirect(frompage)
        else:
            # Username or password not given, let the user retry
            return web.render('login.html', error=error, frompage=frompage, admins=[]).render()


    @expose_for(Level.admin)
    @web.mime.json
    @web.method.get
    def showjson(self, **kwargs):
        """
        A helper function to display keywords as json. Only for debugging, no data leaks possible
        """
        return web.json_out(kwargs)


    @expose_for()
    def markdown(self, fn):
        """
        A simple markdown API access. Can be used for text files
        """
        fn = conf.abspath(fn)
        return web.markdown(fn.read_text())

    def markdownpage(self, content, title=''):
        """
        Returns a fully rendered page with navigation including the rendered markdown content
        """
        return web.render('empty.html', title=title,
                         error='', success='', content=content).render()

    @expose_for()
    @web.mime.plain
    def robots_txt(self):
        """
        Disallows search engine in ODMF servers

        Returns:
            User-agent: *
            Disallow: /
        """
        return "User-agent: *\nDisallow: /\n"

    @expose_for()
    @web.method.get
    def resources(self, format='html'):
        """
        Returns a json object representing all resources of this cherrypy web-application
        """
        from .auth import is_member
        root = web.Resource('/', self).create_tree()
        web.mime.set(format)
        if format == 'json':
            return web.json_out(
                {
                    r.uri:  {'level': r.level, 'doc': r.doc, 'methods': r.methods}
                    for r in root.walk()
                    if not r.level or is_member(r.level)
                }
            )
        elif format in ['xlsx', 'csv', 'tsv']:
            import pandas as pd
            import io
            df = pd.DataFrame(
                [
                    [r.uri, r.level, r.doc, r.icon, str(r.methods)]
                    for r in root.walk()
                    if not r.level or is_member(r.level)
                ],
                columns=['uri', 'level', 'doc', 'icon', 'methods']
            )
            if format == 'xlsx':
                buf = io.BytesIO()
                df.to_excel(buf)
                return buf.getvalue()

            elif format == 'csv':
                buf = io.StringIO()
                df.to_csv(buf)
                return buf.getvalue().encode('utf-8')

            elif format == 'tsv':
                buf = io.StringIO()
                df.to_csv(buf, sep='\t')
                return buf.getvalue().encode('utf-8')
        elif format == 'html':
            def get_icon(icon: str):
                if icon:
                    return f'!fa-{icon}'
                else:
                    return ''
            md_text = '\n\n'.join(
                '#' * r.uri.count('/') + f' {get_icon(r.icon)} {r.uri}\n\n - level: {r.level}\n - methods: {r.methods}\n\n{r.doc}'
                for r in root.walk()
                if not r.level or is_member(r.level)
            )
            return self.markdownpage(md_text, 'Site map')


    def __init__(self):
        """
        Creates the root page and marks self as the root object
        """
        web.render.set_root(self)


