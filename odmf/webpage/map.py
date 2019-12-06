'''
Created on 12.07.2012

@author: philkraf
'''
from . import lib as web
from .. import db


@web.show_in_nav_for(0)
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

        return web.render('map.html', site=site).render()

    @web.expose
    @web.json_out
    def sites(self):
        with db.session_scope() as session:

            return session.query(db.Site).order_by(db.Site.id).all()

    @web.expose
    def sitedescription(self, siteid):
        if not siteid:
            return('<div class="error">Site %s not found</div>' % siteid)
        session = db.Session()
        site = session.query(db.Site).get(int(siteid))
        res = web.render('sitedescription.html', site=site).render()
        session.close()
        return res
