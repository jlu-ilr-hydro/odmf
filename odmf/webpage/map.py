'''
Created on 12.07.2012

@author: philkraf
'''
from . import lib as web
from .. import db
from .datasetpage import DatasetPage
from .preferences import Preferences


class MapPage(object):
    exposed = True

    @web.expose
    def index(self, site=None):
        if site is None:
            site = 'null'
        else:
            session = db.Session()

            # decode for valid json string
            site = web.as_json(db.Site.get(session, int(site))).decode('utf-8')

            session.close()
        return web.render('map.html', site=site).render('html', doctype='html')

    @web.expose
    def sites(self):
        session = db.Session()
        web.setmime('application/json')
        sites = session.query(db.Site).order_by(db.Site.id)
        res = web.as_json(sites.all())
        session.close()
        return res

    @web.expose
    def sitedescription(self, siteid):
        if not siteid:
            return('<div class="error">Site %s not found</div>' % siteid)
        session = db.Session()
        site = session.query(db.Site).get(int(siteid))
        res = web.render('sitedescription.html', site=site).render('html')
        session.close()
        return res
