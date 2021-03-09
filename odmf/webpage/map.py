'''
Created on 12.07.2012

@author: philkraf
'''
from . import lib as web
from .. import db
from ..config import conf
from kajiki.template import literal


@web.show_in_nav_for(0, icon='map')
class MapPage(object):
    """
    The main map page
    """

    @web.expose
    @web.method.get
    def index(self):

        # The & is not working in the xml template as an uri literal. We define it here - that is simpler
        google_maps_querystring = f'key={conf.google_maps_api_key}&callback=initMap'

        return web.render('map.html', google_maps_querystring=google_maps_querystring).render()

    @web.expose
    @web.mime.json
    def sites(self):
        with db.session_scope() as session:

            return web.json_out(session.query(db.Site).order_by(db.Site.id).all())

    @web.expose
    def sitedescription(self, siteid):
        if not siteid:
            return('<div class="error">Site %s not found</div>' % siteid)
        session = db.Session()
        site = session.query(db.Site).get(int(siteid))
        res = web.render('sitedescription.html', site=site).render()
        session.close()
        return res
