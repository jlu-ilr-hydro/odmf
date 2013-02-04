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
from auth import users, require, member_of, group, expose_for
import codecs
from math import sqrt


class DatasetPage:
    exposed=True
    @expose_for()
    def index(self):
        text = file(web.abspath('templates/datasetlist.html')).read()
        return text.replace('${navigation()}',web.navigation())

    @expose_for(group.guest)
    def default(self,id='new',site_id=None,vt_id=None,user=None):
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
            try:
                similar_datasets = self.subset(session, valuetype=active.valuetype.id, site=active.site.id)
                parallel_datasets = session.query(db.Dataset).filter_by(site=active.site).filter(db.Dataset.start<=active.end,db.Dataset.end>=active.start)
                datasets = {"same type": similar_datasets.filter(db.Dataset.id!=active.id),
                            "same time": parallel_datasets.filter(db.Dataset.id!=active.id)}
            except:
                datasets={}
            result= web.render('dataset.html',activedataset=active,session=session,
                              error=error,datasets=datasets,db=db,title='Schwingbach-Datensatz #' + str(id)
                              ).render('html',doctype='html')
                
        except:
            result = web.render('dataset.html',error=traceback(),title='Schwingbach-Datensatz (Fehler)',
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
    
    def subset(self,session,valuetype=None,user=None,site=None,date=None):
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
            
        return datasets.join(db.ValueType).order_by(db.ValueType.name,db.sql.desc(db.Dataset.end))
    
    @expose_for()
    def attrjson(self,attribute,valuetype=None,user=None,site=None,date=None):
        """TODO: This function is not very well scalable. If the number of datasets grows,
        please use distinct to get the distinct sites / valuetypes etc.
        """
        web.setmime('application/json')        
        if not hasattr(db.Dataset,attribute):
            raise AttributeError("Dataset has no attribute '%s'" % attribute)
        session=db.Session()
        res=''
        try:
            datasets = self.subset(session,valuetype,user,site,date)
            items = set(getattr(ds, attribute) for ds in datasets)
            res = web.as_json(sorted(items))
            session.close()
        finally:
            session.close()
        return res
        
        
    @expose_for()
    def json(self,valuetype=None,user=None,site=None,date=None):
        web.setmime('application/json')        
        session=db.Session()
        try:
            dump = web.as_json(self.subset(session, valuetype, user, site, date))
        finally:
            session.close()
        return dump
    

    @expose_for(group.editor)
    def findsplitpoints(self,datasetid,threshold):
        session=db.Session()
        output=''
        try:
            ds = db.Dataset.get(session,int(datasetid))
            jumps=ds.findjumps(float(threshold))
            output = web.render('record.html',records=jumps,actionname="split dataset",action="/dataset/setsplit").render('xml')
        except:
            output=traceback()          
        finally:
            session.close()
        return output


    @expose_for(group.admin)
    def setsplit(self,datasetid,recordid):
        print "Split at ds[%s].rec[%s]" % (datasetid,recordid)  
    
    @expose_for(group.logger)
    def records_csv(self,dataset):
        web.setmime('text/csv')
        session = db.Session()
        ds = session.query(db.Dataset).get(dataset)
        st = StringIO()
        st.write(codecs.BOM_UTF8)
        st.write((u'"Dataset","ID","time","%s","site","comment"\n' % (ds.valuetype)).encode('utf-8'))
        query = session.query(db.Record).filter_by(dataset=ds).order_by(db.Record.time)
        for r in query:
            d=dict(c=str(r.comment).replace('\r','').replace('\n',' / '),
                 v=r.calibrated,
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
            records = ds.records.filter(db.Record.time>=start, db.Record.time<=end)
            records=records.order_by(db.Record.time)
            t0 = datetime(1,1,1)
            date2num = lambda t: (t-t0).total_seconds()/86400 + 1.0
            def r2c(records):
                for r in records:
                    if r.value is None:
                        yield np.log(-1),date2num(r.time)
                    else:
                        yield r.calibrated,date2num(r.time)
                    
            ts = np.zeros(shape=(records.count(),2),dtype=float)
            for i,r in enumerate(r2c(records)):
                ts[i] = r  
            fig=plt.figure()
            ax=fig.gca()
            ax.plot_date(ts[:,1],ts[:,0],color+marker+line)
            loc=ax.xaxis.get_major_locator()
            #loc.maxticks.update({0:5,1:6,2:10,3:7,4:9,5:9,6:9})
            #loc.interval_multiples=True
            io = StringIO()
            ax.grid()
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

class Match:
    def __init__(self,time,target,source,dt):
        self.target=target
        self.time=time
        self.source=source
        self.dt=dt
    def delta(self):
        return self.source-self.target
        
class Calibration:
    def __len__(self):
        return len(self.matches)
    def __init__(self,matches=[]):
        self.matches=list(matches)
        self.slope=1.0
        self.offset=0.0
        self.meanoffset=0.0
        self.r2 = 0.0
        self.target_mean=0.0
        self.source_mean=0.0
        self.source_std = 0.0
        self.target_std = 0.0
        self.refresh()
    def __iter__(self):
        for m in self.matches:
            yield dict(t=m.time, source=m.source, target=m.target, 
                       lr=m.target*self.slope + self.offset, 
                       off=m.target + self.meanoffset,
                       dt=m.dt,
                       ) 
    def refresh(self):
        if len(self.matches) > 1:
            self.target_mean = self.source_mean = 0.0
            n = float(len(self))
            for m in self.matches:
                self.target_mean+=m.target/n
                self.source_mean+=m.source/n
            cov = var_s = var_t = 0.0
            for m in self.matches:
                cov +=  (m.target - self.target_mean) * (m.source - self.source_mean)
                var_s += (m.source - self.source_mean)**2
                var_t += (m.target - self.target_mean)**2
            self.meanoffset = self.source_mean - self.target_mean
            self.slope = cov/var_t
            self.offset = self.source_mean - self.slope * self.target_mean
            self.target_std = sqrt(var_t)
            self.source_std = sqrt(var_s)
            # Variant:
            # self.slope = cov/var_s
            # self.offset = self.target_mean - self.slope * self.source_mean
            self.r2 = cov**2/(var_s*var_t) 
                
        elif len(self.matches) == 1:
            self.meanoffset = self.offset = self.matches[0].delta()
            self.slope=1.0
            self.r2 = 0.0
        else:
            self.slope=1.0
            self.offset=0.0
            self.meanoffset=0.0
            self.r2 = 0.0

            

class CalibratePage(object):
    exposed=True
    def getsourcerecords(self,source,target):
        return source.records.filter(db.Record.time>=target.start,db.Record.time<=target.end)
        
    def getmatches(self,target,source,limit=10):
        sourcerecords = self.getsourcerecords(source,target)
        for i,sr in enumerate(sourcerecords):
            tv,dt = target.findvalue(sr.time) 
            yield Match(sr.time,tv,sr.value,dt)
            if i>=limit-1:
                break
            
    @expose_for(group.editor)
    def index(self,targetid,sourceid=None,limit=None,calibrate=False):
        session = db.Session()
        error=''
        target = db.Dataset.get(session,int(targetid))
        sources = session.query(db.Dataset).filter_by(site=target.site).filter(db.Dataset.start<=target.end,db.Dataset.end>=target.start)

        sourceid = web.conv(int,sourceid)
        limit=web.conv(int,limit,10)
        source=sourcerecords=None
        sourcecount=0
        result = Calibration()

        if sourceid:
            source = db.Dataset.get(session,sourceid)
            sourcerecords = self.getsourcerecords(source, target)
            sourcecount=sourcerecords.count()
            
            if calibrate:
                result=Calibration(self.getmatches(target,source,limit))
                
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
        
DatasetPage.calibration=CalibratePage()
               
            
        
        
        
        
        
