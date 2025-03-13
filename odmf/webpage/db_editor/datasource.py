
from .. import lib as web
from ..auth import Level, expose_for

from ... import db

from traceback import format_exc as traceback

@web.show_in_nav_for(2, 'thermometer-half')
class DatasourcePage:

    @expose_for(Level.guest)
    def default(self, id='new'):
        with db.session_scope() as session:
            instruments = session.query(db.Datasource).order_by(db.Datasource.id)
            error = ''
            if id == 'new':
                newid = db.newid(db.Datasource, session)
                inst = db.Datasource(id=newid,
                                     name='<Name>')
            else:
                try:
                    inst = session.get(db.Datasource, int(id))
                except:
                    error = traceback()
                    inst = None

            return web.render('dataset/instrument.html', instruments=instruments,
                            actualinstrument=inst, error=error).render()

    @expose_for(Level.editor)
    def saveitem(self, **kwargs):
        try:
            id = web.conv(int, kwargs.get('id'), '')
        except:
            return web.render(error=traceback(), title='Datasource #%s' % kwargs.get('id'))
        if 'save' in kwargs:
            try:
                with db.session_scope() as session:
                    inst = session.get(db.Datasource, int(id))
                    if not inst:
                        inst = db.Datasource(id=id)
                        session.add(inst)
                    inst.name = kwargs.get('name')
                    inst.sourcetype = kwargs.get('sourcetype')
                    inst.comment = kwargs.get('comment')
                    inst.manuallink = kwargs.get('manuallink')
            except:
                return web.render('empty.html', error=traceback(), title='valuetype #%s' % id
                                  ).render()
        raise web.redirect('./%s' % id)

    @expose_for()
    @web.mime.json
    def json(self):
        with db.session_scope() as session:
            return web.json_out(session.query(db.Datasource).all())
