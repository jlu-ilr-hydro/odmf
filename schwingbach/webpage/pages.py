# -*- coding: utf-8 -*-

import lib as web
import db
from traceback import format_exc as traceback
from base64 import b64encode
from webpage.upload import DownloadPage
from datetime import datetime
import json
from cStringIO import StringIO
class PersonPage:
    exposed=True  
    @web.expose
    @web.output('person.html')    
    def default(self,act_user='new'):
        session = db.Session()
        persons = session.query(db.Person).order_by(db.sql.desc(db.Person.can_supervise),db.Person.surname)
        supervisors = persons.filter(db.Person.can_supervise==True)
        error=''
        jobs=[]
        if act_user == 'new':
            p_act = db.Person()
        else:
            try:
                p_act = session.query(db.Person).get(act_user)
                jobs=p_act.jobs.order_by(db.sql.asc(db.Job.done),db.sql.asc(db.Job.due))
            except:
                p_act=None
                error=traceback()   
        result = web.render('person.html',persons=persons,active_person=p_act,
                          supervisors=supervisors,error=error,jobs=jobs).render('html',doctype='html')
        session.close()
        return result

    @web.expose
    def saveitem(self,**kwargs):
        username=kwargs.get('username')
        if 'save' in kwargs and username:
            session = db.Session()        
            p_act = session.query(db.Person).filter_by(username=username).first()
            if not p_act:
                p_act=db.Person(username=username)
                session.add(p_act)
            p_act.email=kwargs.get('email')
            p_act.firstname=kwargs.get('firstname')
            p_act.surname=kwargs.get('surname')
            p_act.supervisor=session.query(db.Person).get(kwargs.get('supervisor'))
            #p_act.can_supervise=kwargs.get('can_supervise')
            p_act.car_available=kwargs.get('car_available')
            p_act.telephone=kwargs.get('telephone')
            p_act.mobile=kwargs.get('mobile')
            p_act.comment=kwargs.get('comment')
            session.commit()
            session.close()
        raise web.HTTPRedirect('./' + username)
    @web.expose
    def json(self,supervisors=False):
        web.setmime('application/json')
        session = db.Session()
        persons = session.query(db.Person).order_by(db.sql.desc(db.Person.can_supervise),db.Person.surname)
        if supervisors:
            persons = persons.filter(db.Person.can_supervise==True)
        io= StringIO()
        io.write('[\n')
        for p in persons:
            io.write('{"username":%s, "text":%s}\n' % (p.username,p))
        io.write(']\n')
        return io.getvalue()

        
