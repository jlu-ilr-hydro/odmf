import time

from odmf.webpage import lib as web

import io
import pandas as pd
from cherrypy import log

from odmf.webpage.auth import group, expose_for

from odmf import dataimport as di
from odmf import db
from odmf.dataimport import importlog
from odmf.dataimport import pandas_import as pi
from odmf.tools import Path


def plot_series(idescr: di.ImportDescription, data: pd.DataFrame) -> dict:

    def make_plot(col):
        ser: pd.Series = data[col.name]
        ser.index = data['time']
        ax = ser.plot(figsize=(8, 2))
        svg = io.StringIO()
        ax.figure.savefig(svg, format='svg', dpi=100, transparent=True)
        ax.figure.clear()
        return svg.getvalue()

    return {
        col.name: make_plot(col)
        for col in idescr.columns
    }



@web.expose
class DbImportPage:
    """
    Class to handle data imports from files
    """

    @expose_for(group.editor)
    def index(self, filename, **kwargs):
        filepath = Path(filename)
        if not filepath.exists():
            raise web.redirect(f'{filepath.parent().href}', f'{filepath} not found - cannot import')
        import re
        # If the file ends with log.xls[x], import as log list
        if re.match(r'(.*)_log\.xlsx?$', filename):
            log("Import with logimport")
            return self.as_logimport(filename, **kwargs)
        # else import as instrument file
        else:
            return self.with_config(filename, **kwargs)

    @staticmethod
    def as_logimport(filename, **kwargs):
        path = Path(filename.strip('/'))
        error = di.checkimport(path)
        if error:
            raise web.redirect(path.parent().href, error=error)
        try:
            li = importlog.LogbookImport(path.absolute, web.user())
            logs, cancommit = li('commit' in kwargs)
        except importlog.LogImportError as e:
            raise web.redirect(path.parent().href, error=str(e))

        if 'commit' in kwargs and cancommit:
            di.savetoimports(path.absolute, web.user(), ["_various_as_its_manual"])
            raise web.redirect(path.parent().href, error=error)
        else:
            return web.render(
                'logimport.html', filename=path, logs=logs,
                cancommit=cancommit, error=error
            ).render()

    @staticmethod
    def with_config(filename, **kwargs):
        """
        Shows dbimport.html with the datafile loaded and ready for import
        """
        path = Path(filename.strip('/'))
        error = di.checkimport(path)

        # The content of the file
        rawcontent = open(path.absolute, 'rb').read(1024).decode('utf-8', 'ignore')
        stats, startdate, enddate, table = {}, None, None, ''
        plots = {}
        try:
            config = di.ImportDescription.from_file(path.absolute)
            df = pi.load_dataframe(config, path)
            stats, startdate, enddate = pi.get_statistics(config, df)
            plots = plot_series(config, df)
            table = df.to_html(
                float_format=lambda f: f'{f:0.5g}',
                classes=('table', 'thead-dark', 'table-responsive', 'table-striped'),
                border=0,
                max_rows=30
            )

        except pi.DataImportError as e:

            error = str(e)


        return web.render(
            'dbimport.html',
            rawcontent=rawcontent,
            config=config,
            stats=stats,
            error=error,
            table=table,
            filename=filename,
            dirlink=path.up(),
            startdate=startdate, enddate=enddate,
            plots=plots
        ).render()



    @expose_for(group.editor)
    @web.method.post
    def submit_config(self, filename, siteid, **kwargs):
        path = Path(filename.strip('/'))
        siteid = web.conv(int, siteid)
        user = kwargs.pop('user', web.user())
        config = di.ImportDescription.from_file(path.absolute)
        try:
            with db.session_scope() as session:
                messages = pi.submit(session, config, path, user, siteid)
                di.savetoimports(path.absolute, web.user(), [m.split()[0] for m in messages])

        except pi.DataImportError as e:
            raise web.redirect('..', error=str(e))

        else:
            raise web.redirect(path.parent().href, msg='\n'.join(f' - {msg}' for msg in messages))

