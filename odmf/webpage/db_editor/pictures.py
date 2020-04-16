import cherrypy

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
            img = session.query(db.Image).get(int(id))

            if img:
                web.mime.set(img.mime)
                res = img.image
                return res
            else:
                raise cherrypy.HTTPError(404)

    @expose_for()
    def thumbnail(self, id):
        with db.session_scope() as session:
            img = session.query(db.Image).get(int(id))

            if img:
                web.mime.set(img.mime)
                res = img.thumbnail
                return res
            else:
                raise cherrypy.HTTPError(404)

    @expose_for()
    def imagelist_json(self, site=None, by=None):
        session = db.Session()
        imagelist = session.query(db.Image).order_by(
            db.Image._site, db.Image.time)
        if site:
            imagelist.filter(db.Image._site == site)
        if by:
            imagelist.filter(db.Image._by == by)
        res = web.as_json(imagelist.all())
        session.close()
        return bytearray(res)

    @expose_for()
    def index(self, id='', site='', by=''):
        with db.session_scope() as session:
            img = imagelist = None
            error = ''
            if id:
                img = session.query(db.Image).get(int(id))
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
            # TODO: UnboundLocalError: local variable 'image' referenced before assignment
            return web.render('picture.html', picture=img, error=error, imagelist=imagelist, site=site, by=by).render()

    @expose_for(group.logger)
    def upload(self, imgfile, siteid, user):
        session = db.Session()
        site = session.query(db.Site).get(int(siteid)) if siteid else None
        by = session.query(db.Person).get(user) if user else None
        # io = StringIO()
        # for l in imgfile:
        #    io.write(l)
        # io.seek(0)
        img = db.Image(site=site, by=by, imagefile=imgfile.file)
        session.add(img)
        session.commit()
        imgid = img.id
        session.close()
        raise web.redirect(conf.root_url + '/picture?id=%i' % imgid)