class SitePage:
    exposed=True  
    @web.expose
    def default(self,actualsite_id='1',error=''):
        session=db.Session()
        if actualsite_id=='new':
            actualsite=db.Site(id=db.newid(db.Site,session),
                               lon=8.55,lat=50.5,
                               name='<enter site name>')
        else:
            try:
                actualsite=session.query(db.Site).get(int(actualsite_id))
            except:
                error=traceback()
                actualsite=None
        
        result = web.render('site.html',actualsite=actualsite,error=error,image=''
                            ).render('html',doctype='html')
        session.close()
        return result    
    @web.expose
    def saveitem(self,**kwargs):
        try:
            siteid=web.conv(int,kwargs.get('id'),'')
        except:
            return web.render(error=traceback(),title='site #%s' % kwargs.get('id'))
        if 'save' in kwargs:
            try:
                session = db.Session()        
                site = session.query(db.Site).get(int(siteid))
                if not site:
                    site=db.Site(id=int(siteid))
                    session.add(site)
                site.lon=web.conv(float,kwargs.get('lon'))
                site.lat=web.conv(float,kwargs.get('lat'))
                site.name=kwargs.get('name')
                site.height=web.conv(float,kwargs.get('height'))
                site.comment=kwargs.get('comment')
                session.commit()
                session.close()

            except:
                return web.render('empty.html',error=traceback(),title='site #%s' % siteid
                                  ).render('html',doctype='html')
        raise web.HTTPRedirect('./%s' % siteid)
    @web.expose
    def edit(self,siteid='new'):
        session=db.Session()
        if siteid=='new':        
            actualsite=db.Site(id=db.newid(db.Site,session),
                               lon=8.55,lat=50.5,
                               name='<enter site name>')
        else:
            try:
                actualsite=session.query(db.Site).get(int(siteid))
                
            except:
                error=traceback()
                actualsite=None
        if actualsite:
            result=web.render('newsite.html',actualsite=actualsite).render('xml')
        else:        
            result= web.Markup('<div class="error">%s</div>' % error)
        session.close()
        return result
    @web.expose
    def instrument(self,installationid=None,siteid=None,action='add',date=None,instrumentid=None):
        session=db.Session()
        error=''
        try:
            date=web.parsedate(date)
            site = session.query(db.Site).get(int(siteid))
            instrument = session.query(db.Instrument).get(int(instrumentid))
            if installationid:
                inst = session.query(db.Installation).get(int(installationid))
            else:
                instid = session.query(db.Installation)\
                        .filter(db.Installation.instrument==instrument,db.Installation.site==site)\
                        .order_by(db.sql.desc(db.Installation.id)).first().id
                inst = db.Installation(site, instrument, instid+1, date)
                session.add(inst)
            if action!='add' and inst:
                inst.removedate = date
        except:
            error=traceback()
        raise web.HTTPRedirect('/site/%s?error=%s' % (siteid,error))
        
        

                  
    @web.expose
    def json(self):
        session=db.Session()
        web.setmime('application/json')
        sites=[{'id':s.id,'text':str(s)} for s in session.query(db.Site).order_by(db.Site.id)]
        res = json.dumps(sites,indent=4)
        return res
        
    @web.expose
    def kml(self,sitefilter=None):
        session = db.Session()
        web.setmime('application/vnd.google-earth.kml+xml')
        
        query = session.query(db.Site)
        if filter:
            query = query.filter(sitefilter)
        stream = web.render('sites.xml',sites=query,actid=0,descriptor=SitePage.kml_description)
        result = stream.render('xml')
        session.close()
        return result    
    @classmethod
    def kml_description(cls,site):
        host = "http://fb09-pasig.umwelt.uni-giessen.de:8081"
        text=[ site.comment,
               u'<a href="%s/site/%s">edit...</a>' % (host,site.id)]
        if site.height:
            text.insert(0,'%0.1f m NN' % site.height)
        text.append(u'<h3>Logbuch:</h3>')
        for log in site.logs:
            content=dict(date=web.formatdate(log.time),user=log.user,msg=log.message,host=host,id=log.id)
            text.append(u'<li><a href="%(host)s/log/%(id)s">%(date)s, %(user)s: %(msg)s</a></li>' % content)
        text.append(u'<h3>Datens&auml;tze:</h3>')            
        for ds in site.datasets:
            content=dict(id=ds.id,name=ds.name,start=web.formatdate(ds.start),end=web.formatdate(ds.end),vt=ds.valuetype,host=host)
            text.append(u'<li><a href="%(host)s/dataset/%(id)s">%(name)s, %(vt)s (%(start)s-%(end)s)</a></li>' % content)
        return '<br/>'.join(text)
class VTPage:
    exposed=True
    
    @web.expose
    def default(self,vt_id='new'):
        session=db.Session()
        valuetypes=session.query(db.ValueType).order_by(db.ValueType.id).all()
        error=''
        if vt_id=='new':
            id = db.newid(db.ValueType,session)
            vt=db.ValueType(id=id,
                            name='<Name>')
        else:
            try:
                vt=session.query(db.ValueType).get(int(vt_id))
                #image=b64encode(self.sitemap.draw([actualsite]))
            except:
                error=traceback()
                #image=b64encode(self.sitemap.draw(sites.all()))
                vt=None
        
        result = web.render('valuetype.html',valuetypes=valuetypes,actualvaluetype=vt,error=error).render('html',doctype='html')
        session.close()
        return result    
    
    
    @web.expose
    def saveitem(self,**kwargs):
        try:
            id=web.conv(int,kwargs.get('id'),'')
        except:
            return web.render(error=traceback(),title='valuetype #%s' % kwargs.get('id'))
        if 'save' in kwargs:
            try:
                session = db.Session()        
                vt = session.query(db.ValueType).get(int(id))
                if not vt:
                    vt=db.ValueType(id=id)
                    session.add(vt)
                vt.name=kwargs.get('name')
                vt.unit=kwargs.get('unit')
                vt.comment=kwargs.get('comment')
                session.commit()
                session.close()
            except:
                return web.render('empty.html',error=traceback(),title='valuetype #%s' % id
                                  ).render('html',doctype='html')
        raise web.HTTPRedirect('./%s' % id)
class DatasetPage:
    exposed=True
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
        session.close()
        return result    
    @web.expose
    def kml(self,valuetypeid=None,user=None):
        session=db.Session()
        datasets = session.query(db.Dataset)
        try:
            if valuetypeid:
                vt = session.query(db.ValueType).get(int(valuetypeid))
                if vt:
                    datasets = datasets.filter(db.Dataset.valuetype==vt)
                else:
                    raise RuntimeError("Cannot find valuetype %s" % valuetypeid)
            if user:
                p = session.query(db.Persion).get(user)
                if p:
                    datasets = datasets.filter(db.Dataset.measured_by==p)
                else:
                    raise RuntimeError("Cannot find user %s" % user)
            sites=[d.site for d in datasets]
            web.setmime('application/vnd.google-earth.kml+xml')
            result = web.render('sites.xml',sites=sites,actid=0,descriptor=SitePage.kml_description).render('xml')
        except:
            error = traceback()
            web.setmime('text/html')

            result = web.render('dataset.html',error=error,datasets=datasets,session=session,db=db,activedataset=None,title="Schwangbach-Datenbank (Fehler)").render('html',doctype='html')
            
                    
                
        session.close()
        return result
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
                session.commit()
                session.close()
            except:
                return web.render('empty.html',error=traceback(),title='Dataset #%s' % id
                                  ).render('html',doctype='html')
        elif 'new' in kwargs:
            id='new'
        raise web.HTTPRedirect('./%s' % id)
