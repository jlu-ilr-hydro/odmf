

from .. import lib as web
from ..auth import group, expose_for

from ... import db
from traceback import format_exc as traceback


@web.show_in_nav_for(1, 'ruler')
class VTPage:

    @expose_for(group.guest)
    def default(self, vt_id='new'):
        session = db.Session()
        valuetypes = session.query(
            db.ValueType).order_by(db.ValueType.id).all()
        error = ''
        if vt_id == 'new':
            id = db.newid(db.ValueType, session)
            vt = db.ValueType(id=id,
                              name='<Name>')
        else:
            try:
                vt = session.query(db.ValueType).get(int(vt_id))
                # image=b64encode(self.sitemap.draw([actualsite]))
            except:
                error = traceback()
                # image=b64encode(self.sitemap.draw(sites.all()))
                vt = None

        result = web.render('valuetype.html', valuetypes=valuetypes,
                            actualvaluetype=vt, error=error).render()
        session.close()
        return result

    @expose_for(group.supervisor)
    def saveitem(self, **kwargs):
        try:
            id = web.conv(int, kwargs.get('id'), '')
        except:
            return web.render(error=traceback(), title='valuetype #%s' % kwargs.get('id'))
        if 'save' in kwargs:
            try:
                session = db.Session()
                vt = session.query(db.ValueType).get(int(id))
                if not vt:
                    vt = db.ValueType(id=id)
                    session.add(vt)
                vt.name = kwargs.get('name')
                vt.unit = kwargs.get('unit')
                vt.minvalue = web.conv(float, kwargs.get('minvalue'))
                vt.maxvalue = web.conv(float, kwargs.get('maxvalue'))
                vt.comment = kwargs.get('comment')
                session.commit()
                session.close()
            except:
                return web.render('empty.html', error=traceback(), title='valuetype #%s' % id
                                  ).render()
        raise web.redirect('./%s' % id)

    @expose_for(group.guest)
    @web.mime.json
    def json(self):
        with db.session_scope() as session:
            return web.json_out(session.query(db.ValueType).all())
