import cherrypy

from ...config import conf
from .. import lib as web
from ..auth import Level, expose_for
from ... import db

from traceback import format_exc as traceback

@web.show_in_nav_for(2, 'thermometer-half')
@cherrypy.popargs('instid')
class DatasourcePage:

    @expose_for(Level.guest)
    def index(self, instid=None, **kwargs):
        if cherrypy.request.method == 'GET':
            with db.session_scope() as session:
                instruments = db.sql.select(db.Datasource).order_by(db.Datasource.name)
                if instid == 'new':
                    instid = db.newid(db.Datasource, session)
                    inst = db.Datasource(id=instid)
                else:
                    inst = session.get(db.Datasource, web.conv(int, instid))
                sites = db.sql.select(db.Site).order_by(db.Site.id)


                return web.render(
                    'dataset/instrument.html',
                    instruments=session.scalars(instruments).all(),
                    actualinstrument=inst,
                    sites=session.scalars(sites),

                ).render()

        elif cherrypy.request.method == 'POST':
            with db.session_scope() as session:
                inst = session.get(db.Datasource, web.conv(int, instid))
                if inst is None:
                    instid = db.newid(db.Datasource, session)
                    inst = db.Datasource(id=instid)
                    session.add(inst)
                    session.flush()

                inst.name = kwargs.get('name')
                inst.sourcetype = kwargs.get('sourcetype')
                inst.comment = kwargs.get('comment')
                inst.manuallink = kwargs.get('manuallink')

                redirect = conf.url('instrument', inst.id)
            raise web.redirect(redirect, success='Instrument saved')


    @expose_for()
    @web.mime.json
    def json(self):
        with db.session_scope() as session:
            return web.json_out(session.query(db.Datasource).all())
