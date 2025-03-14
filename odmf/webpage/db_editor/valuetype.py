import cherrypy

from .. import lib as web
from ..auth import Level, expose_for

from ... import db
from ...config import conf



@web.show_in_nav_for(2, 'ruler')
@cherrypy.popargs('vt_id')
class VTPage:

    @expose_for(Level.guest)
    def index(self, vt_id=None, **kwargs):
        if cherrypy.request.method == 'GET':
            with db.session_scope() as session:
                valuetypes = session.query(
                    db.ValueType).order_by(db.ValueType.id).all()
                error = ''
                if vt_id == 'new':
                    id = db.newid(db.ValueType, session)
                    vt = db.ValueType(id=id)
                elif vt_id:
                    vt = session.get(db.ValueType, web.conv(int, vt_id))
                else:
                    vt = None
                return web.render('dataset/valuetype.html', valuetypes=valuetypes,
                                    actualvaluetype=vt).render()
        elif cherrypy.request.method == 'POST':
            with db.session_scope() as session:
                vt = session.get(db.ValueType, web.conv(int, vt_id))
                if not vt:
                    vt = db.ValueType()
                    session.add(vt)
                    session.flush()
                vt.name = kwargs.get('name')
                vt.unit = kwargs.get('unit')
                vt.minvalue = web.conv(float, kwargs.get('minvalue'))
                vt.maxvalue = web.conv(float, kwargs.get('maxvalue'))
                vt.comment = kwargs.get('comment')
                redirect = conf.url('valuetype', vt.id)
        raise web.redirect(redirect, success='Valuetype saved')

    @expose_for(Level.guest)
    @web.mime.json
    def json(self):
        with db.session_scope() as session:
            return web.json_out(session.query(db.ValueType).all())
