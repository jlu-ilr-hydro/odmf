# -*- coding: utf-8 -*-

import lib
import db
from traceback import format_exc as traceback
from base64 import b64encode
import plotmap
from webpage.upload import DownloadPage
class PersonPage:
    exposed=True  
    @lib.expose
    @lib.output('person.html')    
    def default(self,act_user=''):
        session = db.Session()
        persons = session.query(db.Person)
        supervisors = persons.filter(db.Person.can_supervise>0)
        error=''
        try:
            p_act = session.query(db.Person).get(act_user)
        except:
            p_act=None
            error=traceback()   
        return lib.render(persons=persons,active_person=p_act,
                          supervisors=supervisors,error=error)

    @lib.expose
    def saveitem(self,**kwargs):
        username=kwargs.get('username')
        if 'save' in kwargs and username:
            session = db.Session()        
            p_act = session.query(db.Person).filter_by(username=username).first()
            if not p_act:
                p_act=db.Person(username=username)
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
        raise lib.HTTPRedirect('./' + username)

class SitePage:
    exposed=True  
    sitemap=plotmap.Map(lib.abspath('media/basemap150dpi.jpg'))
    @lib.expose
    @lib.output('site.html')
    def default(self,actualsite_id=None):
        session=db.Session()
        sites=session.query(db.Site).order_by(db.Site.name)
        error=''
        if actualsite_id=='new':
            actualsite=db.Site(id=db.newid(db.Site,session),
                               lon=8.55,lat=50.5,
                               name='<enter site name>')
        else:
            try:
                actualsite=session.query(db.Site).get(int(actualsite_id))
                #image=b64encode(self.sitemap.draw([actualsite]))
            except:
                error=traceback()
                #image=b64encode(self.sitemap.draw(sites.all()))
                actualsite=None
        
        return lib.render(sites=sites,actualsite=actualsite,error=error,image='')    
    @lib.expose
    @lib.output('empty.html')
    def saveitem(self,**kwargs):
        try:
            siteid=lib.conv(int,kwargs.get('id'),'')
        except:
            return lib.render(error=traceback(),title='site #%s' % kwargs.get('id'))
        if 'save' in kwargs:
            try:
                session = db.Session()        
                site = session.query(db.Site).get(int(siteid))
                if not site:
                    site=db.Site(id=id)
                site.lon=lib.conv(float,kwargs.get('lon'))
                site.lat=lib.conv(float,kwargs.get('lat'))
                site.name=kwargs.get('name')
                site.height=lib.conv(float,kwargs.get('height'))
                site.comment=kwargs.get('comment')
                session.commit()
            except:
                return lib.render(error=traceback(),title='site #%s' % siteid)
        elif 'new' in kwargs:
            siteid='new'
        raise lib.HTTPRedirect('./%s' % siteid)

    @lib.expose
    @lib.mimetype('application/vnd.google-earth.kml+xml')
    @lib.output('sites.xml', 'xml')
    def kml(self,sitefilter=None):
        session = db.Session()
        query = session.query(db.Site)
        if filter:
            query = query.filter(sitefilter)
        return lib.render(sites=query)
        
class Root(object):
    site=SitePage()
    user=PersonPage()
    bgmap=plotmap.BackgroundMap(lib.abspath('media/basemap150dpi.jpg'))
    bgmap.expose=True
    from upload import DownloadPage
    download=DownloadPage()
    
    @lib.expose
    @lib.output('empty.html')
    def index(self):
        return lib.render(title='Schwingbach - Home',error='')
    

        
if __name__=='__main__':
    
    lib.start_server(Root(), autoreload=False, port=8081)
            
            
            
        
        
