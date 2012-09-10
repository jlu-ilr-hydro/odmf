# -*- coding:utf-8 -*-
'''
Created on 31.01.2012

@author: philkraf
'''
import sqlalchemy as sql
import sqlalchemy.orm as orm
from base import Base,Session
from sqlalchemy.schema import ForeignKey
from datetime import datetime
from cherrypy.lib.reprconf import as_dict
from projection import LLtoUTM, dd_to_dms
def newid(cls,session=None):
    "Creates a new id for all mapped classes with an field called id, which is of integer type"
    if not session:
        session=Session()
    max_id = session.query(sql.func.max(cls.id)).select_from(cls).scalar()
    if not max_id is None:
        return max_id+1
    else:
        return 1
    
class Site(Base):
    "All locations in the database. The coordiante system is always geographic with WGS84/ETRS"
    __tablename__ = 'site'
    id = sql.Column(sql.Integer,primary_key=True)
    lat = sql.Column(sql.Float)
    lon = sql.Column(sql.Float)
    height = sql.Column(sql.Float)
    name = sql.Column(sql.String)
    comment = sql.Column(sql.String)
    icon = sql.Column(sql.String(30))
    def __str__(self):
        E='E' if self.lon>0 else 'W'
        N='N' if self.lat>0 else 'S'
        coord ='%0.6f%s,%0.6f%s' % (abs(self.lon),E,abs(self.lat),N)
        if self.height:
            coord+=',%0.3f m a.s.l' % self.height
        return "#%i (%s) - %s" % (self.id,coord,self.name)
    def __jdict__(self):
        return dict(id=self.id,
                lat=self.lat,
                lon=self.lon,
                height=self.height,
                name=self.name,
                comment=self.comment,
                icon=self.icon)
    def __cmp__(self,other):
        return cmp(self.id,other.id)
    
    def as_UTM(self):
        """Returns a tuple (x,y) as UTM/WGS84 of the site position
        If withzone is True it returns the name of the UTM zone as a third argument
        """
        return LLtoUTM(23, self.lat, self.lon)
    
    def as_coordinatetext(self):
        lat = dd_to_dms(self.lat)
        lon = dd_to_dms(self.lon)
        return (u"%i° %i' %0.2f''N - " % lat) + (u"%i° %i' %0.2f''E" % lon)          


class Datasource(Base):
    __tablename__= 'datasource'
    id = sql.Column(sql.Integer,
                    primary_key=True)
    name=sql.Column(sql.String)
    sourcetype=sql.Column(sql.String)
    comment=sql.Column(sql.String)
    def __str__(self):
        return '%s (%s)' % (self.name,self.sourcetype)
    def __jdict__(self):
        return dict(id=self.id,
                 name=self.name,
                 sourcetype=self.sourcetype,
                 comment=self.comment)

class Installation(Base):
    """Defines the installation of an instrument (Datasource) at a site for a timespan
    """
    __tablename__ = 'installation'
    _instrument=sql.Column('datasource_id',sql.Integer,sql.ForeignKey('datasource.id'),primary_key=True)
    _site=sql.Column('site_id',sql.Integer,sql.ForeignKey('site.id'),primary_key=True)
    id=sql.Column('installation_id',sql.Integer,primary_key=True)
    installdate = sql.Column(sql.DateTime,nullable=True)
    removedate = sql.Column(sql.DateTime,nullable=True)
    comment = sql.Column(sql.String)
    instrument = orm.relationship('Datasource',
                                  backref=orm.backref('sites',order_by=installdate.desc,lazy='dynamic'),
                                  primaryjoin="Datasource.id==Installation._instrument")
    site=orm.relationship('Site',backref=orm.backref('instruments',order_by=installdate.desc,lazy='dynamic'),
                          primaryjoin="Site.id==Installation._site",)
    def __init__(self,site,instrument,id,installdate=None,comment=''):
        self.site=site
        self.instrument=instrument
        self.id=id
        self.comment=comment
        self.installdate=installdate
    @property
    def active(self):
        today = datetime.today()
        return self.installdate<=today and (self.removedate is None or self.removedate>today)
    def __str__(self):
        fmt = "Installation of %(instrument)s at %(site)s"
        return fmt % dict(instrument=self.instrument,site=self.site) 
    def __repr__(self):
        return "<Installation(site=%i,instrument=%i,id=%i)>" % (self.site.id,self.instrument.id,self.id)
    def __jdict__(self):
        return  dict(id=self.id,
                     instrument = self.instrument,
                     site = self.site,
                     installdate = self.installdate, 
                     removedate = self.removedate,
                     comment = self.comment)
    

