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
from auth import users, require, member_of, has_level, group
import codecs
class DatasetPage:
    exposed=True
    @web.expose
    def index(self):
        text = file(web.abspath('templates/datasetlist.html')).read()
        return text.replace('${navigation()}',web.navigation())

    @require(member_of(group.guest))
    @web.expose
    def default(self,id='new',site_id=None,vt_id=None,user=None):
        session=db.Session()
        datasets = session.query(db.Dataset)
        error=''
        try:
            site = session.query(db.Site).get(site_id) if site_id else None
            valuetype = session.query(db.ValueType).get(vt_id) if vt_id else None
            user = session.query(db.Person).get(user) if user else None
            if id=='new':
                active = db.Dataset(id=db.newid(db.Dataset,session),
                                    site=site,valuetype=valuetype, measured_by = user)
            else:
                active = session.query(db.Dataset).get(id)
            if site:
                datasets=datasets.filter_by(site=site)
            if valuetype:
                datasets=datasets.filter_by(valuetype=valuetype)
            if user:
                datasets=datasets.filter_by(measured_by=user)
        
            result= web.render('dataset.html',activedataset=active,session=session,
                              error=error,datasets=datasets,db=db,title='Schwingbach-Datensatz #' + str(id)
                              ).render('html',doctype='html')
                
        except:
            result = web.render('dataset.html',error=traceback(),title='Schwingbach-Datensatz (Fehler)',
                              session=session,datasets=datasets,db=db,activedataset=None).render('html',doctype='html')
        finally:
            session.close()
        return result    
    
    @require(member_of(group.editor))
    @web.expose
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
                ds.calibration_offset = float(kwargs.get('calibration_offset'))
                ds.calibration_slope = float(kwargs.get('calibration_slope'))
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
        return datasets
    
    
    @web.expose
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
        
        
    @web.expose
    def json(self,valuetype=None,user=None,site=None,date=None):
        session=db.Session()
        try:
            dump = web.as_json(self.subset(session, valuetype, user, site, date))
        finally:
            session.close()
        return dump
    
    @require(member_of(group.logger))
    @web.expose
    def records_csv(self,dataset):
        web.setmime('text/csv')
        session = db.Session()
        ds = session.query(db.Dataset).get(dataset)
        st = StringIO()
        st.write(codecs.BOM_UTF8)
        st.write((u'"Dataset","ID","time","%s","site","comment"\n' % (ds.valuetype)).encode('utf-8'))
        query = session.query(db.Record).filter_by(dataset=ds)                 
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
        
    
    @require(member_of(group.guest))
    @web.expose
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
    
    @require(member_of(group.guest))
    @web.expose
    def plot(self,id,start=None,end=None,marker='',line='-',color='k'):
        web.setmime('image/png')
        session=db.Session()
        try:
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
            records=records.filter(db.Record.value!=None)
            reccount = records.count()
            print reccount,"Records"
            t0 = datetime(1,1,1)
            date2num = lambda t: (t-t0).total_seconds()/86400 + 1.0
            def r2c(records):
                for r in records:
                    yield complex(r.calibrated,date2num(r.time))
                    
            import numpy as np       
            ts = np.fromiter(r2c(records),dtype=complex,count=records.count())
            import matplotlib
            matplotlib.use('Agg',warn=False)
            import pylab as plt
            
            fig=plt.figure()
            ax=fig.gca()
            ax.plot_date(ts.imag,ts.real,color+marker+line)
            loc=ax.xaxis.get_major_locator()
            loc.maxticks.update({0:5,1:6,3:7,4:9,5:9,6:9})
            #loc.interval_multiples=True
            io = StringIO()
            ax.grid()
            plt.ylabel('%s [%s]' % (ds.valuetype.name,ds.valuetype.unit))
            plt.title(ds.site)
            fig.savefig(io,dpi=100)
        finally:
            session.close()
        return io.getvalue()
        
        
        

