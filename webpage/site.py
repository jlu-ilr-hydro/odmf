# -*- coding: utf-8 -*-

'''
Created on 13.07.2012

@author: philkraf
'''
import lib as web
import db
from traceback import format_exc as traceback
from datetime import datetime
from genshi import escape
from glob import glob
import os.path as op
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
            result=web.render('newsite.html',actualsite=actualsite,icons=self.geticons()).render('xml')
        else:        
            result= web.Markup('<div class="error">%s</div>' % error)
        session.close()
        return result
    @web.expose
    def getinstruments(self):
        web.setmime('application/json')
        session=db.Session()
        res=web.as_json(session.query(db.Datasource))
        session.close()
        return res
    
    @web.expose
    def addinstrument(self,siteid,instrumentid,date=None):
        if not instrumentid:
            raise web.HTTPRedirect('/instrument/new')
        session=db.Session()
        error=''
        try:
            date=web.parsedate(date)
            site = session.query(db.Site).get(int(siteid))
            instrument = session.query(db.Datasource).get(int(instrumentid))
            pot_installations = session.query(db.Installation)
            pot_installations=pot_installations.filter(db.Installation.instrument==instrument,db.Installation.site==site)
            pot_installations=pot_installations.order_by(db.sql.desc(db.Installation.id))
            if pot_installations.count():
                instid = pot_installations.first().id
            else:
                instid = 0
            inst = db.Installation(site, instrument, instid+1, date)
            session.add(inst)
            session.commit()
        except:
            error=traceback()
        finally:
            session.close()
        return error
    @web.expose
    def removeinstrument(self,siteid,instrumentid,installationid,date=None):
        session=db.Session()
        error=''
        try:
            date=web.parsedate(date)
            site = session.query(db.Site).get(int(siteid))
            instrument = session.query(db.Datasource).get(int(instrumentid))
            pot_installations = session.query(db.Installation)
            pot_installations=pot_installations.filter(db.Installation.instrument==instrument,db.Installation.site==site)
            pot_installations=pot_installations.order_by(db.sql.desc(db.Installation.id))
            inst = pot_installations.filter_by(id=int(installationid)).first()
            if inst:
                inst.removedate = date
                session.commit()
            else:
                error='Could not find installation to remove (siteid=%s,instrument=%s,id=%s)' % (siteid,instrumentid,installationid)
                session.rollback()
        except:
            error=traceback()
            session.rollback()
        finally:
            session.close()
        return error
    @web.expose
    def json(self):
        session=db.Session()
        web.setmime('application/json')
        res = web.as_json(session.query(db.Site).order_by(db.Site.id))
        session.close()
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
    def geticons(self):
        path = web.abspath('media/mapicons')
        return [op.basename(p) for p in glob(op.join(path,'*.png'))]
        
        