class Person(Base):
    __tablename__= 'person'
    username=sql.Column(sql.String,primary_key=True)
    email=sql.Column(sql.String)
    firstname=sql.Column(sql.String)
    surname=sql.Column(sql.String)
    _supervisor=sql.Column('supervisor',sql.String, sql.ForeignKey('person.username'))
    supervisor=orm.relationship('Person',remote_side=[username])
    telephone=sql.Column(sql.String)
    comment=sql.Column(sql.String)
    can_supervise=sql.Column(sql.Boolean, default=False)
    mobile=sql.Column(sql.String)
    car_available=sql.Column(sql.Integer,default=0)
    def __str__(self):
        return "%s %s" % (self.firstname,self.surname)
    def __jdict__(self):
        return dict(username=self.username,
                    email=self.email,
                    firstname=self.firstname,
                    surname=self.surname,
                    supervisor=str(self.supervisor),
                    telephone = self.telephone,
                    mobile=self.mobile,
                    comment=self.comment,
                    car_available = self.car_available)
    def __cmp__(self,other):
        return cmp(self.surname,other.surname)



class Image(Base):
    __tablename__='image'
    id=sql.Column(sql.Integer,primary_key=True)
    name=sql.Column(sql.String)
    time=sql.Column(sql.DateTime)
    mime=sql.Column(sql.String)
    _site=sql.Column("site",sql.Integer, sql.ForeignKey('site.id'))
    site=orm.relationship("Site", backref='images')
    _by=sql.Column("by",sql.ForeignKey('person.username'))
    by=orm.relationship("Person",backref='images')
    image=sql.Column(sql.LargeBinary)
    thumbnail = sql.Column(sql.LargeBinary)

class Log(Base):
    __tablename__='log'
    id=sql.Column(sql.Integer,primary_key=True)
    time=sql.Column(sql.DateTime)
    _user=sql.Column('user',sql.String,sql.ForeignKey('person.username'))
    user = orm.relationship("Person")
    message = sql.Column(sql.String)
    _site = sql.Column('site',sql.Integer,sql.ForeignKey('site.id'))
    site = orm.relationship("Site", backref=orm.backref('logs',lazy='dynamic'))
    def __str__(self):
        return "%s, %s: %s" % (self.user,self.time,self.message)
    def __cmp__(self,other):
        return cmp(self.id,other.id)

    def __jdict__(self):
        return dict(id=self.id,
                    time=self.time,
                    user= self.user,
                    site=self.site,
                    message=self.message)

class Job(Base):
    __tablename__='job'
    id=sql.Column(sql.Integer,primary_key=True)
    name=sql.Column(sql.String)
    description = sql.Column(sql.String)
    due=sql.Column(sql.DateTime)
    _author=sql.Column('author',sql.String,sql.ForeignKey('person.username'))
    author = orm.relationship("Person",primaryjoin='Job._author==Person.username')
    _responsible =sql.Column('responsible',sql.String,sql.ForeignKey('person.username'))
    responsible = orm.relationship("Person",primaryjoin='Job._responsible==Person.username',
                                    backref=orm.backref('jobs',lazy='dynamic'))
    done = sql.Column(sql.Boolean,default=False)
    nextreminder = sql.Column(sql.DateTime)
    def __str__(self):
        return "%s: %s %s" % (self.responsible,self.name,' (Done)' if self.done else '')
    def __repr__(self):
        return "<Job(id=%s,name=%s,resp=%s,done=%s)>" % (self.id,self.name,self.responsible,self.done)
    def __jdict__(self):
        return dict(id=self.id,
                    name=self.name,
                    description=self.description,
                    due=self.due,
                    author = self.author,
                    responsible = self.responsible,
                    done=self.done,
                    nextreminder = self.nextreminder)
    def __cmp__(self,other):
        return cmp(self.id,other.id)

    @property
    def color(self):
        if self.done:
            return '#FFF'
        dt = (self.due-datetime.now()).days
        if dt<0:
            return '#F00'
        elif dt==0:
            return '#F80'
        elif dt<2:
            return '#8F4'
        else:
            return '#8F8'
    
    
    
