# -*- coding: utf-8 -*-

'''
Created on 13.07.2012

@author: philkraf
'''
import datetime

import cherrypy
import pandas as pd
import io
from cherrypy.lib.static import serve_fileobj
from traceback import format_exc as traceback
from glob import glob
import os.path as op
import typing

from .. import lib as web
from ... import db
from ..auth import expose_for, Level
from io import BytesIO
from ...db import projection as proj
from ...config import conf


@web.expose
@web.show_in_nav_for(1, 'map-location')
@cherrypy.popargs('siteid')
class SitePage:
    url = conf.root_url + '/site/'
    @expose_for(Level.guest)
    def index(self, siteid=None, error=''):
        """
        Shows the page for a single site.
        """
        siteid = web.conv(int, siteid)
        if not siteid:
            return web.render('site-list.html', error=error)

        with db.session_scope() as session:

            datasets = instruments = []
            try:
                instruments = session.query(db.Datasource).order_by(db.Datasource.name)
                actualsite = session.get(db.Site, int(siteid))
                if not actualsite:
                    error = f'Site #{siteid} does not exist'
                else:
                    datasets = actualsite.datasets.join(db.ValueType).order_by(
                        db.ValueType.name, db.sql.desc(db.Dataset.end)
                    )
            except:
                error = traceback()
                actualsite = None
            return web.render('site.html', id=siteid, actualsite=actualsite, error=error,
                              datasets=datasets, icons=self.geticons(), instruments=instruments
                              ).render()

    @expose_for(Level.editor)
    @web.method.get
    def new(self, lat=None, lon=None, name=None, error=''):
        with db.session_scope() as session:
            datasets = instruments = []
            try:
                instruments = session.query(db.Datasource).order_by(db.Datasource.name)
                actualsite = db.Site(id=db.newid(db.Site, session),
                                     lon=web.conv(float, lon) or 8.55, lat=web.conv(float, lat) or 50.5,
                                     name=name or '<enter site name>')
            except:
                error = traceback()
                actualsite = None

            return web.render('site.html', id=int(actualsite.id), actualsite=actualsite, error=error,
                              datasets=datasets, icons=self.geticons(), instruments=instruments
                              ).render()

    @expose_for(Level.editor)
    @web.method.post
    def save(self, siteid, lon=None, lat=None, name=None, height=None, icon=None, comment=None):
        try:
            siteid = web.conv(int, siteid)
        except:
            raise web.redirect(f'{self.url}/{siteid}', error=traceback())
        with db.session_scope() as session:
            try:
                lon = web.conv(float, lon)
                lat = web.conv(float, lat)
                if lon > 180 or lat > 180:
                    lat, lon = proj.UTMtoLL(23, lat, lon, conf.utm_zone)
                if None in (lon, lat):
                    raise web.redirect(f'../{siteid}', error='The site has no coordinates')

                site = session.get(db.Site, siteid)
                if not site:
                    site = db.Site(id=siteid, lat=lat, lon=lon)
                    session.add(site)
                site.lat, site.lon = lat, lon
                site.name = name or site.name
                site.height = web.conv(float, height) or site.height
                site.icon = icon or site.icon
                site.comment = comment or site.comment
            except Exception as e:
                tb = traceback()
                raise web.redirect(f'{self.url}/{siteid}', error=f'## {e}\n\n```{tb}```')
        raise web.redirect(f'{self.url}/{siteid}')

    @expose_for(Level.editor)
    @web.method.post
    def savegeo(self, siteid, geojson=None, strokewidth=None, strokeopacity=None, strokecolor=None, fillopacity=None, fillcolor=None):
        import json
        with db.session_scope() as session:
            try:
                siteid = web.conv(int, siteid)
                site = session.get(db.Site, siteid)
                if not (siteid or site):
                    raise web.redirect(f'{self.url}/{siteid}', error=f'#{siteid} not found')
                if site.geometry:
                    geometry = site.geometry
                else:
                    geometry = db.site.SiteGeometry()

                geojson = json.loads(geojson)
                geometry.geojson = geojson or geometry.geojson
                geometry.strokewidth = strokewidth or geometry.strokewidth
                geometry.strokeopacity = strokeopacity or geometry.strokeopacity
                geometry.strokecolor = strokecolor or geometry.strokecolor
                geometry.fillopacity = fillopacity or geometry.fillopacity
                geometry.fillcolor = fillcolor or geometry.fillcolor
            except Exception as e:
                tb = traceback()
                raise web.redirect(f'{self.url}/{siteid}', error=f'## {e}\n\n```{tb}```')
        raise web.redirect(f'{self.url}/{siteid}')




    @expose_for()
    @web.mime.json
    def getinstalledinstruments(self):
        with db.session_scope() as session:
            inst = [
                inst for inst in session.query(db.Datasource)
                if inst.sites.count()
            ]
            return web.json_out(sorted(inst))

    @expose_for()
    @web.mime.json
    def getinstruments(self):
        with db.session_scope() as session:
            inst = session.query(db.Datasource).all()
            return web.json_out(sorted(inst))

    @expose_for(Level.editor)
    @web.method.post
    def addinstrument(self, siteid, instrumentid, date=None, comment=None):
        try:
            with db.session_scope() as session:

                date = web.parsedate(date)
                site = session.get(db.Site, int(siteid))
                instrument = session.get(db.Datasource, int(instrumentid))
                pot_installations = session.query(db.Installation)
                pot_installations = pot_installations.filter(
                    db.Installation.instrument == instrument, db.Installation.site == site)
                pot_installations = pot_installations.order_by(
                    db.sql.desc(db.Installation.id))
                if pot_installations.count():
                    instid = pot_installations.first().id
                else:
                    instid = 0
                inst = db.Installation(site, instrument, instid + 1, date, comment=comment)
                session.add(inst)

        except Exception as e:
            raise web.AJAXError(500, str(e))


    @expose_for(Level.editor)
    @web.method.post
    def removeinstrument(self, siteid, instrumentid, installationid, date=None):
        with db.session_scope() as session:
            try:
                date = web.parsedate(date)
                site = session.get(db.Site, int(siteid))
                inst: db.Installation = session.query(db.Installation).filter_by(
                    _site=int(siteid), _instrument=int(instrumentid), id=int(installationid)
                ).first()
                if inst:
                    inst.removedate = date
                    return 'Installation ' + str(inst) + ' removed'
                else:
                    error = f'Could not find installation to remove (siteid={site} id={instrumentid})'
                    raise web.AJAXError(500, error)

            except Exception as e:
                raise web.AJAXError(500, str(e))

    @staticmethod
    def sites_filter(session,
                     valuetype=None, instrument=None,
                     user=None, date=None, max_data_age=None,
                     fulltext=None, project=None) -> typing.Tuple[typing.List[db.Site], int]:
        """
        Returns the sites matching the filter variables as a geojson FeatureCollectiom

        Parameters
        ----------
        session:
            The database session object

        valuetype: id
            Return only sites with datasets containing this valuetype

        instrument: id
            Return only sites with an active installation of the given instrument_id,
            use '*' to match any active installation, negative number to include removed installations

        user:
            user name of user doing measurements at this site

        date: datetime
            Return only sites with datasets at this date

        max_data_age: int
            Only return sites where data has been collected in the last `max_data_age` days

        fulltext: str
            Return sites containing the fulltext in the title or the description

        project: int
            Returns sites with dataset from a specific project

        """

        valuetype = web.conv(int, valuetype)
        date = web.parsedate(date, False)
        max_data_age = web.conv(int, max_data_age)
        project = web.conv(int, project)
        Q = session.query
        if any([valuetype, user, date, max_data_age, project]):
            datasets = Q(db.Dataset)
            if valuetype:
                datasets = datasets.filter_by(_valuetype=valuetype)
            if user:
                datasets = datasets.filter_by(_measured_by=user)
            if date:
                datasets = datasets.filter(
                    db.Dataset.start <= date, db.Dataset.end >= date)
            if max_data_age:
                age = datetime.timedelta(days=max_data_age * 365.25)
                oldest = datetime.datetime.today() - age
                datasets = datasets.filter(db.Dataset.end >= oldest)
            if project:
                datasets = datasets.filter_by(_project=project)
            sites = {ds.site for ds in datasets}
        else:
            sites = set(session.query(db.Site))

        if instrument:
            if instrument == 'any':
                installations = Q(db.Installation).filter(db.Installation.removedate == None)
            elif instrument == 'installed':
                installations = Q(db.Installation).join(db.Datasource).filter(
                    db.Installation.removedate == None,
                    db.Datasource.sourcetype != 'manual'
                )
            else:
                instrument = web.conv(int, instrument)
                installations = Q(db.Installation).filter_by(_instrument=abs(instrument))
                if instrument > 0:
                    installations = installations.filter(db.Installation.removedate == None)
            sites &= {inst.site for inst in installations}
        if fulltext:
            from sqlalchemy import or_
            filter = Q(db.Site).filter(
                or_(
                    db.Site.name.ilike('%' + fulltext + '%'),
                    db.Site.comment.ilike('%' + fulltext + '%')
                )
            )
            sites &= set(filter)

        return sorted(sites, key=lambda s: s.id), len(sites)

    @expose_for()
    @web.mime.json
    @web.method.get
    def json(self, valuetype=None, instrument=None, user=None, date=None, max_data_age=None, fulltext=None, project=None, limit=None, page=None):
        """
        Returns the sites matching the filter variables as a geojson FeatureCollectiom

        Parameters
        ----------
        valuetype: id
            Return only sites with datasets containing this valuetype

        instrument: id
            Return only sites with an active installation of the given instrument_id,
            use '*' to match any active installation, negative number to include removed installations

        user:
            user name of user doing measurements at this site

        date: datetime
            Return only sites with datasets at this date

        max_data_age: int
            Only return sites where data has been collected in the last `max_data_age` days

        fulltext: str
            Return sites containing the fulltext in the title or the description

        """
        try:
            with db.session_scope() as session:
                sites, count = self.sites_filter(session, valuetype, instrument, user, date, max_data_age, fulltext, project)

                if page and limit:
                    page, limit = int(page), int(limit)
                    offset = (page - 1) * limit
                    sites = sites[offset:limit * page]

                return web.json_out(dict(sites=sites, count=count, limit=limit, page= page))
        except Exception as e:
            raise web.AJAXError(500, str(e))

    @expose_for()
    @web.mime.json
    @web.method.get
    def geojson(self, valuetype=None, instrument=None, user=None, date=None, max_data_age=None, fulltext=None, project=None, limit=None, offset=None):
        """
        Returns the sites matching the filter variables as a geojson FeatureCollection

        Parameters
        ----------
        valuetype: id
            Return only sites with datasets containing this valuetype

        instrument: id
            Return only sites with an active installation of the given instrument_id,
            use '*' to match any active installation, negative number to include removed installations

        user:
            user name of user doing measurements at this site

        date: datetime
            Return only sites with datasets at this date

        max_data_age: int
            Only return sites where data has been collected in the last `max_data_age` days

        fulltext: str
            Return sites containing the fulltext in the title or the description

        """
        try:
            with db.session_scope() as session:
                sites, count = self.sites_filter(session, valuetype, instrument, user, date, max_data_age, fulltext, project)
                geojson = {
                    "type": "FeatureCollection",
                    "features": [s.as_feature() for s in sites]
                }
                return web.json_out(geojson)
        except Exception as e:
            raise web.AJAXError(500, str(e))

    @expose_for()
    @web.mime.kml
    @web.method.get
    def kml(self, sitefilter=None):
        with db.session_scope() as session:
            query = session.query(db.Site)
            if filter:
                query = query.filter(sitefilter)
            stream = web.render('sites.xml', sites=query.all(),
                                actid=0, descriptor=SitePage.kml_description)
            return stream.render('xml')

    @classmethod
    def kml_description(cls, site):
        host = "http://fb09-pasig.umwelt.uni-giessen.de:8081"
        text = [site.comment,
                '<a href="%s/site/%s">edit...</a>' % (host, site.id)]
        if site.height:
            text.insert(0, '%0.1f m NN' % site.height)
        text.append('<h3>Logbuch:</h3>')
        for log in site.logs:
            content = dict(date=web.formatdate(log.time),
                           user=log.user, msg=log.message, host=host, id=log.id)
            text.append(
                '<li><a href="%(host)s/log/%(id)s">%(date)s, %(user)s: %(msg)s</a></li>' % content)
        text.append('<h3>Datens&auml;tze:</h3>')
        for ds in site.datasets:
            content = dict(id=ds.id, name=ds.name, start=web.formatdate(
                ds.start), end=web.formatdate(ds.end), vt=ds.valuetype, host=host)
            text.append(
                '<li><a href="%(host)s/dataset/%(id)s">%(name)s, %(vt)s (%(start)s-%(end)s)</a></li>' % content)
        return '<br/>'.join(text)

    def geticons(self):
        path = conf.abspath('media/mapicons')
        return sorted(op.basename(p) for p in glob(op.join(path, '*.png')) if not op.basename(p) == 'selection.png')

    @expose_for(Level.guest)
    @web.mime.json
    @web.method.get
    def with_instrument(self, instrumentid):
        with db.session_scope() as session:
            inst = session.get(db.Datasource, int(instrumentid))
            return web.json_out(sorted(set(i.site for i in inst.sites)))

    @expose_for(Level.logger)
    @web.mime.csv
    @web.method.get
    def sites_csv(self):
        with db.session_scope() as session:
            query = session.query(db.Site).order_by(db.Site.id)
            st = BytesIO()
            # TODO: Py3 encoding
            st.write(
                '"ID","long","lat","x_proj","y_proj","height","name","comment"\n'.encode('utf-8'))
            for s in query:
                c = s.comment.replace('\r', '').replace('\n', ' / ')
                h = '%0.3f' % s.height if s.height else ''
                Z, x, y = s.as_UTM()
                st.write(('%s,%f,%f,%0.1f,%0.1f,%s,"%s","%s"\n' %
                          (s.id, s.lon, s.lat, x, y, h, s.name, c)).encode('utf-8'))
            return st.getvalue()

    @expose_for(Level.logger)
    @web.method.get
    def export(self, format='xlsx'):
        from ...tools.exportdatasets import serve_dataframe
        with db.session_scope() as session:
            q = session.query(db.Site)
            dataframe = pd.read_sql(q.statement, session.bind)
            name = f'sites-{datetime.datetime.now():%Y-%m-%d}'
            return serve_dataframe(dataframe, f'{name}.{format}')
