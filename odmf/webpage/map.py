'''
Created on 12.07.2012

@author: philkraf
'''
from . import lib as web
from .. import db


@web.expose
class MapPage(object):

    @web.expose
    def index(self, site=None):
        if site is None:
            site = 'null'
        else:
            with db.session_scope() as session:
                # decode for valid json string
                site = web.as_json(
                    session.query(db.Site).get(int(site))
                ).decode('utf-8')

        return web.render('map.html', site=site).render('html', doctype='html')

    @web.expose
    @web.mime.json
    def sites(self):
        session = db.Session()
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
