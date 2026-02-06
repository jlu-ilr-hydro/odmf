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
from ..lib.render_tools import dict_to_html

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
            li = importlog.LogbookImport(path.absolute, web.user(), sheetname=kwargs.get('sheet', 0))
            logs, cancommit = li('commit' in kwargs)
        except importlog.LogImportError as e:
            raise web.redirect(path.href, error=str(e))

        if cherrypy.request.method=='POST' and 'commit' in kwargs and cancommit:
            di.savetoimports(path.absolute, web.user(), ["_various_as_its_manual"])
            raise web.redirect(path.parent().href, error=error)
        else:
            return web.render(
                'import/logimport.html', filename=path, logs=logs,
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
        try:
            datasets, info, errors, labconf = li.labimport(path, dryrun=dryrun)
        except li.LabImportError as e:
            raise web.redirect(path.href, error=str(e))
        except Exception as e:
            raise web.redirect(path.href, error=str(e))
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
                error= error,
                filename=path,
                conffile=path.glob_up('*.labimport'),
                cancommit=True,
                labconf=labconf,
                datasets=ds_objects,
                info_dict=info,
                errors=errors
            ).render()
    
    @expose_for(Level.editor)
    def record(self, filename, **kwargs):
        """
        Imports records from a file and shows the result. On POST, imports the data to the database
        """
        import re
        path = Path(filename.strip('/'))
        errors = []
        if error:=di.checkimport(path):
            errors.append(error)
        
        # - Load df from parquet, csv or excel
        if re.match(r'.*\.parquet$', path.name, re.IGNORECASE):
            df = pd.read_parquet(path.absolute)
        elif re.match(r'.*\.xls.?$', path.name, re.IGNORECASE):
            df = pd.read_excel(path.absolute, sheet_name=kwargs.get('sheet',0))
        elif re.match(r'.*\.[ct]sv$', path.name, re.IGNORECASE):
            df = pd.read_csv(path.absolute, sep=None, engine='python')

        # - check columns, remove nan
        if not all(c in df.columns.str.lower() for c in 'time|dataset|value'.split('|')):
            errors.append('File must contain at least the columns time, dataset and value')
        else:
            df = df[~(pd.isna(df['time']) | pd.isna(df['value']) | pd.isna(df['dataset']))]
            # - count all records per datasets and show value ranges
            df_agg = df.groupby('dataset').agg({'value': ['count', 'min', 'mean', 'max'],'time': ['min', 'max']})
            # - load all unique datasets
            with db.session_scope() as session:
                sql = db.sql.select(db.Dataset).where(db.Dataset.id.in_(df_agg.index))
                datasets = {
                    ds.id: ds 
                    for ds, in session.execute(sql)
                }
                dataset_description = {
                    ds_id: f'n: {row[("value", "count")]}, value: {row[("value", "min")]:04g}..{row[("value", "max")]:0.4g} {datasets[ds_id].valuetype.unit}, time: {row[("time", "min")]:%Y-%m-%d}..{row[("time", "max")]:%Y-%m-%d}'
                    for ds_id, row in df_agg.iterrows()
                    if ds_id in datasets
                }
                for ds_id in df_agg.index:
                    if ds_id not in datasets:
                        errors.append(f'Dataset {ds_id} not found in database')
        
                # - on GET, show datasets with their info
                if cherrypy.request.method == 'GET':
                    return web.render(
                        'import/recordimport.html',
                        error= '\n'.join(errors),
                        filename=path,
                        datasets=datasets,
                        dataset_description=dataset_description,
                        can_commit=not errors
                    ).render()
                
                # - on POST, import data to db and redirect to dataset page
                elif cherrypy.request.method == 'POST':
                    from odmf.dataimport.parquet_import import addrecords_dataframe
                    try:
                        ds_ids, n_records = addrecords_dataframe(df)
                    except Exception as e:
                        raise web.redirect(path.href, error=str(e))
                    else:
                        di.savetoimports(path.absolute, web.user(), ds_ids)
                        raise web.redirect(path.parent().href, msg=f'File import successful: added {n_records} records in {len(ds_ids)} datasets')





