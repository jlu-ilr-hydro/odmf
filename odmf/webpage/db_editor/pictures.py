import cherrypy

from .. import lib as web
from ..auth import Level, expose_for
from ...config import conf

from ... import db

@cherrypy.popargs('id')
@web.show_in_nav_for(0, 'camera')
class PicturePage:
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

    @web.method.get
    @expose_for()
    def index(self, id=None, site=None, by=None):
        with db.session_scope() as session:
            img = imagelist = None
            error = ''
            if id:
                img = session.get(db.Image, int(id))
                if not img:
                    error = f"No image with id={id} found"
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
    @expose_for(Level.logger)
    def upload(self, imgfile, siteid, user, comment=''):
        if hasattr(imgfile, 'file'):
            imgfiles = [imgfile]
        else:
            imgfiles = imgfile
        with db.session_scope() as session:
            site = session.get(db.Site, int(siteid)) if siteid else None
            by = session.get(db.Person, user) if user else None
            username = by.username
            for imgfile in imgfiles:
                img = db.Image(site=site, by=by, imagefile=imgfile.file, comment=comment)
                session.add(img)
                session.flush()
        raise web.redirect(conf.url('picture'), site=siteid, by=username)

    @web.method.post
    @expose_for(Level.editor)
    def rotate(self, id, degrees):
        """
        Rotate image by (90, 180, 270, -90) degrees
        """
        with db.session_scope() as session:
            image = session.get(db.Image, int(id))
            image.rotate(int(degrees))


    @web.method.post
    @expose_for(Level.admin)
    def delete(self, id):
        """Delete image at imageid"""
        with db.session_scope() as session:
            img = session.get(db.Image, int(id))
            session.delete(img)

    @web.method.post
    @expose_for(Level.editor)
    def change(self, id, username=None, siteid=None, comment=None):
        """
        Change image metadata
        """
        with db.session_scope() as session:
            image = session.get(db.Image, int(id))
            if username and session.get(db.Person, username):
                image._by = username
            if siteid and (site:=session.get(db.Site, int(siteid))) :
                image.site = site
            if comment:
                image.comment = comment

        raise web.HTTPRedirect('.')

            

            
        

