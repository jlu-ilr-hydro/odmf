'''
Created on 18.07.2012

@author: philkraf
'''
import lib as web
import db
from traceback import format_exc as traceback
from datetime import datetime
from genshi import escape
from cStringIO import StringIO
from auth import group, expose_for, users
import codecs
from tools.calibration import Calibration, CalibrationSource


class DatasetPage:
    """
    Serves the direct dataset manipulation and querying
    """
    exposed=True
    @expose_for()
    def index(self):
        """
        Returns the query page (datasetlist.html). Site logic is handled with ajax
        """
        return web.render('datasetlist.html').render('html',doctype='html');

    @expose_for(group.guest)
    def default(self,id='new',site_id=None,vt_id=None,user=None):
        """
        Returns the dataset view and manipulation page (datasettab.html). 
        Expects an valid dataset id, 'new' or 'last'. With new, a new dataset
        is created, if 'last' the last chosen dataset is taken   
        """
        if id=='last':
            # get the last viewed dataset from web-session. If there is no 
            # last dataset, redirect to index
            id = web.cherrypy.session.get('dataset')
            if id is None:
                raise web.HTTPRedirect('/dataset/')
        session=db.Session()
        error=''
        datasets={}
        try:
            site = session.query(db.Site).get(site_id) if site_id else None
            valuetype = session.query(db.ValueType).get(vt_id) if vt_id else None
            if user is None: user = web.user()
            user = session.query(db.Person).get(user) if user else None
            if id=='new':
                active = db.Timeseries(id=db.newid(db.Dataset,session),name = 'New Dataset',
                                    site=site,valuetype=valuetype, measured_by = user)
            else: # Else load requested dataset
                active = session.query(db.Dataset).get(int(id))
                if active: # save requested dataset as 'last'
                    web.cherrypy.session['dataset']=id
            try:
                # load data for datasettab.html: 
                # similar datasets (same site and same type)
                similar_datasets = self.subset(session, valuetype=active.valuetype.id, site=active.site.id)
                # parallel dataset (same site and same time, different type)
                parallel_datasets = session.query(db.Dataset).filter_by(site=active.site).filter(db.Dataset.start<=active.end,db.Dataset.end>=active.start)
                datasets = {"same type": similar_datasets.filter(db.Dataset.id!=active.id),
                            "same time": parallel_datasets.filter(db.Dataset.id!=active.id)}
            except:
                # If loading fails, don't show similar datasets
                datasets={}
            # Render the resulting page
            result= web.render('datasettab.html',
                               # activedataset is the current dataset (id or new)
                               activedataset=active,
                               # Use session to do queries during rendering
                               session=session,
                               # Render error messages
                               error=error,
                               # similar and parallel datasets
                               datasets=datasets,
                               # the db module for queries during rendering
                               db=db,
                               # The title of the page
                               title='Schwingbach-Datensatz #' + str(id)
                              ).render('html',doctype='html')
                
        except:
            # If anything above fails, render error message
            result = web.render('datasettab.html',
                                # render traceback as error
                                error=traceback(),
                                # a title
                                title='Schwingbach-Datensatz (Fehler)',
                            # See above
                              session=session,datasets=datasets,db=db,activedataset=None).render('html',doctype='html')
        finally:
            session.close()
        return result    
    
    @expose_for(group.editor)
    def saveitem(self,**kwargs):
        """
        Saves the changes for an edited dataset
        """
        try:
            # Get current dataset
            id=web.conv(int,kwargs.get('id'),'')
        except:
            return web.render(error=traceback(),title='Dataset #%s' % kwargs.get('id')
                              ).render('html',doctype='html')
        # if save button has been pressed for submitting the dataset
        if 'save' in kwargs:
            try:
                # get database session
                session = db.Session()
                pers = db.Person.get(session,kwargs.get('measured_by'))
                vt=db.ValueType.get(session,kwargs.get('valuetype'))
                q=db.Quality.get(session,kwargs.get('quality'))
                s=db.Site.get(session,kwargs.get('site'))
                src=db.Datasource.get(session,kwargs.get('source'))

                # get the dataset        
                ds = session.query(db.Dataset).get(int(id))
                if not ds:
                    # If no ds with id exists, create a new one
                    ds=db.Timeseries(id=id)
                # Get properties from the keyword arguments kwargs
                ds.site = s
                ds.filename = kwargs.get('filename')
                ds.name=kwargs.get('name')
                ds.comment=kwargs.get('comment')
                ds.measured_by = pers
                ds.valuetype = vt
                ds.quality = q
                if src:
                    ds.source = src
                
                # Timeseries only arguments
                if ds.is_timeseries():
                    if kwargs.get('start'):
                        ds.start=datetime.strptime(kwargs['start'],'%d.%m.%Y')
                    if kwargs.get('end'):
                        ds.end=datetime.strptime(kwargs['end'],'%d.%m.%Y')
                    ds.calibration_offset = web.conv(float,kwargs.get('calibration_offset'),0.0)
                    ds.calibration_slope = web.conv(float,kwargs.get('calibration_slope'),1.0)
                # Transformation only arguments
                if ds.is_transformed():
                    ds.expression = kwargs.get('expression')
                    ds.latex = kwargs.get('latex')
                # Save changes
                session.commit()
            except:
                # On error render the error message
                return web.render('empty.html',error=traceback(),title='Dataset #%s' % id
                                  ).render('html',doctype='html')
            finally:
                session.close()
        elif 'new' in kwargs:
            id='new'
        # reload page
        raise web.HTTPRedirect('./%s' % id)
    
    @expose_for()
    def statistics(self,id):
        """
        Returns a json file holding the statistics for the dataset (is loaded by page using ajax)
        """
        web.setmime(web.mime.json)
        session=db.Session()
        ds = db.Dataset.get(session,int(id));
        if ds:
            # Get statistics
            mean,std,n = ds.statistics()
            # Convert to json
            res=web.as_json(dict(mean=mean,std=std,n=n))
        else:
            # Return empty dataset statistics
            res=web.as_json(dict(mean=0,std=0,n=0))
        return res
    
    @expose_for(group.admin)
    def remove(self,dsid):
        """
        Removes a dataset. Called by javascript, page reload handled by client
        """
        try:
            db.removedataset(dsid)
            return None
        except Exception as e:
            return str(e)
    
    def subset(self,session,valuetype=None,user=None,site=None,date=None,instrument=None,type=None):
        """
        A not exposed helper function to get a subset of available datasets using filter
        """
        datasets=session.query(db.Dataset)
        if user:
            user=session.query(db.Person).get(user)
            datasets=datasets.filter_by(measured_by=user)
        if site:
            site=session.query(db.Site).get(int(site))
            datasets=datasets.filter_by(site=site)
        if date:
            date=web.parsedate(date)
            datasets=datasets.filter(db.Dataset.start<=date,db.Dataset.end>=date)
        if valuetype:
            vt=session.query(db.ValueType).get(int(valuetype))
            datasets=datasets.filter_by(valuetype=vt)
        if instrument:
            if instrument=='null':
                source = None
            else:
                source = session.query(db.Datasource).get(int(instrument))
            datasets=datasets.filter_by(source=source)
        if type:
            datasets=datasets.filter_by(type=type)
            
        return datasets.join(db.ValueType).order_by(db.ValueType.name,db.sql.desc(db.Dataset.end))
    
    @expose_for()
    def attrjson(self,attribute,valuetype=None,user=None,site=None,date=None,instrument=None,type=None):
        """
        Gets the attributes for a dataset filter. Returns json. Used for many filters using ajax.
        e.g: Map filter, datasetlist, import etc.
        
        TODO: This function is not very well scalable. If the number of datasets grows,
        please use distinct to get the distinct sites / valuetypes etc.
        """
        web.setmime('application/json')        
        if not hasattr(db.Dataset,attribute):
            raise AttributeError("Dataset has no attribute '%s'" % attribute)
        session=db.Session()
        res=''
        try:
            # Get dataset for filter
            datasets = self.subset(session,valuetype,user,site,date,instrument,type)
            # Make a set of the attribute items 
            items = set(getattr(ds, attribute) for ds in datasets)
            # Convert object set to json
            res = web.as_json(sorted(items))
            session.close()
        finally:
            session.close()
        return res
        
        
    @expose_for()
    def json(self,valuetype=None,user=None,site=None,date=None,instrument=None,type=None):
        """
        Gets a json file of available datasets with filter
        """
        web.setmime('application/json')        
        session=db.Session()
        try:
            dump = web.as_json(self.subset(session, valuetype, user, site, date,instrument,type).all())
        finally:
            session.close()
        return dump
    
    @expose_for(group.editor)
    def updaterecorderror(self,dataset,records):
        """
        Mark record id (records) as is_error for dataset. Called by javascript
        """
        try:
            recids = set(int(r) for r in records.split())
            session=db.Session()
            ds = db.Dataset.get(session,int(dataset))
            q=ds.records.filter(db.Record.id.in_(recids))
            for r in q:
                r.is_error = True
            session.commit()
            session.close()
        except:
            return traceback()

    @expose_for(group.editor)
    def findsplitpoints(self,datasetid,threshold):
        """
        finds jumps between records in dataset.
        r_{i+1}-r_{i}>threshold
        """
        session=db.Session()
        output=''
        try:
            ds = db.Dataset.get(session,int(datasetid))
            jumps=ds.findjumps(float(threshold))
            output = web.render('record.html',dataset=ds,records=jumps,actionname="split dataset",action="/dataset/setsplit").render('xml')
        except:
            output=traceback()          
        finally:
            session.close()
        return output


    @expose_for(group.editor)
    def setsplit(self,datasetid,recordid):
        """
        Splits the datset at record id
        """
        try:
            session=db.Session()
            ds = db.Dataset.get(session,int(datasetid))
            rec = ds.records.filter_by(id=int(recordid)).first()
            ds,dsnew = ds.split(rec.time)
            if ds.comment: ds.comment+='\n'
            ds.comment+='splitted by ' + web.user() + ' at ' + web.formatdate() + '. New dataset is ' + str(dsnew)
            if dsnew.comment: dsnew.comment+='\n'
            ds.comment+='This dataset is created by a split done by ' + web.user() + ' at ' + web.formatdate() + '. Orignal dataset is ' + str(ds) 
            res = "New dataset: %s" % dsnew
        except:
            res=traceback()
        finally:
            session.close()
        return res
         
    
    @expose_for(group.logger)
    def records_csv(self,dataset,raw=False):
        """
        Exports the records of the timeseries as csv
        """
        web.setmime('text/csv')
        session = db.Session()
        ds = session.query(db.Dataset).get(dataset)
        st = StringIO()
        st.write(codecs.BOM_UTF8)
        st.write((u'"Dataset","ID","time","%s","site","comment"\n' % (ds.valuetype)).encode('utf-8'))
        for r in ds.iterrecords(raw):
            d=dict(c=unicode(r.comment).replace('\r','').replace('\n',' / '),
                 v=r.calibrated if raw else r.value,
                 time = web.formatdate(r.time)+' '+web.formattime(r.time),
                 id=r.id,
                 ds=ds.id,
                 s=ds.site.id)

            st.write((u'%(ds)i,%(id)i,%(time)s,%(v)s,%(s)i,"%(c)s"\n' % d).encode('utf-8'))
        session.close()
        return st.getvalue()
        
    @expose_for(group.logger)
    def plot(self,id,start=None,end=None,marker='',line='-',color='k'):
        """
        Plots the dataset. Might be deleted in future. Rather use PlotPage
        """
        web.setmime('image/png')
        session=db.Session()
        try:
            import matplotlib
            matplotlib.use('Agg',warn=False)
            import pylab as plt
            import numpy as np  
            ds = session.query(db.Dataset).get(int(id))
            if start:
                start=web.parsedate(start)
            else:
                start=ds.start
            if end:
                end=web.parsedate(end)
            else:
                end=ds.end
            t,v = ds.asarray(start,end)
            fig=plt.figure()
            ax=fig.gca()
            ax.plot_date(t,v,color+marker+line)
            loc=ax.xaxis.get_major_locator()
            io = StringIO()
            ax.grid()
            plt.xticks(rotation=15)
            plt.ylabel('%s [%s]' % (ds.valuetype.name,ds.valuetype.unit))
            plt.title(ds.site)
            fig.savefig(io,dpi=100)
        finally:
            session.close()
        return io.getvalue()
        
    @expose_for(group.editor)
    def addrecord(self,datasetid,time,value,comment=None):
        """
        Adds a record to the dataset. Purge?
        """
        error=''
        session=db.Session()
        try:
            error="Dataset %s not found" % datasetid 
            ds = db.Dataset.get(int(datasetid))
            error="'%s' is not a number. Use . as decimal sign." % value
            value = float(value)
            error = "'%s' is not a valid date." % time 
            time = web.parsedate(time)
            error = "Could not create record for %s" % ds
            ds.addrecord(value=value,time=time,comment=comment)
        except Exception as e:
            return error + '\n' + e.message
        finally:
            session.close()
        return ''
    
    @expose_for(group.editor)
    def records(self,dataset,mindate,maxdate,minvalue,maxvalue):
        """
        Returns a html-table of filtered records
        """
        session=db.Session()
        ds = db.Dataset.get(session,int(dataset))
        records = ds.records.order_by(db.Record.time).filter(~db.Record.is_error)
        try:
            if mindate.strip(): records=records.filter(db.Record.time>web.parsedate(mindate.strip()))
            if maxdate.strip(): records=records.filter(db.Record.time<web.parsedate(maxdate.strip()))
            if minvalue: records=records.filter(db.Record.value>float(minvalue))
            if maxvalue: records=records.filter(db.Record.value<float(maxvalue))
        except:
            return web.Markup('<div class="error">'+traceback()+'</div>')
        res = web.render('record.html',records=records,dataset=ds,actionname='',action='').render('xml')
        session.close()
        return res
            
    @expose_for(group.editor)
    def plot_coverage(self,siteid):
        """
        Makes a bar plot (ganntt like) for the time coverage of datasets at a site
        """
        session = db.Session()
        web.setmime('image/png')
        try:
            import matplotlib
            matplotlib.use('Agg',warn=False)
            import pylab as plt
            import numpy as np
            ds = session.query(db.Dataset).filter_by(_site=int(siteid)).order_by(db.Dataset._source,db.Dataset._valuetype,db.Dataset.start).all()
            left = plt.date2num([d.start for d in ds])
            right = plt.date2num([d.end for d in ds])
            btm = np.arange(-.5,-len(ds),-1)
            #return 'left=' + str(left) + ' right=' + str(right) + ' btm=' + str(btm)
            fig = plt.figure()
            ax = fig.gca()
            ax.barh(left=left,width=right-left,bottom=btm,height=0.9,fc='0.75',ec='0.5')
            for l,b,d in zip(left,btm,ds):
                ax.text(l,b+.5,'#%i' % d.id, color='k',va='center')
            ax.xaxis_date()
            ax.set_yticks(btm+.5)
            ax.set_yticklabels([d.source.name + '/' + d.valuetype.name for d in ds])
            ax.set_position([0.3,0.05,0.7,0.9])
            ax.set_title('Site #' + siteid)
            ax.set_ylim(-len(ds)-.5,.5)
            ax.grid()
            io = StringIO()
            fig.savefig(io,dpi=100)
        finally:
            session.close()  
        return io.getvalue()
    
    @expose_for(group.editor)
    def create_transformation(self,sourceid):
        """
        Creates a transformed timeseries from a timeseries. Redirects to the new transformed timeseries
        """
        session = db.Session()
        id=int(sourceid)
        try:
            sts = session.query(db.Timeseries).get(id)
            id = db.newid(db.Dataset,session)
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
    def transform_removesource(self,transid,sourceid):
        """
        Remove a source from a transformed timeseries. To be called from javascript. Client handles rendering
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
    def transform_addsource(self,transid,sourceid):
        """
        Adds a source to a transformed timeseries. To be called from javascript. Client handles rendering
        """
        session=db.Session()
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
    exposed=True
            
    @expose_for(group.editor)
    def index(self,targetid,sourceid=None,limit=None,calibrate=False):
        """
        Renders the calibration options.
        """
        session = db.Session()
        error=''
        target = db.Dataset.get(session,int(targetid))
        sources = session.query(db.Dataset).filter_by(site=target.site).filter(db.Dataset.start<=target.end,db.Dataset.end>=target.start)
        if sourceid:
            sourceid = int(sourceid)
        limit=web.conv(int,limit,3600)
        source=sourcerecords=None
        sourcecount=0
        result = Calibration()
        try:   
            if sourceid:
                source = CalibrationSource([sourceid], target.start, target.end)
                sourcerecords = source.records(session)
                sourcecount=sourcerecords.count()
                
                if calibrate and calibrate!='false':
                    result=Calibration(target,source,limit)
                    if not result:
                        error='No matching records for the given time limit is found'
                source = db.Dataset.get(session,sourceid)
        except:
            error = traceback()    
        out = web.render('calibrate.html',
                          error=error,
                          target=target,
                          sources=sources,
                          source=source,
                          limit=limit,
                          sourcecount = sourcecount,
                          result=result,
                          ).render('html') 

        session.close()
        return out 
    @expose_for(group.editor)
    def apply(self,targetid,sourceid,slope,offset):
        """
        Applies calibration to dataset.
        """
        session=db.Session()
        error=''
        try:
            target = db.Dataset.get(session,int(targetid))
            source = db.Dataset.get(session,int(sourceid))
            target.calibration_slope = float(slope)
            target.calibration_offset = float(offset)
            if target.comment:
                target.comment += '\n'
            target.comment += "Calibrated against %s at %s by %s" % (source,web.formatdate(),users.current)
            session.commit()
        except:
            error=traceback()
        finally:
            session.close()
            return error
        
DatasetPage.calibration=CalibratePage()
               
            
        
        
        
        
        
