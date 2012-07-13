'''
Created on 12.07.2012

@author: philkraf
'''
import lib as web
import db

class MapPage(object):
    exposed=True
    @web.expose
    def index(self):
        return file(web.abspath('templates/map.html'))  
    @web.expose
    def sites(self):
        session=db.Session()
        web.setmime('application/json')
        res = web.as_json(session.query(db.Site).order_by(db.Site.id))
        session.close()
        return res

        res = json.dumps(sites,indent=4)
        return res
    @web.expose
    def sitedescription(self,siteid=0):
        if not siteid:
            return('<div class="error">Site %s not found</div>' % siteid)
        session=db.Session()
        site=session.query(db.Site).get(int(siteid))
        res = web.render('sitedescription.html',site=site).render('html')
        session.close()
        return res
