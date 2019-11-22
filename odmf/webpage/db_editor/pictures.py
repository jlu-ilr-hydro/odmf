import cherrypy

from .. import lib as web
from ..auth import group, expose_for

from ... import db


class PicturePage(object):
    """
    Displaying all images and providing image/thumbnail

    See memoryview doc for python3 tobytes
    """
    exposed = True

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
        session = db.Session()
        error = ''
        img = imagelist = None
        if id:
            img = session.query(db.Image).get(int(id))
            if not img:
                error = "No image with id=%s found" % id
        else:
            imagelist = session.query(db.Image).order_by(
                db.Image._site, db.Image.time)
            if site:
                imagelist = imagelist.filter_by(_site=site)
            if by:
                imagelist = imagelist.filter_by(_by=by)
        res = web.render('picture.html', image=img, error=error,
                         images=imagelist, site=site, by=by).render('html')
        session.close()
        print('Image:Index(%s, %s, %s)' % (id, site, by))
        return res

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
        raise web.HTTPRedirect('/picture?id=%i' % imgid)
