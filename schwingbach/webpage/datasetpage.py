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
    exposed=True
    @expose_for()
    def index(self):
        return web.render('datasetlist.html').render('html',doctype='html');
        #text = file(web.abspath('templates/datasetlist.html')).read()
        #return text.replace('${navigation()}',web.navigation())

    @expose_for(group.guest)
    def default(self,id='new',site_id=None,vt_id=None,user=None):
        if id=='last':
            id = web.cherrypy.session.get('dataset')
            if id is None:
                raise web.HTTPRedirect('/dataset/')
        session=db.Session()
        error=''
        datasets={}
        try:
            site = session.query(db.Site).get(site_id) if site_id else None
            valuetype = session.query(db.ValueType).get(vt_id) if vt_id else None
            user = session.query(db.Person).get(user) if user else None
            if id=='new':
                active = db.Dataset(id=db.newid(db.Dataset,session),
                                    site=site,valuetype=valuetype, measured_by = user)
            else:
                active = session.query(db.Dataset).get(id)
                if active:
                    web.cherrypy.session['dataset']=id
            try:
                similar_datasets = self.subset(session, valuetype=active.valuetype.id, site=active.site.id)
                parallel_datasets = session.query(db.Dataset).filter_by(site=active.site).filter(db.Dataset.start<=active.end,db.Dataset.end>=active.start)
                datasets = {"same type": similar_datasets.filter(db.Dataset.id!=active.id),
                            "same time": parallel_datasets.filter(db.Dataset.id!=active.id)}
            except:
                datasets={}
            result= web.render('datasettab.html',activedataset=active,session=session,
                              error=error,datasets=datasets,db=db,title='Schwingbach-Datensatz #' + str(id)
                              ).render('html',doctype='html')
                
        except:
            result = web.render('datasettab.html',error=traceback(),title='Schwingbach-Datensatz (Fehler)',
                              session=session,datasets=datasets,db=db,activedataset=None).render('html',doctype='html')
        finally:
            session.close()
        return result    
    
    @expose_for(group.editor)
    def saveitem(self,**kwargs):

        try:
            id=web.conv(int,kwargs.get('id'),'')
        except:
            return web.render(error=traceback(),title='Dataset #%s' % kwargs.get('id')
                              ).render('html',doctype='html')
        if 'save' in kwargs:
            try:
                session = db.Session()        
                ds = session.query(db.Dataset).get(int(id))
                if not ds:
                    ds=db.Dataset(id=id)
                if kwargs.get('start'):
                    ds.start=datetime.strptime(kwargs['start'],'%d.%m.%Y')
                if kwargs.get('end'):
                    ds.end=datetime.strptime(kwargs['end'],'%d.%m.%Y')
                ds.filename = kwargs.get('filename')
                ds.name=kwargs.get('name')
                ds.comment=kwargs.get('comment')
                ds.measured_by = session.query(db.Person).get(kwargs.get('measured_by'))
                ds.valuetype = session.query(db.ValueType).get(kwargs.get('valuetype'))
                ds.quality = session.query(db.Quality).get(kwargs.get('quality'))
                ds.site = session.query(db.Site).get(kwargs.get('site'))
                ds.calibration_offset = web.conv(float,kwargs.get('calibration_offset'),0.0)
                ds.calibration_slope = web.conv(float,kwargs.get('calibration_slope'),1.0)
                if kwargs.get('source'):
                    ds.source = session.query(db.Datasource).get(int(kwargs.get('source')))
                session.commit()
            except:
                return web.render('empty.html',error=traceback(),title='Dataset #%s' % id
                                  ).render('html',doctype='html')
            finally:
                session.close()
        elif 'new' in kwargs:
            id='new'
        raise web.HTTPRedirect('./%s' % id)
    
    @expose_for(group.admin)
    def remove(self,dsid):
        try:
            db.removedataset(dsid)
            return None
        except Exception as e:
            return str(e)
    
    def subset(self,session,valuetype=None,user=None,site=None,date=None,instrument=None):
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
            source = session.query(db.Datasource).get(int(instrument))
            datasets=datasets.filter_by(source=source)
            
        return datasets.join(db.ValueType).order_by(db.ValueType.name,db.sql.desc(db.Dataset.end))
    
    @expose_for()
    def attrjson(self,attribute,valuetype=None,user=None,site=None,date=None,instrument=None):
        """TODO: This function is not very well scalable. If the number of datasets grows,
        please use distinct to get the distinct sites / valuetypes etc.
        """
        web.setmime('application/json')        
        if not hasattr(db.Dataset,attribute):
            raise AttributeError("Dataset has no attribute '%s'" % attribute)
        session=db.Session()
        res=''
        try:
            datasets = self.subset(session,valuetype,user,site,date,instrument)
            items = set(getattr(ds, attribute) for ds in datasets)
            res = web.as_json(sorted(items))
            session.close()
        finally:
            session.close()
        return res
        
        
    @expose_for()
    def json(self,valuetype=None,user=None,site=None,date=None,instrument=None):
        web.setmime('application/json')        
        session=db.Session()
        try:
            dump = web.as_json(self.subset(session, valuetype, user, site, date,instrument).all())
        finally:
            session.close()
        return dump
    
    @expose_for(group.editor)
    def updaterecorderror(self,dataset,records):
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
        web.setmime('text/csv')
        session = db.Session()
        ds = session.query(db.Dataset).get(dataset)
        st = StringIO()
        st.write(codecs.BOM_UTF8)
        st.write((u'"Dataset","ID","time","%s","site","comment"\n' % (ds.valuetype)).encode('utf-8'))
        query = session.query(db.Record).filter_by(dataset=ds).order_by(db.Record.time)
        if not raw:
            query = query.filter(~db.Record.is_error)
        for r in query:
            d=dict(c=unicode(r.comment).replace('\r','').replace('\n',' / '),
                 v=r.calibrated if raw else r.value,
                 time = web.formatdate(r.time)+' '+web.formattime(r.time),
                 id=r.id,
                 ds=ds.id,
                 s=ds.site.id)

            st.write((u'%(ds)i,%(id)i,%(time)s,%(v)s,%(s)i,"%(c)s"\n' % d).encode('utf-8'))
        session.close()
        return st.getvalue()
        
    @expose_for(group.guest)
    def edit(self,id):
        session=db.Session()
        try:
            if id=='new':
                active = db.Dataset(id=db.newid(db.Dataset,session))
            else:
                active = session.query(db.Dataset).get(id)
            result= web.render('datasetedit.xml',activedataset=active,session=session,db=db).render('html')
        finally:
            session.close()
        return result
    
    @expose_for(group.logger)
    def plot(self,id,start=None,end=None,marker='',line='-',color='k'):
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
            records = session.query(db.Record).filter(db.Record.time>=start, db.Record.time<=end,db.Record._dataset==ds.id)
            records=records.order_by(db.Record.time).filter(~db.Record.is_error)
            t0 = datetime(1,1,1)
            date2num = lambda t: (t-t0).total_seconds()/86400 + 1.0
            def r2c(records):
                for r in records:
                    if r[0] is None:
                        yield np.log(-1),date2num(r[1])
                    else:
                        yield r[0],date2num(r[1])
            ts = np.zeros(shape=(records.count(),2),dtype=float)
            for i,r in enumerate(r2c(records.values('value','time'))):
                ts[i] = r
            ts[:,0]*=ds.calibration_slope 
            ts[:,0]+=ds.calibration_offset  
            fig=plt.figure()
            ax=fig.gca()
            ax.plot_date(ts[:,1],ts[:,0],color+marker+line)
            loc=ax.xaxis.get_major_locator()
            #loc.maxticks.update({0:5,1:6,2:10,3:7,4:9,5:9,6:9})
            #loc.interval_multiples=True
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
            
    @expose_for(group.supervisor)
    def plot_coverage(self,siteid):
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

                    

class CalibratePage(object):
    exposed=True
            
    @expose_for(group.editor)
    def index(self,targetid,sourceid=None,limit=None,calibrate=False):
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

        if sourceid:
            source = CalibrationSource([sourceid], target.start, target.end)
            sourcerecords = source.records(session)
            sourcecount=sourcerecords.count()
            
            if calibrate and calibrate!='false':
                result=Calibration(target,source,limit)
            source = db.Dataset.get(session,sourceid)    
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
               
            
        
        
        
        
        
