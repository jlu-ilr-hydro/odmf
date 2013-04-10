'''
Created on 12.07.2012

@author: philkraf
'''
import lib as web
import db
from datasetpage import DatasetPage
class MapPage(object):
    exposed=True
    @web.expose
    def index(self):
        #res = file(web.abspath('templates/map.html')).read();
        #return res.replace("${navigation('Map')}",web.navigation('Map'))  
        return web.render('map.html').render('html',doctype='html')
    @web.expose
    def sites(self):
        session=db.Session()
        web.setmime('application/json')
        sites = session.query(db.Site).order_by(db.Site.id)
        res = web.as_json(sites.all())
        session.close()
        return res

    @web.expose
    def sitedescription(self,siteid):
        if not siteid:
            return('<div class="error">Site %s not found</div>' % siteid)
        session=db.Session()
        site=session.query(db.Site).get(int(siteid))
        res = web.render('sitedescription.html',site=site).render('html')
        session.close()
        return res
