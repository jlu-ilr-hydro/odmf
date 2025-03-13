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
from ..auth import Level, expose_for, users
import codecs
from ...db.calibration import Calibration, CalibrationSource
from ...config import conf
from pytz import common_timezones
import cherrypy
import pandas as pd


def get_ds(session, datasetid):
    """
    Gets a dataset from an id
    """
    return session.get(db.Dataset, int(datasetid))


def has_access(ds: db.Dataset, level:Level=Level.guest):
    return ds.get_access_level(users.current) >= max(ds.access, level)

@cherrypy.popargs('datasetid')
@web.show_in_nav_for(1, icon='clipboard')
class DatasetPage:
    """
    Serves the direct dataset manipulation and querying
    """
    exposed = True


    @expose_for()
    @web.method.get
    def index(self, datasetid=None, error='', message=None):
        """
        Returns the query page (datasetlist.html). Site logic is handled with ajax
        """
        if datasetid is None:
            return web.render('dataset/datasetlist.html').render()
        else:
            with db.session_scope() as session:
                active = get_ds(session, datasetid)
                if active:  # save requested dataset as 'last'
                    web.cherrypy.session['dataset'] = datasetid  # @UndefinedVariable
                    return self.render_dataset(session, active, error=error, message=message)
                else:
                    raise web.redirect(conf.root_url + '/dataset', error=f'No ds{datasetid} available')
    @expose_for(Level.editor)
    def new(self, site_id=None, vt_id=None, user=None, error='', _=None, template=None):
        active = None
        with db.session_scope() as session:
            if template:
                template_ds = session.get(db.Timeseries, template)
                if not template_ds:
                    error=f'Dataset {template} not found - cannot use as a template'
                else:
                    active = template_ds.copy(db.newid(db.Dataset, session))
            else:
                site = session.get(db.Site, site_id) if site_id else None
                valuetype = session.get(db.ValueType, vt_id) if vt_id else None
                # All projects

                if user is None:
                    user = web.user()
                user: db.Person = session.get(db.Person, user) if user else None

            active = active or db.Timeseries(
                id=db.newid(db.Dataset, session),
                name='New Dataset',
                site=site,
                valuetype=valuetype,
                measured_by=user,
                access=user.access_level,
                timezone=conf.datetime_default_timezone,
                calibration_offset=0,
                calibration_slope=1
            )
            return self.render_dataset(session, active, error=error)

    def render_dataset(self, session, active: db.Dataset, message='', error=''):
        """
        Returns the dataset view and manipulation page (dataset-edit.html).
        Expects a valid dataset id, 'new' or 'last'. With new, a new dataset
        is created, if 'last' the last chosen dataset is taken   
        """
        if error:
            web.session.error = error
        if message:
            web.session.success = message

        def access(level: Level=Level.guest):
            return has_access(active, level)
        # Render the resulting page
        return web.render(
            'dataset/dataset-edit.html',
            # activedataset is the current dataset (id or new)
            ds_act=active, n=active.size(), access=access,
            # All available timezones
            timezones=common_timezones + ['Fixed/60'],
            # The title of the page
            title=f'ds{active.id}',
            # A couple of prepared queries to fill select elements
            valuetypes=session.query(db.ValueType).order_by(db.ValueType.name),
            persons=session.query(db.Person).order_by(db.Person.can_supervise.desc(), db.Person.surname),
            sites=session.query(db.Site).order_by(db.Site.id),
            quality=session.query(db.Quality).order_by(db.Quality.id),
            datasources=session.query(db.Datasource),
            projects=session.query(db.Project),
            same_time_ds=self.parallel_datasets(session, active),
            alarms=session.query(db.timeseries.DatasetAlarm).filter_by(dsid=active.id),
            topics=session.query(db.message.Topic).order_by(db.message.Topic.name),
        ).render()

    @staticmethod
    def parallel_datasets(session, active: db.Timeseries):
        # parallel dataset (same site and same time, different type)
        if active.site and active.start and active.end:
            return session.query(db.Dataset).filter_by(site=active.site).filter(
                db.Dataset.start <= active.end, db.Dataset.end >= active.start).filter(db.Dataset.id != active.id)
        else:
            return []

    @expose_for(Level.editor)
    def alarm(self, datasetid, **kwargs):
        """
        Adds or changes DatasetAlarm objects to send messages when a condition is met.
        """
        from ...db.timeseries import DatasetAlarm
        success = ''
        with db.session_scope() as session:
            ds = session.get(db.Dataset, datasetid)
            if not ds:
                error = f'Dataset {datasetid} not found'
                raise web.redirect(conf.url('dataset'), error=error)
            if cherrypy.request.method == 'GET':
                alarms = session.scalars(db.sql.select(db.timeseries.DatasetAlarm).filter_by(dsid=ds.id)).all()
                web.mime.json.set()
                return web.as_json(alarms).encode('utf-8')
            elif cherrypy.request.method == 'POST':
                alarm = session.get(DatasetAlarm, kwargs.get('id'))
                if not alarm:
                    alarm = DatasetAlarm(dataset=ds)
                    session.add(alarm)
                    session.flush()
                    success = 'New alarm: '
                else:
                    success = 'Alarm changed: '

                alarm.active = web.conv(bool, kwargs.get('active'))
                alarm.aggregation_function = web.conv(str, kwargs.get('aggregation_function'))
                try:
                    alarm.aggregation_time = pd.to_timedelta(kwargs.get('aggregation_time')).total_seconds() / 86400
                except (ValueError, AttributeError):
                    raise web.redirect(conf.url('dataset', datasetid, '#alarms'), error=str(kwargs.get('aggregation_time')) + ' is no timespan value')
                if kwargs.get('threshold_value'):
                    if kwargs.get('threshold_type') == 'above':
                        alarm.threshold_above = web.conv(float, kwargs.get('threshold_value'))
                    else:
                        alarm.threshold_below = web.conv(float, kwargs.get('threshold_value'))

                topic = session.get(db.message.Topic, kwargs.get('topic'))
                if topic:
                    alarm.topic = topic
                session.flush()
                if any(v is None for v in [alarm.aggregation_function, alarm.aggregation_time, alarm.topic, alarm.active, alarm.dataset]):
                    raise web.redirect(conf.url('dataset', datasetid, '#alarms'), error='Alarm is missing values')
                success += str(alarm)
        raise web.redirect(conf.url('dataset', datasetid, '#alarms'), success=success)




    @expose_for(Level.editor)
    @web.method.post
    def save(self, **kwargs):
        """
        Saves the changes for an edited dataset
        """
        try:
            # Get current dataset
            id = web.conv(int, kwargs.get('id'), '')
        except:
            raise web.redirect(conf.root_url + f'/dataset/{id}', error=traceback())
        # if save button has been pressed for submitting the dataset
        if 'save' in kwargs:
            # get database session
            with db.session_scope() as session:
                try:
                    pers = session.get(db.Person, kwargs.get('measured_by'))
                    vt = session.get(db.ValueType, kwargs.get('valuetype'))
                    q = session.get(db.Quality, kwargs.get('quality'))
                    s = session.get(db.Site, kwargs.get('site'))
                    src = session.get(db.Datasource, kwargs.get('source'))

                    # get the dataset
                    ds = get_ds(session, id)
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

                    if ds.get_access_level(users.current) >= Level.admin:
                        project = session.get(db.Project, kwargs.get('project'))
                        ds.project = project

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

                    session.add(ds)
                    session.flush()
                    if not has_access(ds, Level.editor):
                        raise web.HTTPError(403, 'No sufficient rights to alter dataset')
                except:
                    # On error render the error message
                    raise web.redirect(conf.root_url + f'/dataset/{id}', error=traceback())
        elif 'new' in kwargs:
            id = 'new'
        # reload page
        raise web.redirect(conf.root_url + f'/dataset/{id}')

    @expose_for()
    @web.method.get
    @web.mime.json
    def statistics(self, datasetid):
        """
        Returns a json file holding the statistics for the dataset (is loaded by page using ajax)
        """
        with db.session_scope() as session:
            ds = get_ds(session, datasetid)
            if ds:
                # Get statistics
                mean, std, n = ds.statistics()
                # Convert to json
                return web.json_out(dict(mean=mean, std=std, n=n))
            else:
                # Return empty dataset statistics
                return web.json_out(dict(mean=0, std=0, n=0))

    @expose_for(Level.editor)
    @web.method.post_or_delete
    def remove(self, datasetid):
        """
        Removes a dataset. Called by javascript, page reload handled by client
        """
        with db.session_scope() as session:
            ds = get_ds(session, datasetid)
            if has_access(ds, Level.admin):
                try:
                    db.removedataset(datasetid)
                    return None
                except Exception as e:
                    return str(e)
            else:
                return f'Cannot remove {datasetid} - not admin or owner'

    def subset(self, session, valuetype=None, user=None,
               site=None, date=None, instrument=None,
               dstype=None, level=None, onlyaccess=False, project=None) -> db.orm.Query:
        """
        A not exposed helper function to get a subset of available datasets using filter
        """
        datasets: db.orm.Query = session.query(db.Dataset)
        if user:
            user = session.get(db.Person, user)
            datasets = datasets.filter_by(measured_by=user)
        if project and project!='NaN':
            datasets = datasets.filter_by(_project=int(project))
        if site and site!='NaN':
            site = session.get(db.Site, web.conv(int, site))
            datasets = datasets.filter_by(site=site)
        if date:
            date = web.parsedate(date)
            datasets = datasets.filter(
                db.Dataset.start <= date,
                db.Dataset.end >= date
            )
        if valuetype and valuetype!='NaN':
            vt = session.get(db.ValueType, web.conv(int, valuetype))
            datasets = datasets.filter_by(valuetype=vt)
        if instrument:
            if instrument in ('null', 'NaN'):
                source = None
            else:
                source = session.get(db.Datasource, int(instrument))
            datasets = datasets.filter_by(source=source)
        if dstype:
            datasets = datasets.filter_by(type=type)
        if level is not None:
            datasets = datasets.filter_by(level=level)
        if onlyaccess:
            lvl = users.current.level  # @UndefinedVariable
            datasets = datasets.filter(lvl >= db.Dataset.access)
        return datasets

    @expose_for()
    @web.method.get
    @web.mime.json
    def attributes(self, valuetype=None, user=None, site=None, date=None, instrument=None,
                   dstype=None, level=None, project=None, onlyaccess=False):
        """
        Gets for each dataset attribute a unique list of values fitting to the filter

        Should replace multiple calls to attrjson
        """
        ds_attributes = ['project', 'valuetype', 'measured_by', 'site', 'source', 'type', 'level',
                         'uses_dst', 'timezone', 'project', 'quality']
        entities = {
            'level': db.Dataset.level,
            'valuetype' : db.ValueType,
            'measured_by': db.Person,
            'site': db.Site,
            'source': db.Datasource,
            'type': db.Dataset.type,
            'uses_dst': db.Dataset.uses_dst,
            'timezone': db.Dataset.timezone,
            'project': db.Project,
            'quality': db.Quality
        }
        import time

        def untuple(obj):
            try:
                obj_single, = obj
                return obj_single
            except (TypeError, ValueError):
                return obj

        def get_entity(q, entity):
            if isinstance(entity, type):
                qq = sorted(q.join(entity).with_entities(entity).distinct())
            else:
                qq = q.with_entities(entity).distinct().order_by(entity)
            return qq

        with db.session_scope() as session:
            # Get dataset for filter
            datasets = self.subset(session, valuetype, user,
                                   site, date, instrument,
                                   dstype, level, onlyaccess, project)
            t = time.time()
            # This is not really working by now, don't understand with_entities completely
            result = {
                attr : [untuple(o) for o in get_entity(datasets, entity)]
                for attr, entity in entities.items()
            }
            result['count'] = datasets.count()
            result['time'] = time.time() - t
            # print('Attributes in {:0.3f}s'.format(time.time() - t))
            return web.json_out(result)


    @expose_for()
    @web.method.get
    @web.mime.json
    def json(self, valuetype=None, user=None, site=None,
             date=None, instrument=None, dstype=None,
             level=None, project=None, onlyaccess=False, limit=None, page=None):
        """
        Gets a json file of available datasets with filter
        """
        me =users.current
        def ds_to_json_with_access(ds: db.Dataset):
            return ds.__jdict__() | {'accesslevel': ds.get_access_level(me).name}

        with db.session_scope() as session:
            dataset_q = self.subset(
                session, valuetype, user, site,
                date, instrument, dstype, level, onlyaccess, project
            ).order_by(db.Dataset.id)
            count = dataset_q.count()
            if limit:
                dataset_q = dataset_q.limit(int(limit))

            if page:
                dataset_q = dataset_q.offset((int(page) - 1) * int(limit))

            datasets = [ds_to_json_with_access(ds) for ds in dataset_q]

            return web.json_out({
                'datasets': datasets,
                'count': count,
                'limit': limit,
                'page': page
            })
    @expose_for()
    @web.method.post
    @web.mime.xlsx
    def to_excel(self, valuetype=None, user=None, site=None,
             date=None, instrument=None, dstype=None,
             level=None, project=None, onlyaccess=False, limit=None, page=None):
        """Exports the current dataset list as an excel file"""
        import pandas as pd
        from ...tools.exportdatasets import serve_dataframe
        with db.session_scope() as session:
            dataset_q = self.subset(
                session, valuetype, user, site,
                date, instrument, dstype, level, onlyaccess, project
            ).order_by(db.Dataset.id)
            if limit:
                dataset_q = dataset_q.limit(int(limit))
            if page:
                dataset_q = dataset_q.offset((int(page) - 1) * int(limit))
            datasets = pd.read_sql(dataset_q.statement, session.bind)
            name = f'datasets-{datetime.now():%Y-%m-%d}.xlsx'
            return serve_dataframe(datasets, name)


    @expose_for(Level.editor)
    @web.method.post
    def updaterecorderror(self, dataset, records):
        """
        Mark record id (records) as is_error for dataset. Called by javascript
        """
        with db.session_scope() as session:
            recids = set(int(r) for r in records.split())
            ds = session.get(db.Dataset, int(dataset))
            q = ds.records.filter(db.Record.id.in_(recids))
            for r in q:
                r.is_error = True

    @expose_for(Level.editor)
    @web.method.post
    def setsplit(self, datasetid, recordid):
        """
        Splits the datset at record id
        """
        try:
            with db.session_scope() as session:
                ds = session.get(db.Dataset, int(datasetid))
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

    @expose_for(Level.logger)
    @web.method.get
    @web.mime.csv
    def records_csv(self, dataset, raw=False):
        """
        Exports the records of the timeseries as csv

        TODO: replace with export function with multiple formats using pandas
        """
        with db.session_scope() as session:
            ds = session.get(db.Dataset, dataset)
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

    @expose_for(Level.logger)
    @web.method.post
    def plot(self, id, start='', end='', marker='', line='-', color='k', interactive=False):
        """
        Plots the dataset. Might be deleted in future. Rather use PlotPage
        """
        import pylab as plt
        try:
            with db.session_scope() as session:
                ds: db.Timeseries = session.get(db.Dataset, int(id))
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
                ylabel = f'{ds.valuetype.name} [{ds.valuetype.unit}]'
                title = f'{ds.site}'

            fig = plt.figure(figsize=(10, 5))
            ax = fig.gca()
            data.plot.line(ax=ax, color=color, marker=marker, linestyle=line)
            ax.grid()
            plt.xticks(rotation=15)
            plt.ylabel(ylabel)
            plt.title(title)

            bytesio = io.BytesIO()
            fig.savefig(bytesio, dpi=100, format='png')
            data = b64encode(bytesio.getvalue())
            return b'<img src="data:image/png;base64, ' + data + b'"/>'
        except Exception as e:
            raise web.AJAXError(500, str(e))

    @web.expose
    @web.mime.json
    def records_json(self, dataset,
                     mindate=None, maxdate=None, minvalue=None, maxvalue=None,
                     threshold=None, limit=None, witherror=False) -> dict:
        """
        Returns the records of the dataset as JSON
        """
        with db.session_scope() as session:
            ds = session.get(db.Dataset, int(dataset))
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

    @expose_for(Level.editor)
    @web.method.post
    def records(self, dataset, mindate, maxdate, minvalue, maxvalue,
                threshold=None, limit=None, offset=None):
        """
        Returns a htms-table of filtered records
        TODO: This method should be replaced by records_json. 
        Needs change in dataset-edit.html to create DOM elements using
        jquery from the delivered JSON
        """
        with db.session_scope() as session:
            ds = session.get(db.Dataset, int(dataset))
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
                return web.literal('<div class="alert alert-danger">' + traceback() + '</div>')
            return web.render('dataset/record.html', records=records, currentcount=currentcount,
                             totalrecords=totalcount, dataset=ds, actionname="split dataset",
                             action="/dataset/setsplit",
                             action_help=f'{conf.root_url}/download/wiki/dataset/split.wiki').render()

    @expose_for(Level.logger)
    @web.method.post
    def add_record(self, dataset, time, value, id=None, sample=None, comment=None):
        """
        Adds a single record to a dataset, great for connected fieldwork
        :param dataset: Dataset id
        :param time: Datetime
        :param value: the value
        :param sample: A sample name (usually None)
        :param comment: A comment (often None)
        :return:
        """
        with db.session_scope() as session:
            ds: db.Timeseries = session.get(db.Dataset, int(dataset))
            if not has_access(ds, Level.editor):
                raise web.HTTPError(403, 'Not allowed')
            time = web.parsedate(time)
            ds.addrecord(id, value, time, comment, sample, out_of_timescope_ok=True)
        raise web.redirect(str(dataset) + '/#add-record', success='record added')



    @expose_for(Level.editor)
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

    @expose_for(Level.editor)
    @web.method.post
    def create_transformation(self, sourceid):
        """
        Creates a transformed timeseries from a timeseries. 
        Redirects to the new transformed timeseries
        """
        id = int(sourceid)
        try:
            with db.session_scope() as session:
                sts = session.get(db.Timeseries, id)
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
            raise web.AJAXError(500, str(e))
        return '/dataset/%s' % id

    @expose_for(Level.editor)
    @web.method.post
    def transform_removesource(self, transid, sourceid):
        """
        Remove a source from a transformed timeseries. 
        To be called from javascript. Client handles rendering
        """
        try:
            with db.session_scope() as session:
                tts = session.get(db.TransformedTimeseries, int(transid))
                sts = session.get(db.Timeseries, int(sourceid))
                tts.sources.remove(sts)
                tts.updatetime()
        except Exception as e:
            return str(e)

    @expose_for(Level.editor)
    @web.method.post
    def transform_addsource(self, transid, sourceid):
        """
        Adds a source to a transformed timeseries. 
        To be called from javascript. Client handles rendering
        """
        try:
            with db.session_scope() as session:
                tts = session.get(db.TransformedTimeseries, int(transid))
                sts = session.get(db.Timeseries, int(sourceid))
                tts.sources.append(sts)
                tts.updatetime()
        except Exception as e:
            return str(e)


    @expose_for(Level.editor)
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
            target = session.get(db.Dataset, int(targetid))
            if sourceid:
                sourceid = int(sourceid)
                source_ds: db.Dataset = session.get(db.Dataset, sourceid)
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

    @expose_for(Level.editor)
    @web.method.post
    def apply_calibration(self, targetid, sourceid, slope, offset):
        """
        Applies calibration to dataset.

        """
        error = ''
        try:
            with db.session_scope() as session:
                target: db.Dataset = session.get(db.Dataset, int(targetid))
                source = session.get(db.Dataset, int(sourceid))
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


