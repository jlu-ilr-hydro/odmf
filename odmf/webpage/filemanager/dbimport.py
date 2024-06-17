import time

from odmf.webpage import lib as web

import io
import pandas as pd
from cherrypy import log
import cherrypy

from odmf.webpage.auth import Level, expose_for

from odmf import dataimport as di
from odmf import db
from odmf.dataimport import importlog
from odmf.dataimport import pandas_import as pi
from ...dataimport import lab_import as li

from odmf.tools import Path


def plot_series(idescr: di.ImportDescription, data: pd.DataFrame) -> dict:

    def make_plot(col):
        try:
            ser: pd.Series = data[col.name]
            ser.index = data['time']
            ax = ser.plot(figsize=(8, 2))
            svg = io.StringIO()
            ax.figure.savefig(svg, format='svg', dpi=100, transparent=True)
            ax.figure.clear()
            return svg.getvalue()
        except Exception as e:
            return f'<div class="alert alert-danger">{e} - are No-Data-values handled correctly by the .conf?</div>'

    return {
        col.name: make_plot(col)
        for col in idescr.columns
    }



@web.expose
class DbImportPage:
    """
    Class to handle data imports from files
    """

    @expose_for(Level.editor)
    def log(self, filename, **kwargs):
        path = Path(filename.strip('/'))
        error = di.checkimport(path)
        if error:
            raise web.redirect(path.parent().href, error=error)
        try:
            li = importlog.LogbookImport(path.absolute, web.user())
            logs, cancommit = li('commit' in kwargs)
        except importlog.LogImportError as e:
            raise web.redirect(path.parent().href, error=str(e))

        if cherrypy.request.method=='POST' and 'commit' in kwargs and cancommit:
            di.savetoimports(path.absolute, web.user(), ["_various_as_its_manual"])
            raise web.redirect(path.parent().href, error=error)
        else:
            return web.render(
                'logimport.html', filename=path, logs=logs,
                cancommit=cancommit, error=error
            ).render()

    @expose_for(Level.editor)
    def conf(self, filename, **kwargs):
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
            'import/confimport.html',
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



    @expose_for(Level.editor)
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


    @expose_for(Level.editor)
    def lab(self, filename, **kwargs):

        path = Path(filename.strip('/'))
        error = di.checkimport(path)
        dryrun = True
        if not error and cherrypy.request.method == 'POST':
            if 'errors_ok' in kwargs:
                dryrun = False
            else:
                error = 'Errors are present: if you want to import with errors present, you need to check "Submit with errors"'
        datasets, info, errors, labconf = li.labimport(path, dryrun=dryrun)
        if not dryrun:
            di.savetoimports(path.absolute, web.user(), datasets)
            raise web.redirect(path.href, msg=f'File import successful: added {info["imported"]} records in {len(datasets)} datasets')

        with db.session_scope() as session:
            ds_objects = [
                (ds, datasets[ds.id]) for ds in
                session.query(db.Dataset).filter(db.Dataset.id.in_(datasets))
            ]
            return web.render(
                'import/labimport.html',
                error = error,
                filename=path, cancommit=True,
                labconf=labconf,
                datasets=ds_objects,
                info_dict=info,
                errors=errors
            ).render()






