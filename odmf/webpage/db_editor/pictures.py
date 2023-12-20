import cherrypy

from kajiki.template import literal

from .. import lib as web
from ..auth import group, expose_for
from ...config import conf

from ... import db


@web.show_in_nav_for(0, 'camera')
class PicturePage(object):
    """
    Navigation and search for photos from the observatory
    """

    @expose_for()
    def image(self, id):
        with db.session_scope() as session:
            img = session.get(db.Image, int(id))

            if img:
                web.mime.set(img.mime)
                res = img.image
                return res
            else:
                raise web.HTTPError(404)

    @expose_for()
    def thumbnail(self, id):
        with db.session_scope() as session:
            img = session.get(db.Image, int(id))

            if img:
                web.mime.set(img.mime)
                res = img.thumbnail
                return res
            else:
                raise web.HTTPError(404)


    @expose_for()
    def index(self, id='', site='', by=''):
        with db.session_scope() as session:
            img = imagelist = None
            error = ''
            if id:
                img = session.get(db.Image, int(id))
                if not img:
                    error = "No image with id=%s found" % id
            else:
                imagelist = session.query(db.Image).order_by(
                    db.Image._site, db.Image.time
                )
                if site:
                    imagelist = imagelist.filter_by(_site=site)
                if by:
                    imagelist = imagelist.filter_by(_by=by)
            return web.render('picture.html', picture=img, error=error, imagelist=imagelist, site=site, by=by).render()

    @web.method.post
    @expose_for(group.logger)
    def upload(self, imgfile, siteid, user):
        with db.session_scope() as session:
            site = session.get(db.Site, int(siteid)) if siteid else None
            by = session.get(db.Person, user) if user else None
            img = db.Image(site=site, by=by, imagefile=imgfile.file)
            session.add(img)
            session.flush()
            imgid = img.id

        raise web.redirect(conf.root_url + '/picture', id=imgid)
