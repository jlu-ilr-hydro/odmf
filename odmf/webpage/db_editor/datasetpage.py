'''
Created on 18.07.2012

@author: philkraf
'''
from base64 import b64encode
from .. import lib as web
from ... import db
from traceback import format_exc as traceback
from datetime import datetime, timedelta
import io
from ..auth import group, expose_for, users
import codecs
from ...tools.calibration import Calibration, CalibrationSource
from ...config import conf
from pytz import common_timezones
import cherrypy


@web.show_in_nav_for(1, icon='clipboard')
class DatasetPage:
    """
    Serves the direct dataset manipulation and querying
    """
    exposed = True

    @expose_for(group.logger)
    @web.method.get
    def index(self, error=''):
        """
        Returns the query page (datasetlist.html). Site logic is handled with ajax
        """
        return web.render('datasetlist.html', error=error).render()

    @expose_for(group.guest)
    @web.method.get
    def default(self, id='new', site_id=None, vt_id=None, user=None, error='', _=None):
        """
        Returns the dataset view and manipulation page (dataset-edit.html).
        Expects an valid dataset id, 'new' or 'last'. With new, a new dataset
        is created, if 'last' the last chosen dataset is taken   
        """
        if id == 'last':
            # get the last viewed dataset from web-session. If there is no
            # last dataset, redirect to index
            id = web.cherrypy.session.get('dataset')  # @UndefinedVariable
            if id is None:
                raise web.redirect(conf.root_url + '/dataset/')
        with db.session_scope() as session:

            site = session.query(db.Site).get(site_id) if site_id else None
            valuetype = session.query(db.ValueType).get(
                vt_id) if vt_id else None
            # All projects

            if user is None:
                user = web.user()
            user: db.Person = session.query(db.Person).get(user) if user else None
            if id == 'new':
                active = db.Timeseries(
                    id=db.newid(db.Dataset, session),
                    name='New Dataset',
                    site=site,
                    valuetype=valuetype,
                    measured_by=user,
                    access=user.access_level
                )
            else:  # Else load requested dataset
                active = session.query(db.Dataset).get(int(id))

                if active:  # save requested dataset as 'last'
                    web.cherrypy.session['dataset'] = id  # @UndefinedVariable
                else:
                    raise web.redirect(conf.root_url + '/dataset', error=f'No ds{id} available')

            # Setting the project, for editing and ui navigation
            if active.project is not None:
                project = session.query(db.Project).get(int(active.project))
            else:
                project = None

            try:
                # load data for dataset-edit.html:
                # similar datasets (same site and same type)
                similar_datasets = self.subset(session, valuetype=active.valuetype.id,
                                               site=active.site.id)
                # parallel dataset (same site and same time, different type)
                parallel_datasets = session.query(db.Dataset).filter_by(site=active.site).filter(
                    db.Dataset.start <= active.end, db.Dataset.end >= active.start)

                datasets = {"same type": similar_datasets.filter(db.Dataset.id != active.id),
                            "same time": parallel_datasets.filter(db.Dataset.id != active.id)}
            except:
                # If loading fails, don't show similar datasets
                datasets = {}

            # Render the resulting page
            return web.render(
                'dataset-edit.html',
                # activedataset is the current dataset (id or new)
                ds_act=active, n=active.size() if active else 0,
                # Render error messages
                error=error,
                # similar and parallel datasets
                datasets=datasets,
                # The project
                activeproject=project,
                # All available timezones
                timezones=common_timezones + ['Fixed/60'],
                # The title of the page
                title='ds' + str(id),
                # A couple of prepared queries to fill select elements
                valuetypes=session.query(db.ValueType).order_by(db.ValueType.name),
                persons=session.query(db.Person).order_by(db.Person.can_supervise.desc(), db.Person.surname),
                sites=session.query(db.Site).order_by(db.Site.id),
                quality=session.query(db.Quality).order_by(db.Quality.id),
                datasources=session.query(db.Datasource),
                projects=session.query(db.Project),
                potential_calibration_sources=session.query(db.Dataset).filter(
                    db.Dataset._site == active._site,
                    db.Dataset.start <= active.end,
                    db.Dataset.end >= active.start
                )
            ).render()

    @expose_for(group.editor)
    @web.method.post
    def saveitem(self, **kwargs):
        """
        Saves the changes for an edited dataset
        """
        id = kwargs.get('id', '')
        try:
            # Get current dataset
            id = web.conv(int, id, '')
        except:
            raise web.redirect(conf.root_url + f'/dataset/{id}', error=traceback())
        # if save button has been pressed for submitting the dataset
        if 'save' in kwargs:
            # get database session
            with db.session_scope() as session:
                try:
                    pers = session.query(db.Person).get(kwargs.get('measured_by'))
                    vt = session.query(db.ValueType).get(kwargs.get('valuetype'))
                    q = session.query(db.Quality).get(kwargs.get('quality'))
                    s = session.query(db.Site).get(kwargs.get('site'))
                    src = session.query(db.Datasource).get(kwargs.get('source'))

                    # get the dataset
                    ds = session.query(db.Dataset).get(int(id))
                    if not ds:
                        # If no ds with id exists, create a new one
                        ds = db.Timeseries(id=id)
                    # Get properties from the keyword arguments kwargs
                    ds.site = s
                    ds.filename = kwargs.get('filename')
                    ds.name = kwargs.get('name')
                    ds.comment = kwargs.get('comment')
                    ds.measured_by = pers
                    ds.valuetype = vt
                    ds.quality = q

                    # TODO: Is it necessary to protect this
                    # of being modified by somebody who isn't a supervisor or higher?
                    if kwargs.get('project') == '0':
                        ds.project = None
                    else:
                        ds.project = kwargs.get('project')

                    ds.timezone = kwargs.get('timezone')

                    if src:
                        ds.source = src
                    if 'level' in kwargs:
                        ds.level = web.conv(float, kwargs.get('level'))
                    # Timeseries only arguments
                    if ds.is_timeseries():
                        if kwargs.get('start'):
                            ds.start = web.parsedate(kwargs['start'])
                        if kwargs.get('end'):
                            ds.end = web.parsedate(kwargs['end'])
                        ds.calibration_offset = web.conv(
                            float, kwargs.get('calibration_offset'), 0.0)
                        ds.calibration_slope = web.conv(
                            float, kwargs.get('calibration_slope'), 1.0)
                        ds.access = web.conv(int, kwargs.get('access'), 1)
                    # Transformation only arguments
                    if ds.is_transformed():
                        ds.expression = kwargs.get('expression')
                        ds.latex = kwargs.get('latex')
                    # Save changes
                    session.commit()
                except:
                    # On error render the error message
                    raise web.redirect(conf.root_url + f'/dataset/{id}', error=traceback())
        elif 'new' in kwargs:
            id = 'new'
        # reload page
        raise web.redirect(str(id))

    @expose_for()
    @web.method.get
    @web.mime.json
    def statistics(self, id):
        """
        Returns a json file holding the statistics for the dataset (is loaded by page using ajax)
        """
        with db.session_scope() as session:
            ds = session.query(db.Dataset).get(int(id))
            if ds:
                # Get statistics
                mean, std, n = ds.statistics()
                # Convert to json
                return web.json_out(dict(mean=mean, std=std, n=n))
            else:
                # Return empty dataset statistics
                return web.json_out(dict(mean=0, std=0, n=0))

    @expose_for(group.admin)
    @web.method.post_or_delete
    def remove(self, dsid):
        """
        Removes a dataset. Called by javascript, page reload handled by client
        """
        try:
            db.removedataset(dsid)
            return None
        except Exception as e:
            return str(e)

    def subset(self, session, valuetype=None, user=None,
               site=None, date=None, instrument=None,
               type=None, level=None, onlyaccess=False) -> db.orm.Query:
        """
        A not exposed helper function to get a subset of available datasets using filter
        """
        datasets: db.orm.Query = session.query(db.Dataset)
        if user:
            user = session.query(db.Person).get(user)
            datasets = datasets.filter_by(measured_by=user)
        if site and site!='NaN':
            site = session.query(db.Site).get(web.conv(int, site))
            datasets = datasets.filter_by(site=site)
        if date:
            date = web.parsedate(date)
            datasets = datasets.filter(
                db.Dataset.start <= date, db.Dataset.end >= date)
        if valuetype and valuetype!='NaN':
            vt = session.query(db.ValueType).get(web.conv(int, valuetype))
            datasets = datasets.filter_by(valuetype=vt)
        if instrument:
            if instrument in ('null', 'NaN'):
                source = None
            else:
                source = session.query(db.Datasource).get(int(instrument))
            datasets = datasets.filter_by(source=source)
        if type:
            datasets = datasets.filter_by(type=type)
        if level is not None:
            datasets = datasets.filter_by(level=level)
        if onlyaccess:
            lvl = users.current.level  # @UndefinedVariable
            datasets = datasets.filter(lvl >= db.Dataset.access)
        return datasets.join(db.ValueType).order_by(db.ValueType.name, db.sql.desc(db.Dataset.end))

    @expose_for()
    @web.method.get
    @web.mime.json
    def attrjson(self, attribute, valuetype=None, user=None,
                 site=None, date=None, instrument=None,
                 type=None, level=None, onlyaccess=False):
        """
        Gets the attributes for a dataset filter. Returns json. Used for many filters using ajax.
        e.g: Map filter, datasetlist, import etc.

        TODO: This function is not very well scalable. If the number of datasets grows,
        please use distinct to get the distinct sites / valuetypes etc.
        """
        if not hasattr(db.Dataset, attribute):
            raise AttributeError("Dataset has no attribute '%s'" % attribute)
        res = ''
        with db.session_scope() as session:
            # Get dataset for filter
            datasets = self.subset(session, valuetype, user,
                                   site, date, instrument,
                                   type, level, onlyaccess)

            # Make a set of the attribute items and cull out None elements
            items = set(getattr(ds, attribute)
                        for ds in datasets if ds is not None)

            # Not reasonable second iteration for eliminating None elements
            items = set(e for e in items if e)

            # Convert object set to json
            return web.json_out(sorted(items))

    @expose_for()
    @web.method.get
    @web.mime.json
    def attributes(self, valuetype=None, user=None, site=None, date=None, instrument=None,
                   type=None, level=None, onlyaccess=False):
        """
        Gets for each dataset attribute a unique list of values fitting to the filter

        Should replace multiple calls to attrjson
        """
        ds_attributes = ['valuetype', 'measured_by', 'site', 'source', 'type', 'level',
                          'uses_dst', 'timezone', 'project', 'quality']

        with db.session_scope() as session:
            # Get dataset for filter
            datasets = self.subset(session, valuetype, user,
                                   site, date, instrument,
                                   type, level, onlyaccess).all()

            # For each attribute iterate all datasets and find the unique values of the dataset
            result = {
                attr.strip('_'): sorted(
                    set(
                        getattr(ds, attr)
                        for ds in datasets
                    ),
                    key=lambda x: (x is not None, x)
                )
                for attr in ds_attributes
            }
            return web.json_out(result)


    @expose_for()
    @web.method.get
    @web.mime.json
    def json(self, valuetype=None, user=None, site=None,
             date=None, instrument=None, type=None,
             level=None, onlyaccess=False):
        """
        Gets a json file of available datasets with filter
        """
        with db.session_scope() as session:
            return web.json_out(self.subset(
                session, valuetype, user, site,
                date, instrument, type, level, onlyaccess
            ).all())

    @expose_for(group.editor)
    @web.method.post
    def updaterecorderror(self, dataset, records):
        """
        Mark record id (records) as is_error for dataset. Called by javascript
        """
        with db.session_scope() as session:
            recids = set(int(r) for r in records.split())
            ds = session.query(db.Dataset).get(int(dataset))
            q = ds.records.filter(db.Record.id.in_(recids))
            for r in q:
                r.is_error = True

    @expose_for(group.editor)
    @web.method.post
    def setsplit(self, datasetid, recordid):
        """
        Splits the datset at record id
        """
        try:
            with db.session_scope() as session:
                ds = session.query(db.Dataset).get(int(datasetid))
                rec = ds.records.filter_by(id=int(recordid)).first()
                ds, dsnew = ds.split(rec.time)
                if ds.comment:
                    ds.comment += '\n'
                ds.comment += ('splitted by ' + web.user() +
                               ' at ' + web.formatdate() +
                               '. New dataset is ' + str(dsnew))
                if dsnew.comment:
                    dsnew.comment += '\n'
                ds.comment += 'This dataset is created by a split done by ' + web.user() + ' at ' + web.formatdate() + \
                              '. Orignal dataset is ' + str(ds)
                return "New dataset: %s" % dsnew
        except:
            return traceback()

    @expose_for(group.logger)
    @web.method.get
    @web.mime.csv
    def records_csv(self, dataset, raw=False):
        """
        Exports the records of the timeseries as csv

        TODO: replace with export function with multiple formats using pandas
        """
        with db.session_scope() as session:
            ds = session.query(db.Dataset).get(dataset)
            st = io.BytesIO()
            st.write(codecs.BOM_UTF8)
            st.write(('"Dataset","ID","time","%s","site","comment"\n' %
                      (ds.valuetype)).encode('utf-8'))
            for r in ds.iterrecords(raw):
                d = dict(c=str(r.comment).replace('\r', '').replace('\n', ' / '),
                         v=r.calibrated if raw else r.value,
                         time=web.formatdate(r.time) + ' ' +
                              web.formattime(r.time),
                         id=r.id,
                         ds=ds.id,
                         s=ds.site.id)

                st.write(('%(ds)i,%(id)i,%(time)s,%(v)s,%(s)i,"%(c)s"\n' %
                          d).encode('utf-8'))
            session.close()
            return st.getvalue()

    @expose_for(group.logger)
    @web.method.get
    def plot(self, id, start='', end='', marker='', line='-', color='k', interactive=False):
        """
        Plots the dataset. Might be deleted in future. Rather use PlotPage
        """
        import pylab as plt
        with db.session_scope() as session:
            ds: db.Timeseries = session.query(db.Dataset).get(int(id))
            if users.current.level < ds.access:
                return f"""
                <div class="alert alert-danger"><h2>No access</h2><p class="lead">
                    Sorry, {users.current.name}, you need higher privileges to see the content of {ds}
                </p></div>
                """
            if start.strip():
                start = web.parsedate(start.strip())
            else:
                start = ds.start
            if end.strip():
                end = web.parsedate(end.strip())
            else:
                end = ds.end
            data = ds.asseries(start, end)
        fig = plt.figure(figsize=(10, 5))
        ax = fig.gca()
        data.plot.line(ax=ax, color=color, marker=marker, line=line)
        ax.grid()
        plt.xticks(rotation=15)
        plt.ylabel('%s [%s]' % (ds.valuetype.name, ds.valuetype.unit))
        plt.title(str(ds.site))

        bytesio = io.BytesIO()
        fig.savefig(bytesio, dpi=100, format='png')
        data = b64encode(bytesio.getvalue())
        return b'<img src="data:image/png;base64, ' + data + b'"/>'

    @web.expose
    @web.mime.json
    def records_json(self, dataset,
                     mindate=None, maxdate=None, minvalue=None, maxvalue=None,
                     threshold=None, limit=None, witherror=False) -> dict:
        """
        Returns the records of the dataset as JSON
        """
        with db.session_scope() as session:
            ds = session.query(db.Dataset).get(int(dataset))
            if users.current.level < ds.access:  # @UndefinedVariable
                raise web.HTTPError(403, 'User privileges not sufficient to access ds:' +
                                         str(dataset))
            records = ds.records.order_by(db.Record.time)
            if witherror:
                records = records.filter(~db.Record.is_error)
            tstart = web.parsedate(mindate.strip(), raiseerror=False)
            tend = web.parsedate(maxdate.strip(), raiseerror=False)
            threshold = web.conv(float, threshold)
            limit = web.conv(int, limit, 250)
            try:
                if threshold:
                    records = ds.findjumps(float(threshold), tstart, tend)
                else:
                    if tstart:
                        records = records.filter(db.Record.time >= tstart)
                    if tend:
                        records = records.filter(db.Record.time <= tend)
                    if minvalue:
                        records = records.filter(
                            db.Record.value > float(minvalue))
                    if maxvalue:
                        records = records.filter(
                            db.Record.value < float(maxvalue))
                    records = records.limit(limit)
            except:
                raise web.HTTPError(500, traceback())
            return web.json_out({'error': None, 'data': records.all()})

    @expose_for(group.editor)
    @web.method.get
    def records(self, dataset, mindate, maxdate, minvalue, maxvalue,
                threshold=None, limit=None, offset=None):
        """
        Returns a html-table of filtered records
        TODO: This method should be replaced by records_json. 
        Needs change in dataset-edit.html to create DOM elements using
        jquery from the delivered JSON
        """
        with db.session_scope() as session:
            ds = session.query(db.Dataset).get(int(dataset))
            records = ds.records.order_by(
                db.Record.time).filter(~db.Record.is_error)
            tstart = web.parsedate(mindate.strip(), raiseerror=False)
            tend = web.parsedate(maxdate.strip(), raiseerror=False)
            threshold = web.conv(float, threshold)
            limit = web.conv(int, limit, 250)
            try:
                if threshold:
                    records = ds.findjumps(float(threshold), tstart, tend)
                    currentcount = None
                    totalcount = None
                else:
                    if tstart:
                        records = records.filter(db.Record.time >= tstart)
                    if tend:
                        records = records.filter(db.Record.time <= tend)
                    if minvalue:
                        records = records.filter(db.Record.value > float(minvalue))
                    if maxvalue:
                        records = records.filter(db.Record.value < float(maxvalue))
                    totalcount = records.count()
                    if offset:
                        records = records.offset(offset)
                    if limit:
                        records = records.limit(limit)
                    currentcount = records.count()
            except:
                return web.literal('<div class="error">' + traceback() + '</div>')
            res = web.render('record.html', records=records, currentcount=currentcount,
                             totalrecords=totalcount, dataset=ds, actionname="split dataset",
                             action="/dataset/setsplit",
                             action_help='/wiki/dataset/split').render()
            return res

    @expose_for(group.editor)
    @web.method.get
    @web.mime.png
    def plot_coverage(self, siteid):
        """
        Makes a bar plot (ganntt like) for the time coverage of datasets at a site
        """
        st = io.BytesIO()
        with db.session_scope() as session:
            import matplotlib
            matplotlib.use('Agg', warn=False)
            import pylab as plt
            import numpy as np
            ds = session.query(db.Dataset).filter_by(_site=int(siteid)).order_by(
                db.Dataset._source, db.Dataset._valuetype, db.Dataset.start).all()
            left = plt.date2num([d.start for d in ds])
            right = plt.date2num([d.end for d in ds])
            btm = np.arange(-.5, -len(ds), -1)
            # return 'left=' + str(left) + ' right=' + str(right) + ' btm=' + str(btm)
            fig = plt.figure()
            ax = fig.gca()
            ax.barh(left=left, width=right - left, bottom=btm,
                    height=0.9, fc='0.75', ec='0.5')
            for l, b, d in zip(left, btm, ds):
                ax.text(l, b + .5, '#%i' % d.id, color='k', va='center')
            ax.xaxis_date()
            ax.set_yticks(btm + .5)
            ax.set_yticklabels(
                [d.source.name + '/' + d.valuetype.name for d in ds])
            ax.set_position([0.3, 0.05, 0.7, 0.9])
            ax.set_title('Site #' + siteid)
            ax.set_ylim(-len(ds) - .5, .5)
            ax.grid()
            fig.savefig(st, dpi=100)
        return st.getvalue()

    @expose_for(group.editor)
    @web.method.post
    def create_transformation(self, sourceid):
        """
        Creates a transformed timeseries from a timeseries. 
        Redirects to the new transformed timeseries
        """
        id = int(sourceid)
        try:
            with db.session_scope() as session:
                sts = session.query(db.Timeseries).get(id)
                id = db.newid(db.Dataset, session)
                tts = db.TransformedTimeseries(
                    id=id,
                    site=sts.site,
                    source=sts.source,
                    filename=sts.filename,
                    name=sts.name,
                    expression='x',
                    latex='x',
                    comment=sts.comment,
                    _measured_by=web.user(),
                    quality=sts.quality,
                    valuetype=sts.valuetype,
                    start=sts.start,
                    end=sts.end
                )
                session.add(tts)
                tts.sources.append(sts)
        except Exception as e:
            return str(e)
        return 'goto:/dataset/%s' % id

    @expose_for(group.editor)
    @web.method.post
    def transform_removesource(self, transid, sourceid):
        """
        Remove a source from a transformed timeseries. 
        To be called from javascript. Client handles rendering
        """
        try:
            with db.session_scope() as session:
                tts = session.query(db.TransformedTimeseries).get(int(transid))
                sts = session.query(db.Timeseries).get(int(sourceid))
                tts.sources.remove(sts)
                tts.updatetime()
        except Exception as e:
            return str(e)

    @expose_for(group.editor)
    @web.method.post
    def transform_addsource(self, transid, sourceid):
        """
        Adds a source to a transformed timeseries. 
        To be called from javascript. Client handles rendering
        """
        try:
            with db.session_scope() as session:
                tts = session.query(db.TransformedTimeseries).get(int(transid))
                sts = session.query(db.Timeseries).get(int(sourceid))
                tts.sources.append(sts)
                tts.updatetime()
        except Exception as e:
            return str(e)


    @expose_for(group.editor)
    @web.method.get
    @web.mime.json
    def calibration_source_info(self, targetid, sourceid=None, limit=None, max_source_count=100):
        """
        Returns the calibration properties for a calibration proposal

        Parameters
        ----------
        targetid
            Dataset id, which should get calibrated
        sourceid
            Dataset id containing the "real" measurements
        limit
            Tolarated time gap between records of the target and records of the source
        max_source_count: int
            Do not perform calibration if there are more records in the source (to prevent long calculation times)
        """
        with db.session_scope() as session:
            error = ''
            target = session.query(db.Dataset).get(int(targetid))
            if sourceid:
                sourceid = int(sourceid)
                source_ds: db.Dataset = session.query(db.Dataset).get(sourceid)
                unit = source_ds.valuetype.unit
            else:
                unit = '?'
            limit = web.conv(int, limit, 3600)
            day = timedelta(days=1)
            count = 0
            result = None

            try:
                if sourceid:
                    source = CalibrationSource(
                        [sourceid], target.start - day, target.end + day)

                    sourcerecords = source.records(session)
                    count = sourcerecords.count()

                    if count and count < web.conv(int, max_source_count, 0):
                        result = Calibration(target, source, limit)
                        if not result:
                            error = 'No matching records for the given time limit is found'
            except:
                error = traceback()

            return web.as_json(
                targetid=targetid,
                sourceid=sourceid,
                error=error,
                count=count,
                unit=unit,
                limit=limit,
                result=result
            ).encode('utf-8')

    @expose_for(group.editor)
    @web.method.post
    def apply_calibration(self, targetid, sourceid, slope, offset):
        """
        Applies calibration to dataset.

        """
        error = ''
        try:
            with db.session_scope() as session:
                target: db.Dataset = session.query(db.Dataset).get(int(targetid))
                source = session.query(db.Dataset).get(int(sourceid))
                target.calibration_slope = float(slope)
                target.calibration_offset = float(offset)
                target.valuetype = source.valuetype
                if target.comment:
                    target.comment += '\n'
                target.comment += ("Calibrated against {} at {} by {}"
                                   .format(source, web.formatdate(), users.current))
        except:
            error = traceback()
        return error


