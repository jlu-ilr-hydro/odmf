'''
Created on 12.07.2012

@author: philkraf
'''
import cherrypy

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
    def index(self, site=None):

        return web.render('site/map.html', site=site).render()

    @web.expose
    @web.method.post
    def allow_google(self, allow):
        cherrypy.session['allow_google_maps'] = allow == 'on'
        referer = cherrypy.request.headers.get('Referer')
        origin = cherrypy.request.headers.get('Origin')
        url = referer.replace(origin, '')
        raise web.redirect(url)

    @web.expose
    @web.mime.json
    def sites(self):
        with db.session_scope() as session:

            return web.json_out(session.query(db.Site).order_by(db.Site.id).all())

    @web.expose
    def sitedescription(self, siteid):
        if not siteid:
            return('<div class="error">Site %s not found</div>' % siteid)
        with db.session_scope() as session:
            if id:=web.conv(int, siteid):
                site = session.get(db.Site, id)
                return web.render('site/sitedescription.html', site=site).render()
            else:
                return ('<div class="alert alert-info">No site selected</div>')
            
