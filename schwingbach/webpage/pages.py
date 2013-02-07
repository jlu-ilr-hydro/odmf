# -*- coding: utf-8 -*-

import lib as web
from auth import users, require, member_of, has_level, group, expose_for
import db
import sys
from traceback import format_exc as traceback
from datetime import datetime, timedelta
from genshi import escape

from webpage.upload import DownloadPage
from webpage.map import MapPage
from webpage.site import SitePage
from webpage.datasetpage import DatasetPage
from webpage.preferences import Preferences
from webpage.plot import PlotPage 
class PersonPage:
    exposed=True
    
    @expose_for(group.guest)
    def default(self,act_user=None):
        session = db.Session()
        persons = session.query(db.Person).order_by(db.sql.desc(db.Person.can_supervise),db.Person.surname)
        supervisors = persons.filter(db.Person.can_supervise==True)
        error=''
        jobs=[]
        act_user = act_user or users.current.name
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
    @expose_for(group.supervisor)
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
    
    @expose_for()
    def json(self,supervisors=False):
        session=db.Session()
        web.setmime('application/json')
        persons = session.query(db.Person).order_by(db.sql.desc(db.Person.can_supervise),db.Person.surname)
        if supervisors:
            persons = persons.filter(db.Person.can_supervise==True)
        res = web.as_json(persons.all())
        session.close()
        return res

        
class VTPage:
    exposed=True
    @expose_for(group.guest)
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
    
    @expose_for(group.editor)
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
    
    @expose_for(group.guest)
    def json(self):
        session=db.Session()
        web.setmime('application/json')
        dump=web.as_json(session.query(db.ValueType).all())
        session.close()
        return dump
class DatasourcePage:
    exposed=True
    
    @expose_for(group.guest)
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
    
    @expose_for(group.editor) 
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
                inst.manuallink=kwargs.get('manuallink')
                session.commit()
                session.close()
            except:
                return web.render('empty.html',error=traceback(),title='valuetype #%s' % id
                                  ).render('html',doctype='html')
        raise web.HTTPRedirect('./%s' % id)
    @expose_for()
    def json(self):
        session=db.Session()
        web.setmime('application/json')
        dump=web.as_json(session.query(db.Datasource).all())
        session.close()
        return dump
    
    
class JobPage:
    exposed=True
    
    @expose_for(group.logger)
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
    
    @expose_for(group.editor)    
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
    @expose_for(group.guest)
    def default(self,logid=None,siteid=None,lastlogdate=None,days=None):
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
        elif logid is None:
            log=session.query(db.Log).order_by(db.sql.desc(db.Log.time)).first()
        else:
            try:
                log = session.query(db.Log).get(int(logid))
            except:
                error=traceback()
                log=None
        if lastlogdate:
            until=web.parsedate(lastlogdate)
        else:
            until = datetime.today()
        days = web.conv(int,days, 30)
        loglist = session.query(db.Log).filter(db.Log.time<=until,db.Log.time>=until-timedelta(days=days)).order_by(db.sql.desc(db.Log.time))
        result = web.render('log.html',actuallog=log,error=error,db=db,session=session,loglist=loglist,
                            ).render('html',doctype='html')
        session.close()
        return result    
    
    @expose_for(group.logger)
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
    @expose_for(group.supervisor)
    def remove(self,id):
        session = db.Session()
        log = session.query(db.Log).get(id)
        if log:
            session.delete(log)
            session.commit()
        raise web.HTTPRedirect('/log')
    
    
    @expose_for()
    def json(self,siteid=None,user=None,old=None,until=None,days=None):
        session=db.Session()
        web.setmime('application/json')

        logs = session.query(db.Log).order_by(db.sql.desc(db.Log.time))
        if siteid:
            logs=logs.filter_by(_site=int(siteid))
        if user:
            logs=logs.filter_by(_user=user)
        if until:
            until = web.parsedate(until)
            logs=logs.filter(db.Log.time<=until)
        if old:
            old = web.parsedate(old)
            logs=logs.filter(db.Log.time>=old)
        elif days:
            days = int(days)
            if until:
                old = until - timedelta(days=days)
            else:
                old = datetime.today() - timedelta(days=days)
            logs=logs.filter(db.Log.time>=old)
           
            
        res = web.as_json(logs.all())
        session.close()
        return res
    
    @expose_for(group.logger)
    def fromclipboard(self,paste):
        web.setmime('text/html')
        lines=paste.splitlines()
        session=db.Session()
        def _raise(line,errormsg):
            raise RuntimeError("Could not create log from:\n'%s'\nReason:%s" % (line,errormsg))
        def parseline(line):
            line = line.replace('\t','|')
            ls = line.split('|')
            if len(ls)<2:
                _raise(line,"At least a message and a siteid, seperated by a tab or | are needed to create a log")
            msg=ls[0]
            try:
                siteid = int(ls[1])
                site = session.query(db.Site).get(siteid)
                if not site: raise RuntimeError()
            except:
                _raise(line,"%s is not a site id" % ls[1])
            if len(ls)>2:
                date = web.parsedate(ls[2])
            else:
                date = datetime.today()
            if len(ls)>3:
                user = session.query(db.Person).get(ls[3])
                if not user: _raise(line,"Username '%s' is not in the database" % ls[3])
            else:
                user=session.query(db.Person).get(web.user())
            logid = db.newid(db.Log,session)
            return db.Log(id=logid,site=site,user=user,message=msg,time=date)
        errors=[]
        logs=[]
        for l in lines:
            try:
                log=parseline(l)
                logs.append(log)
            except Exception as e:
                errors.append(e.message)
        if errors:
            res='Import logs from Clipboard failed with the following errors:<ol>'
            li = ''.join('<li>%s</li>' % e for e in errors)
            return res+li+'</ol>'
        else:
            session.add_all(logs)
            session.commit()
                           
    
            
            
