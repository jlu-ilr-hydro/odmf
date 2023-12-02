import sqlalchemy as sql
import sqlalchemy.orm as orm
from datetime import datetime
from functools import total_ordering

from .projection import LLtoUTM, dd_to_dms, UTMtoLL
from .base import Base
from ..config import conf

from logging import getLogger
logger = getLogger(__name__)


@total_ordering
class Site(Base):
    """
    All locations in the database. The coordiante system is always geographic with WGS84/ETRS
    """
    __tablename__ = 'site'
    id = sql.Column(sql.Integer, primary_key=True)
    lat = sql.Column(sql.Float)
    lon = sql.Column(sql.Float)
    height = sql.Column(sql.Float)
    name = sql.Column(sql.String)
    comment = sql.Column(sql.String)
    icon = sql.Column(sql.String(30))
    geometry = orm.relationship("SiteGeometry", back_populates='site', uselist=False, cascade="save-update, merge, delete, delete-orphan")

    def __init__(self, id:int, lat:float=None, lon:float=None,
                 height:float = None, name:str=None, comment:str=None, icon:str=None,
                 x:float = None, y:float=None):
        self.id = id
        if lat and lon:
            self.lat = lat
            self.lon = lon
        elif x and y:
            self.lat, self.lon = UTMtoLL(23, y, x, conf.utm_zone)
        else:
            raise ValueError('Creating a site needs the position in geographical coordinates '
                             '(lat/lon) or as UTM coordinates (x/y)')
        self.height = height
        self.name = name
        self.comment = comment
        self.icon = icon

    def __str__(self):
        return "#%i - %s" % (self.id, self.name)

    def __jdict__(self):
        return dict(id=self.id,
                    lat=self.lat,
                    lon=self.lon,
                    height=self.height,
                    name=self.name,
                    comment=self.comment,
                    icon=self.icon,
                    )

    def __eq__(self, other):
        if hasattr(other, 'id'):
            return NotImplemented
        return self.id == other.id

    def __lt__(self, other):
        if not hasattr(other, 'id'):
            return NotImplemented
        return self.id < other.id

    def __hash__(self):
        return hash(str(self))

    def as_UTM(self):
        """Returns a tuple (x,y) as UTM/WGS84 of the site position
        If withzone is True it returns the name of the UTM zone as a third argument
        """
        return LLtoUTM(23, self.lat, self.lon)

    def as_coordinatetext(self):
        lat = dd_to_dms(self.lat)
        lon = dd_to_dms(self.lon)
        return ("%i° %i' %0.2f''N - " % lat) + ("%i° %i' %0.2f''E" % lon)

    @property
    def __geo_interface__(self):
        if self.geometry:
            return self.geometry.geojson
        else:
            return {"type": "Point", "coordinates": [self.lat, self.lon]}

    def as_feature(self) -> dict:
        """
        Returns the geometry as a GeoJson feature. Style is a nested property
        :return:
        """
        if self.geometry:
            return self.geometry.as_feature()
        else:
            return {
                "type": "Feature",
                "geometry": self.__geo_interface__,
                "properties": self.__jdict__()
            }


@total_ordering
class SiteGeometry(Base):
    """
    Enhance a site with Geometry features, like line or polygon

    Uses GeoJSON definition to save the geometry of a site
    https://de.wikipedia.org/wiki/GeoJSON
    """
    __tablename__ = 'site_geometry'

    id = sql.Column(sql.Integer, sql.ForeignKey('site.id'), primary_key=True, )
    site = orm.relationship('Site', back_populates='geometry')
    geojson = sql.Column(sql.JSON)  # Contains coordinates in GeoJSON notation
    strokewidth = sql.Column(sql.Float)
    strokeopacity = sql.Column(sql.Float)
    strokecolor = sql.Column(sql.Text)
    fillcolor = sql.Column(sql.Text)
    fillopacity = sql.Column(sql.Float)

    @property
    def __geo_interface__(self):
        return self.geojson
    
    def get_style(self):
        res = {}
        if self.strokewidth:
            res['strokeWidth'] = self.strokewidth
        if self.strokecolor:
            res['strokeColor'] = self.strokecolor
        if self.strokeopacity:
            res['strokeOpacity'] = self.strokeopacity
        if self.fillcolor:
            res['fillColor'] = self.fillcolor
        if self.fillopacity:
            res['fillOpacity'] = self.fillopacity
        return res
    def as_feature(self) -> dict:
        """
        Returns the geometry as a GeoJson feature. Style is a nested property
        :return:
        """
        return {
            "type": "Feature",
            "geometry": self.geojson,
            "properties": self.site.__jdict__() | self.get_style()
        }

    @classmethod
    def from_shape(cls, feature, **properties):
        """
        Creates a site geometry from an object with __geo_interface__
        eg. shapely.geometry, geojson-object or an entry from geopandas.GeoDataFrame.iterfeatures

        The **properties keywords can be used to set style properties. If the feature has properties,
        then the given properties are overridden by the feature
        """
        if not 'type' in feature:
            raise ValueError('Geometry is not a GeoJSON object, no type')
        elif feature['type'] == 'Feature':
            if not 'geometry' in feature:
                raise ValueError('Feature has no geometry')
            else:
                geometry = cls(geojson=feature['geometry'])
                properties = feature.get('properties', properties)
        else:
            geometry = cls(geojson=feature)

        for k in properties:
            if k.lower() != k:
                properties[k.lower()] = properties[k]

        geometry.strokewidth = properties.get('strokewidth')
        geometry.strokecolor = properties.get('strokecolor')
        geometry.strokeopacity = properties.get('strokeopacity')
        geometry.fillcolor = properties.get('fillcolor')
        geometry.fillopacity = properties.get('fillopacity')

        return geometry


