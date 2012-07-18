# -*- coding: utf-8 -*-

import lib as web
import db
import sys
from traceback import format_exc as traceback
from datetime import datetime
from genshi import escape

from webpage.upload import DownloadPage
from webpage.map import MapPage
from webpage.site import SitePage
from webpage.datasetpage import DatasetPage
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
        session=db.Session()
        web.setmime('application/json')
        persons = session.query(db.Person).order_by(db.sql.desc(db.Person.can_supervise),db.Person.surname)
        if supervisors:
            persons = persons.filter(db.Person.can_supervise==True)
        res = web.as_json(persons)
        session.close()
        return res

        
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
    @web.expose
    def json(self):
        session=db.Session()
        web.setmime('application/json')
        dump=web.as_json(session.query(db.ValueType))
        session.close()
        return dump
class DatasourcePage:
    exposed=True
    
    @web.expose
    def default(self,id='new'):
        session=db.Session()
        instruments=session.query(db.Datasource).order_by(db.Datasource.id)
        error=''
        if id=='new':
            newid = db.newid(db.Datasource,session)
            inst=db.Datasource(id=newid,
                               name='<Name>')
        else:
            try:
                inst=session.query(db.Datasource).get(int(id))
            except:
                error=traceback()
                inst=None
        
        result = web.render('instrument.html',instruments=instruments,actualinstrument=inst,error=error).render('html',doctype='html')
        session.close()
        return result    
    
    
    @web.expose
    def saveitem(self,**kwargs):
        try:
            id=web.conv(int,kwargs.get('id'),'')
        except:
            return web.render(error=traceback(),title='Datasource #%s' % kwargs.get('id'))
        if 'save' in kwargs:
            try:
                session = db.Session()        
                inst = session.query(db.Datasource).get(int(id))
                if not inst:
                    inst=db.Datasource(id=id)
                    session.add(inst)
                inst.name=kwargs.get('name')
                inst.sourcetype=kwargs.get('sourcetype')
                inst.comment=kwargs.get('comment')
                session.commit()
                session.close()
            except:
                return web.render('empty.html',error=traceback(),title='valuetype #%s' % id
                                  ).render('html',doctype='html')
        raise web.HTTPRedirect('./%s' % id)
    @web.expose
    def json(self):
        session=db.Session()
        web.setmime('application/json')
        dump=web.as_json(session.query(db.Datasource))
        session.close()
        return dump
    
    
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
    exposed=True
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
    @web.expose
    def json(self,siteid=None,user=None,old=None,new=None):
        session=db.Session()
        logs = session.query(db.Log)
        if siteid:
            logs=logs.filter_by(_site=int(siteid))
        if user:
            logs=logs.filter_by(_user=user)
        if old:
            old = web.parsedate(old)
            logs=logs.filter(db.Log.time>=old)
        if new:
            new = web.parsedate(new)
            logs=logs.filter(db.Log.time<=new)
        res = web.as_json(logs)
        session.close()
        return res
            
                           
        

class Root(object):
    site=SitePage()
    user=PersonPage()
    valuetype=VTPage()
    dataset=DatasetPage()
    download=DownloadPage()
    job = JobPage()
    log = LogPage()
    map=MapPage()
    instrument=DatasourcePage()
    @web.expose
    def index(self):
        return self.map.index()
    @web.expose
    def navigation(self):
        return web.navigation()
        

#if __name__=='__main__':
#    web.start_server(Root(), autoreload=False, port=8081)