class JobPage:
    exposed=True
    @web.expose
    def default(self,jobid='new',user=None):
        session=db.Session()
        error=''
        if jobid=='new':
            job = db.Job(id=db.newid(db.Job,session),name='<Job-Beschreibung>')
            if user:
                p_user = session.query(db.Person).get(user)
                job.responsible = p_user
        else:
            try:
                job = session.query(db.Job).get(int(jobid))
            except:
                error=traceback()
                job=None
        result = web.render('job.html',job=job,error=error,db=db,session=session
                            ).render('html',doctype='html')
        session.close()
        return result    
        
    @web.expose
    def saveitem(self,**kwargs):
        try:
            id=web.conv(int,kwargs.get('id'),'')
        except:
            return web.render(error=str(kwargs) + '\n' + traceback(),title='Job %s' % kwargs.get('id')
                              ).render('html',doctype='html')
        if 'save' in kwargs:
            try:
                session = db.Session()        
                job = session.query(db.Job).get(id)
                if not job:
                    job=db.Job(id=id)
                if kwargs.get('due'):
                    job.due=datetime.strptime(kwargs['due'],'%d.%m.%Y')
                job.filename = kwargs.get('filename')
                job.name=kwargs.get('name')
                job.description=kwargs.get('description')
                job.responsible = session.query(db.Person).get(kwargs.get('responsible'))
                job.author = session.query(db.Person).get(web.user())
                job.done = bool('done' in kwargs)
                job.nextreminder = job.due
                session.commit()
                session.close()
            except:
                return web.render('empty.html',error=('\n'.join('%s: %s' % it for it in kwargs.iteritems())) + '\n' + traceback(),
                                  title='Job #%s' % id
                                  ).render('html',doctype='html')
        elif 'new' in kwargs:
            id='new'
        raise web.HTTPRedirect('./%s' % id)
class LogPage:
    expose=True
    @web.expose
    def default(self,logid="new",siteid=None):
        session=db.Session()
        error=''
        if logid=='new':
            log = db.Log(id=db.newid(db.Log,session),message='<Log-Beschreibung>',time=datetime.today())
            user = web.user()
            if user:
                log.user = session.query(db.Person).get(user)
            if siteid:
                log.site = session.query(db.Site).get(int(siteid))
            log.time=datetime.today()
        else:
            try:
                log = session.query(db.Log).get(int(logid))
            except:
                error=traceback()
                log=None
        result = web.render('log.html',actuallog=log,error=error,db=db,session=session
                            ).render('html',doctype='html')
        session.close()
        return result    
    @web.expose
    def saveitem(self,**kwargs):
        try:
            id=web.conv(int,kwargs.get('id'),'')
        except:
            return web.render(error=str(kwargs) + '\n' + traceback(),title='Job %s' % kwargs.get('id')
                              ).render('html',doctype='html')
        if 'save' in kwargs:
            try:
                session = db.Session()        
                log = session.query(db.Log).get(id)
                if not log:
                    log=db.Log(id=id)
                if kwargs.get('date'):
                    log.time=datetime.strptime(kwargs['date'],'%d.%m.%Y')
                log.message=kwargs.get('message')
                log.user = session.query(db.Person).get(kwargs.get('user'))
                log.site = session.query(db.Site).get(kwargs.get('site'))
                session.commit()
                session.close()
            except:
                return web.render('empty.html',error=('\n'.join('%s: %s' % it for it in kwargs.iteritems())) + '\n' + traceback(),
                                  title='Log #%s' % id
                                  ).render('html',doctype='html')
        elif 'new' in kwargs:
            id='new'
        raise web.HTTPRedirect('./%s' % id)

            
                           
        
class MapPage(object):
    def index(self,valuetype=None,user=None,allsites=None):
        pass     
    
class Root(object):
    site=SitePage()
    user=PersonPage()
    valuetype=VTPage()
    dataset=DatasetPage()
    download=DownloadPage()
    job = JobPage()
    log = LogPage()
    
    @web.expose
    def index(self):
        return self.map()
    @web.expose
    def map(self,error=''):
        return web.render('map.html',error=error).render('html',doctype='html')

#if __name__=='__main__':
#    web.start_server(Root(), autoreload=False, port=8081)