def create_site_from_geometry(
        session,
        shape,
        name: str,
        id: int|None=None,
        height:float|None=None,
        comment:str|None=None,
        icon:str|None=None
):
    """
    Creates a site from a geometry.
    :param session: the sqlalchemy session
    :param shape: An object exposing the __geo_interface__ for geometries. Coordinates **MUST** be in
        geographical coordinates in WGS84
    :param name:
    :param id: The id of the new site, if None a new one is created
    :param height: The height in m a.s.l of the point
    :param comment: A text description of the site
    :param icon: a filename of the site's icon
    :return:
    """
    from shapely import geometry as geo
    from . import base as db
    geometry: geo.Polygon = geo.shape(shape)
    center: geo.Point = geometry.centroid
    id = id or session.query(db.sql.func.max(Site.id)).scalar() + 1
    site = Site(id, lon=center.x, lat=center.y, name=name, height=height, comment=comment, icon=icon)
    site.geometry = SiteGeometry.from_shape(geo.mapping(geometry))

    return site




@total_ordering
class Datasource(Base):
    __tablename__ = 'datasource'
    id = sql.Column(sql.Integer,
                    primary_key=True)
    name = sql.Column(sql.String)
    sourcetype = sql.Column(sql.String)
    comment = sql.Column(sql.String)
    manuallink = sql.Column(sql.String)

    def linkname(self):
        if self.manuallink:
            return self.manuallink.split('/')[-1]
        else:
            return

    def __str__(self):
        return '%s (%s)' % (self.name, self.sourcetype)

    def __eq__(self, other):
        if not hasattr(other, 'name'):
            return NotImplemented
        return self.name == other.name

    def __lt__(self, other):
        if not hasattr(other, 'name'):
            return NotImplemented
        elif other:
            return self.name < other.name
        return False

    def __hash__(self):
        return hash(str(self))

    def __jdict__(self):
        return dict(id=self.id,
                    name=self.name,
                    sourcetype=self.sourcetype,
                    comment=self.comment)


class Installation(Base):
    """Defines the installation of an instrument (Datasource) at a site for a timespan
    """
    __tablename__ = 'installation'
    _instrument = sql.Column('datasource_id', sql.Integer, sql.ForeignKey(
        'datasource.id'), primary_key=True)
    _site = sql.Column('site_id', sql.Integer,
                       sql.ForeignKey('site.id'), primary_key=True)
    id = sql.Column('installation_id', sql.Integer, primary_key=True)
    installdate = sql.Column(sql.DateTime, nullable=True)
    removedate = sql.Column(sql.DateTime, nullable=True)
    comment = sql.Column(sql.String)
    instrument = orm.relationship('Datasource',
                                  backref=orm.backref(
                                      'sites', order_by=installdate.desc, lazy='dynamic'),
                                  primaryjoin="Datasource.id==Installation._instrument")
    site = orm.relationship('Site', backref=orm.backref('instruments', order_by=installdate.desc, lazy='dynamic'),
                            primaryjoin="Site.id==Installation._site",)

    def __init__(self, site, instrument, id, installdate=None, comment=''):
        self.site = site
        self.instrument = instrument
        self.id = id
        self.comment = comment
        self.installdate = installdate

    @property
    def active(self) -> bool:
        today = datetime.today()
        return self.installdate <= today and (self.removedate is None or self.removedate > today)

    def __str__(self):
        fmt = "Installation of %(instrument)s at %(site)s"
        return fmt % dict(instrument=self.instrument, site=self.site)

    def __repr__(self):
        return "<Installation(site=%i,instrument=%i,id=%i)>" % (self.site.id, self.instrument.id, self.id)

    def __jdict__(self):
        return dict(id=self.id,
                    instrument=self.instrument,
                    site=self.site,
                    installdate=self.installdate,
                    removedate=self.removedate,
                    comment=self.comment)


@total_ordering
class Log(Base):
    __tablename__ = 'log'
    id = sql.Column(sql.Integer, primary_key=True)
    time = sql.Column(sql.DateTime)
    # name of logging user
    _user = sql.Column('user', sql.String, sql.ForeignKey('person.username'))
    user = orm.relationship("Person")
    # text of the log
    message = sql.Column(sql.String)
    # affected site
    _site = sql.Column('site', sql.Integer, sql.ForeignKey('site.id'))
    site = orm.relationship("Site", backref=orm.backref(
        'logs', lazy='dynamic', order_by=sql.desc(time)))
    # Type of log
    type = sql.Column(sql.String)

    def __str__(self):
        return f'{self.user}, {self.time}: {self.message} (id:{self.id})'

    def __eq__(self, other):
        if not hasattr(other, 'id'):
            return NotImplemented
        return self.id == other.id

    def __lt__(self, other):
        if not hasattr(other, 'id'):
            return NotImplemented
        return self.id < other.id

    def __jdict__(self):
        return dict(id=self.id,
                    time=self.time,
                    user=self.user,
                    site=self.site,
                    message=self.message)
