'''
Created on 18.07.2012

@author: philkraf
'''
from . import lib as web
from .. import db
from traceback import format_exc as traceback
from datetime import datetime, timedelta
import io
from .auth import group, expose_for, users
import codecs
from ..tools.calibration import Calibration, CalibrationSource
from pytz import common_timezones
import cherrypy

from pprint import pprint


class DatasetPage:
    """
    Serves the direct dataset manipulation and querying
    """
    exposed = True

    @expose_for(group.guest)
    def index(self):
        """
        Returns the query page (datasetlist.html). Site logic is handled with ajax
        """
        return web.render('datasetlist.html').render('html', doctype='html')

    @expose_for(group.guest)
    def default(self, id='new', site_id=None, vt_id=None, user=None):
        """
        Returns the dataset view and manipulation page (datasettab.html). 
        Expects an valid dataset id, 'new' or 'last'. With new, a new dataset
        is created, if 'last' the last chosen dataset is taken   
        """
        if id == 'last':
            # get the last viewed dataset from web-session. If there is no
            # last dataset, redirect to index
            id = web.cherrypy.session.get('dataset')  # @UndefinedVariable
            if id is None:
                raise web.HTTPRedirect('/dataset/')
        session = db.Session()
        error = ''
        datasets = {}
        try:
            site = session.query(db.Site).get(site_id) if site_id else None
            valuetype = session.query(db.ValueType).get(
                vt_id) if vt_id else None
            # All projects

            if user is None:
                user = web.user()
            user = session.query(db.Person).get(user) if user else None
            if id == 'new':
                active = db.Timeseries(id=db.newid(db.Dataset, session), name='New Dataset',
                                       site=site, valuetype=valuetype, measured_by=user)
            else:  # Else load requested dataset
                active = session.query(db.Dataset).get(int(id))

                if active:  # save requested dataset as 'last'
                    web.cherrypy.session['dataset'] = id  # @UndefinedVariable
                else:
                    raise ValueError("Dataset %s is not existent" % (id))

            # Setting the project, for editing and ui navigation
            if active.project is not None:
                project = session.query(db.Project).get(int(active.project))
            else:
                project = None

            try:
                # load data for datasettab.html:
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
            queries = dict(
                valuetypes=session.query(db.ValueType).order_by(db.ValueType.name),
                persons=session.query(db.Person).order_by(db.Person.can_supervise.desc(), db.Person.surname),
                sites=session.query(db.Site).order_by(db.Site.id),
                quality=session.query(db.Quality).order_by(db.Quality.id),
                datasources=session.query(db.Datasource),
                projects=session.query(db.Project),
            )
            result = web.render('datasettab.html',
                                # activedataset is the current dataset (id or new)
                                activedataset=active,
                                # Render error messages
                                error=error,
                                # similar and parallel datasets
                                datasets=datasets,
                                # the db module for queries during rendering
                                db=db,
                                # The project
                                activeproject=project,
                                # All available timezones
                                timezones=common_timezones + ['Fixed/60'],
                                # The title of the page
                                title='ds' + str(id),
                                # A couple of prepared queries to fill select elements
                                **queries
                                ).render('html', doctype='html')
        except:
            # If anything above fails, render error message
            result = web.render('datasettab.html',
                                # render traceback as error
                                error=traceback(),
                                # a title
                                title='Schwingbach-Datensatz (Fehler)',
                                # See above
                                session=session,
                                datasets=datasets,
                                db=db,
                                activedataset=None,
                                **queries
                                ).render('html', doctype='html')
        finally:
            session.close()
        return result

    @expose_for(group.editor)
    @web.postonly
    @web.json_in()
    def new_json(self):
        kwargs = cherrypy.request.json
        with db.session_scope() as session:
            try:
                pers = session.query(db.Person).get(kwargs.get('measured_by'))
                vt = session.query(db.ValueType).get(kwargs.get('valuetype'))
                q = session.query(db.Quality).get(kwargs.get('quality'))
                s = session.query(db.Site).get(kwargs.get('site'))
                src = session.query(db.Datasource).get(kwargs.get('source'))

                ds = db.Timeseries(id=id)
                # Get properties from the keyword arguments kwargs
                ds.site = s
                ds.filename = kwargs.get('filename')
                ds.name = kwargs.get('name')
                ds.comment = kwargs.get('comment')
                ds.measured_by = pers
                ds.valuetype = vt
                ds.quality = q

                # TODO: Is it necessary to protect this of being modified by
                # somebody who isn't a supervisor or higher?
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
                        ds.start = datetime.strptime(
                            kwargs['start'], '%d.%m.%Y')
                    if kwargs.get('end'):
                        ds.end = datetime.strptime(kwargs['end'], '%d.%m.%Y')
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
                return web.render('empty.html', error=traceback(), title='Dataset #%s' % id
                                  ).render('html', doctype='html')

    @expose_for(group.editor)
    @web.postonly
    def addrecord_json(self, dsid, recid, time, value,
                       sample=None, comment=None):
        with db.session_scope() as session:
            try:
                ds = session.query(db.Timeseries).get(int(dsid))
                if not ds:
                    return 'Timeseries ds:{} does not exist'.format(dsid)
                ds.addrecord(Id=int(recid), time=time, value=value, comment=comment, sample=sample)
            except:
                return 'Could not add record, error:\n' + traceback()

    @expose_for(group.editor)
    def saveitem(self, **kwargs):
        """
        Saves the changes for an edited dataset
        """
        try:
            # Get current dataset
            id = web.conv(int, kwargs.get('id'), '')
        except:
            return web.render(error=traceback(), title='Dataset #%s' % kwargs.get('id')
                              ).render('html', doctype='html')
        # if save button has been pressed for submitting the dataset
        if 'save' in kwargs:
            try:
                # get database session
                session = db.Session()
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
                        ds.start = datetime.strptime(
                            kwargs['start'], '%d.%m.%Y')
                    if kwargs.get('end'):
                        ds.end = datetime.strptime(kwargs['end'], '%d.%m.%Y')
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
                return web.render('empty.html', error=traceback(), title='Dataset #%s' % id
                                  ).render('html', doctype='html')
            finally:
                session.close()
        elif 'new' in kwargs:
            id = 'new'
        # reload page
        raise web.HTTPRedirect('./%s' % id)

    @expose_for()
    def statistics(self, id):
        """
        Returns a json file holding the statistics for the dataset (is loaded by page using ajax)
        """
        web.setmime(web.mime.json)
        session = db.Session()
        ds = session.query(db.Dataset).get(int(id))
        if ds:
            # Get statistics
            mean, std, n = ds.statistics()
            # Convert to json
            res = web.as_json(dict(mean=mean, std=std, n=n))
        else:
            # Return empty dataset statistics
            res = web.as_json(dict(mean=0, std=0, n=0))
        return res

    @expose_for(group.admin)
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
               type=None, level=None, onlyaccess=False):
        """
        A not exposed helper function to get a subset of available datasets using filter
        """
        datasets = session.query(db.Dataset)
        if user:
            user = session.query(db.Person).get(user)
            datasets = datasets.filter_by(measured_by=user)
        if site:
            site = session.query(db.Site).get(int(site))
            datasets = datasets.filter_by(site=site)
        if date:
            date = web.parsedate(date)
            datasets = datasets.filter(
                db.Dataset.start <= date, db.Dataset.end >= date)
        if valuetype:
            vt = session.query(db.ValueType).get(int(valuetype))
            datasets = datasets.filter_by(valuetype=vt)
        if instrument:
            if instrument == 'null':
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
    def attrjson(self, attribute, valuetype=None, user=None,
                 site=None, date=None, instrument=None,
                 type=None, level=None, onlyaccess=False):
        """
        Gets the attributes for a dataset filter. Returns json. Used for many filters using ajax.
        e.g: Map filter, datasetlist, import etc.

        TODO: This function is not very well scalable. If the number of datasets grows,
        please use distinct to get the distinct sites / valuetypes etc.
        """
        web.setmime('application/json')
        if not hasattr(db.Dataset, attribute):
            raise AttributeError("Dataset has no attribute '%s'" % attribute)
        session = db.Session()
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
            res = web.as_json(sorted(items))
        return res

    @expose_for()
    def json(self, valuetype=None, user=None, site=None,
             date=None, instrument=None, type=None,
             level=None, onlyaccess=False):
        """
        Gets a json file of available datasets with filter
        """
        web.setmime('application/json')
        session = db.Session()
        try:
            dump = web.as_json(self.subset(session, valuetype, user, site,
                                           date, instrument, type, level, onlyaccess).all())
        finally:
            session.close()
        return dump

    @expose_for(group.editor)
    def updaterecorderror(self, dataset, records):
        """
        Mark record id (records) as is_error for dataset. Called by javascript
        """
        try:
            recids = set(int(r) for r in records.split())
            session = db.Session()
            ds = session.query(db.Dataset).get(int(dataset))
            q = ds.records.filter(db.Record.id.in_(recids))
            for r in q:
                r.is_error = True
            session.commit()
            session.close()
        except:
            return traceback()

    @expose_for(group.editor)
    def setsplit(self, datasetid, recordid):
        """
        Splits the datset at record id
        """
        try:
            session = db.Session()
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
            res = "New dataset: %s" % dsnew
        except:
            res = traceback()
        finally:
            session.close()
        return res

    @expose_for(group.logger)
    def records_csv(self, dataset, raw=False):
        """
        Exports the records of the timeseries as csv
        """
        web.setmime('text/csv')
        session = db.Session()
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
    def multirecords_csv(self, valuetype=None, user=None, site=None,
                         date=None, instrument=None,
                         type=None, level=None, onlyaccess=False,
                         witherrors=False):
        web.setmime('text/csv')
        session = db.scoped_session()
        datasets = self.subset(session, valuetype, user,
                               site, date, instrument,
                               type, level, onlyaccess)
        datagroup = db.DatasetGroup([ds.id for ds in datasets])
        st = io.BytesIO()
        st.write(codecs.BOM_UTF8)
        st.write(('"Dataset","ID","time","{vt} calibrated","{vt} raw",' +
                  '"site","comment","is error?"\n')
                 .format(vt=ds.valuetype)
                 .encode('utf-8'))
        for r in datagroup.iterrecords(session, witherrors):
            d = dict(
                c=(str(r.comment).replace('\r', '').replace(
                    '\n', ' / ')) if r.comment else '',
                vc=r.value if witherrors and not r.is_error else '',
                vr=r.rawvalue,
                time=web.formatdate(r.time) + ' ' + web.formattime(r.time),
                id=r.id,
                ds=ds.id,
                s=ds.site.id,
                e=int(r.is_error))
            st.write(('{ds:i},{id:i},{time},{vc:s0,{vr:s},{s:i},' +
                      '"{c}",{e}\n').format(**d).encode('utf-8'))
        session.close()
        return st.getvalue()

    @expose_for(group.logger)
    def plot(self, id, start=None, end=None, marker='', line='-', color='k'):
        """
        Plots the dataset. Might be deleted in future. Rather use PlotPage
        """
        web.setmime('image/png')
        session = db.Session()
        try:
            import matplotlib
            matplotlib.use('Agg', warn=False)
            import pylab as plt
            ds = session.query(db.Dataset).get(int(id))
            if start:
                start = web.parsedate(start.strip())
            else:
                start = ds.start
            if end:
                end = web.parsedate(end.strip())
            else:
                end = ds.end
            t, v = ds.asarray(start, end)
            fig = plt.figure()
            ax = fig.gca()
            ax.plot_date(t, v, color + marker + line)
            bytesio = io.BytesIO()
            ax.grid()
            plt.xticks(rotation=15)
            plt.ylabel('%s [%s]' % (ds.valuetype.name, ds.valuetype.unit))
            plt.title(str(ds.site))
            fig.savefig(bytesio, dpi=100, format='png')
        finally:
            session.close()
        return bytesio.getvalue()

    @web.expose
    @web.mimetype(web.mime.json)
    def records_json(self, dataset,
                     mindate=None, maxdate=None, minvalue=None, maxvalue=None,
                     threshold=None, limit=None, witherror=False):
        """
        Returns the records of the dataset as JSON
        """
        with db.scoped_session() as session:
            ds = session.query(db.Dataset).get(int(dataset))
            if web.user.current.level < ds.access:  # @UndefinedVariable
                raise cherrypy.HTTPError(403, 'User privileges not sufficient to access ds:' +
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
                raise cherrypy.HTTPError(500, traceback())
            return web.as_json({'error': None, 'data': records.all()})

    @expose_for(group.editor)
    def records(self, dataset, mindate, maxdate, minvalue, maxvalue, threshold=None, limit=None):
        """
        Returns a html-table of filtered records
        TODO: This method should be replaced by records_json. 
        Needs change in datasettab.html to create DOM elements using 
        jquery from the delivered JSON
        """
        session = db.scoped_session()
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
                records = records.limit(limit)
                currentcount = records.count()
        except:
            return web.Markup('<div class="error">' + traceback() + '</div>')
        res = web.render('record.html', records=records, currentcount=currentcount,
                         totalrecords=totalcount, dataset=ds, actionname="split dataset",
                         action="/dataset/setsplit",
                         action_help='/wiki/dataset/split').render('xml')
        session.close()
        return res

    @expose_for(group.editor)
    def plot_coverage(self, siteid):
        """
        Makes a bar plot (ganntt like) for the time coverage of datasets at a site
        """
        session = db.Session()
        web.setmime('image/png')
        try:
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
            st = io.BytesIO()
            fig.savefig(st, dpi=100)
        finally:
            session.close()
        return io.getvalue()

    @expose_for(group.editor)
    def create_transformation(self, sourceid):
        """
        Creates a transformed timeseries from a timeseries. 
        Redirects to the new transformed timeseries
        """
        session = db.Session()
        id = int(sourceid)
        try:
            sts = session.query(db.Timeseries).get(id)
            id = db.newid(db.Dataset, session)
            tts = db.TransformedTimeseries(id=id,
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
            session.commit()
        except Exception as e:
            return e.message
        finally:
            session.close()
        return 'goto:/dataset/%s' % id

    @expose_for(group.editor)
    def transform_removesource(self, transid, sourceid):
        """
        Remove a source from a transformed timeseries. 
        To be called from javascript. Client handles rendering
        """
        session = db.Session()
        try:
            tts = session.query(db.TransformedTimeseries).get(int(transid))
            sts = session.query(db.Timeseries).get(int(sourceid))
            tts.sources.remove(sts)
            tts.updatetime()
            session.commit()
        except Exception as e:
            return e.message
        finally:
            session.close()

    @expose_for(group.editor)
    def transform_addsource(self, transid, sourceid):
        """
        Adds a source to a transformed timeseries. 
        To be called from javascript. Client handles rendering
        """
        session = db.Session()
        try:
            tts = session.query(db.TransformedTimeseries).get(int(transid))
            sts = session.query(db.Timeseries).get(int(sourceid))
            tts.sources.append(sts)
            tts.updatetime()
            session.commit()
        except Exception as e:
            return e.message
        finally:
            session.close()


class CalibratePage(object):
    """
    Handles the calibrate tab. Loaded per ajax
    """
    exposed = True

    @expose_for(group.editor)
    def index(self, targetid, sourceid=None, limit=None, calibrate=False):
        """
        Renders the calibration options.
        """
        session = db.Session()
        error = ''
        target = session.query(db.Dataset).get(int(targetid))
        sources = session.query(db.Dataset).filter_by(site=target.site).filter(
            db.Dataset.start <= target.end, db.Dataset.end >= target.start)
        if sourceid:
            sourceid = int(sourceid)
        limit = web.conv(int, limit, 3600)
        day = timedelta(days=1)
        source = sourcerecords = None
        sourcecount = 0
        result = Calibration()
        try:
            if sourceid:
                source = CalibrationSource(
                    [sourceid], target.start - day, target.end + day)
                sourcerecords = source.records(session)
                sourcecount = sourcerecords.count()

                if calibrate and calibrate != 'false':
                    result = Calibration(target, source, limit)
                    if not result:
                        error = 'No matching records for the given time limit is found'
                source = session.query(db.Dataset).get(sourceid)
        except:
            error = traceback()
        out = web.render('calibrate.html',
                         error=error,
                         target=target,
                         sources=sources,
                         source=source,
                         limit=limit,
                         sourcecount=sourcecount,
                         result=result,
                         ).render('html')

        session.close()
        return out

    @expose_for(group.editor)
    def apply(self, targetid, sourceid, slope, offset):
        """
        Applies calibration to dataset.
        """
        session = db.Session()
        error = ''
        try:
            target = session.query(db.Dataset).get(int(targetid))
            source = session.query(db.Dataset).get(int(sourceid))
            target.calibration_slope = float(slope)
            target.calibration_offset = float(offset)
            if target.comment:
                target.comment += '\n'
            target.comment += ("Calibrated against {} at {} by {}"
                               .format(source, web.formatdate(), users.current))
            session.commit()
        except:
            error = traceback()
        finally:
            session.close()
            return error


DatasetPage.calibration = CalibratePage()
