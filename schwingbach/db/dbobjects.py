# -*- coding:utf-8 -*-
'''
Created on 31.01.2012

@author: philkraf
'''
import sqlalchemy as sql
import sqlalchemy.orm as orm
from base import Base,Session, newid
from sqlalchemy.schema import ForeignKey
from datetime import datetime
from cherrypy.lib.reprconf import as_dict
from projection import LLtoUTM, dd_to_dms
    
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
    _defaultdataset = sql.Column('defaultdataset',sql.Integer, sql.ForeignKey('dataset.id'))
    defaultdataset = orm.relationship('Dataset',primaryjoin='Dataset.id==Site._defaultdataset')
    def __str__(self):
        return "#%i - %s" % (self.id,self.name)
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
    manuallink=sql.Column(sql.String)
    
    def linkname(self):
        if self.manuallink:
            return self.manuallink.split('/')[-1]
        else:
            return
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
    site=orm.relationship("Site", backref=orm.backref('images',lazy='dynamic',order_by=sql.desc(time)))
    _by=sql.Column("by",sql.ForeignKey('person.username'))
    by=orm.relationship("Person",backref=orm.backref('images',lazy='dynamic',order_by=sql.desc(time)))
    image=sql.Column(sql.LargeBinary)
    thumbnail = sql.Column(sql.LargeBinary)
    imageheight = 1024
    thumbnailheight = 72
    def thumbnail64(self):
        from base64 import b64encode
        return b64encode(self.thumbnail)
    def image64(self):
        from base64 import b64encode
        return b64encode(self.image)
    def __PIL_to_stream(self,img,height,format):
        from PIL import Image as pil
        from cStringIO import StringIO
        lores = img.resize((height * img.size[0] // img.size[1], height), pil.ANTIALIAS)
        buffer = StringIO()
        lores.save(buffer,format)
        return buffer
    def __str__(self):
        return "Image at site #%i by %s from %s" % (self.site.id,self.by,self.time)
    def __repr__(self):
        return "<db.Image(site=%i,by=%s,time=%s)>" % (self.site.id,self.by,self.time) 
    def __init__(self,site=None,time=None,by=None,format='jpeg',imagefile=file):
        from PIL import Image as pil
        img = pil.open(imagefile)
        self.mime = 'image/' + format
        self.image= self.__PIL_to_stream(img, self.imageheight, format).getvalue()
        self.thumbnail = self.__PIL_to_stream(img, self.thumbnailheight, format).getvalue()
        self.by=by
        self.time=time
        self.site=site
        
        

class Log(Base):
    __tablename__='log'
    id=sql.Column(sql.Integer,primary_key=True)
    time=sql.Column(sql.DateTime)
    _user=sql.Column('user',sql.String,sql.ForeignKey('person.username'))
    user = orm.relationship("Person")
    message = sql.Column(sql.String)
    _site = sql.Column('site',sql.Integer,sql.ForeignKey('site.id'))
    site = orm.relationship("Site", backref=orm.backref('logs',lazy='dynamic',order_by=sql.desc(time)))
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
    
class Maintenance(Base):
    __tablename__='maintenance'
    id=sql.Column(sql.String,primary_key=True)
    description=sql.Column(sql.String)
    jobtext = sql.Column(sql.String)
    _supervisor=sql.Column('supervisor',sql.String,sql.ForeignKey('person.username'))
    supervisor=  orm.relationship("Person",primaryjoin='Maintenance._supervisor==Person.username')
    _responsible =sql.Column('responsible',sql.String,sql.ForeignKey('person.username'))
    responsible = orm.relationship("Person",primaryjoin='Maintenance._responsible==Person.username')
    repeat = sql.Column(sql.Integer)
    _followed_by = sql.Column('followed_by',sql.String, sql.ForeignKey('maintenance.id'))
    followed_by = orm.relationship('Maintenance',remote_side=[id])

                                   
    