class HeapyPage(object):
    exposed=True
    def __init__(self,hp):
        self.hp=hp
    @expose_for(group.admin)
    def index(self):
        web.setmime('text/plain')
        h = self.hp.heap()
        return str(h)                 

class PicturePage(object):
    exposed=True
    @expose_for()
    def image(self,id):
        session=db.Session()
        img=db.Image.get(session,int(id))
        web.setmime(img.mime)
        res = img.image
        session.close()
        return res
    @expose_for()
    def thumbnail(self,id):
        session=db.Session()
        img=db.Image.get(session,int(id))
        web.setmime(img.mime)
        res = img.thumbnail
        session.close()
        return res
    @expose_for()
    def index(self,id=None,site=None,by=None):
        session=db.Session()
        error=''
        img = imagelist = None
        if id:
            img=db.Image.get(session,int(id))
            if not img: error="No image with id=%s found" % id
        else:
            imagelist = session.query(db.Image).order_by(db.Image._site,db.Image.time)
            if site:
                imagelist.filter(db.Image._site == site)
            if by:
                imagelist.filter(db.Image._by == by)
        res = web.render('picture.html',image=img,error=error,images=imagelist).render('html')
        session.close()
        return res
        
               
        

        

class Root(object):
    _cp_config = {'tools.sessions.on': True,
                  'tools.sessions.timeout':7*24*60, # One Week
                  'tools.sessions.storage_type':'ram',
                  'tools.sessions.storage_path':web.abspath('sessions'), 
                  'tools.auth.on': True}

    site=SitePage()
    user=PersonPage()
    valuetype=VTPage()
    dataset=DatasetPage()
    download=DownloadPage()
    job = JobPage()
    log = LogPage()
    map=MapPage()
    instrument=DatasourcePage()
    picture = PicturePage()
    preferences = Preferences()
    plot = PlotPage()
    
    @expose_for()
    def index(self):
        return self.map.index()
    
    @expose_for()
    def navigation(self):
        return web.navigation()
    
    @expose_for()
    def login(self,frompage='/',username=None,password=None,error='',logout=None):
        if logout:
            users.logout()
            raise web.HTTPRedirect(frompage or '/')
        elif username and password:
            error=users.login(username, password)
            if error:
                return web.render('login.html',error=error,frompage=frompage).render('html',doctype='html')
            else:
                raise web.HTTPRedirect(frompage or '/')
        else:
            return web.render('login.html',error=error,frompage=frompage).render('html',doctype='html')
    @expose_for(group.admin)
    def showjson(self,**kwargs):
        web.setmime('application/json')
        import json
        return json.dumps(kwargs,indent=4)
        
    


        

#if __name__=='__main__':
#    web.start_server(Root(), autoreload=False, port=8081)
