
from .. import lib as web
from ..auth import group, expose_for

from ... import db

from traceback import format_exc as traceback


@web.show_in_nav_for(1, 'thermometer-half')
class DatasourcePage:

    @expose_for(group.guest)
    def default(self, id='new'):
        session = db.Session()
        instruments = session.query(db.Datasource).order_by(db.Datasource.id)
        error = ''
        if id == 'new':
            newid = db.newid(db.Datasource, session)
            inst = db.Datasource(id=newid,
                                 name='<Name>')
        else:
            try:
                inst = session.query(db.Datasource).get(int(id))
            except:
                error = traceback()
                inst = None

        result = web.render('instrument.html', instruments=instruments,
                            actualinstrument=inst, error=error).render()
        session.close()
        return result

    @expose_for(group.editor)
    def saveitem(self, **kwargs):
        try:
            id = web.conv(int, kwargs.get('id'), '')
        except:
            return web.render(error=traceback(), title='Datasource #%s' % kwargs.get('id'))
        if 'save' in kwargs:
            try:
                session = db.Session()
                inst = session.query(db.Datasource).get(int(id))
                if not inst:
                    inst = db.Datasource(id=id)
                    session.add(inst)
                inst.name = kwargs.get('name')
                inst.sourcetype = kwargs.get('sourcetype')
                inst.comment = kwargs.get('comment')
                inst.manuallink = kwargs.get('manuallink')
                session.commit()
                session.close()
            except:
                return web.render('empty.html', error=traceback(), title='valuetype #%s' % id
                                  ).render()
        raise web.redirect('./%s' % id)

    @expose_for()
    @web.mime.json
    def json(self):
        with db.session_scope() as session:
            return web.json_out(session.query(db.Datasource).all())
