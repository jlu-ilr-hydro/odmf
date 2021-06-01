# -*- coding:utf-8 -*-
'''
Created on 31.01.2012

@author: philkraf
'''
import sqlalchemy as sql
import sqlalchemy.orm as orm
from .base import Base
from datetime import datetime
from .projection import LLtoUTM, dd_to_dms, UTMtoLL
from base64 import b64encode
from ..config import conf

from functools import total_ordering

from io import BytesIO


def memoryview_to_b64str(mview):
    if type(mview) is not bytes:
        mview = mview.tobytes()
    return b64encode(mview).decode('ascii')




@total_ordering
class Person(Base):
    __tablename__ = 'person'
    username = sql.Column(sql.String, primary_key=True)
    email = sql.Column(sql.String)
    firstname = sql.Column(sql.String)
    surname = sql.Column(sql.String)
    _supervisor = sql.Column('supervisor', sql.String,
                             sql.ForeignKey('person.username'))
    supervisor = orm.relationship('Person', remote_side=[username])
    telephone = sql.Column(sql.String)
    comment = sql.Column(sql.String)
    can_supervise = sql.Column(sql.Boolean, default=False)
    mobile = sql.Column(sql.String)
    car_available = sql.Column(sql.Integer, default=0)
    password = sql.Column(sql.VARCHAR)
    access_level = sql.Column(sql.INTEGER)
    active = sql.Column(sql.Boolean, default=True, nullable=False)

    def __str__(self):
        return "%s %s" % (self.firstname, self.surname)

    def __jdict__(self):
        return dict(username=self.username,
                    email=self.email,
                    firstname=self.firstname,
                    surname=self.surname,
                    supervisor=str(self.supervisor),
                    telephone=self.telephone,
                    mobile=self.mobile,
                    comment=self.comment,
                    car_available=self.car_available,
                    label="%s %s" % (self.firstname, self.surname),
                    )

    def __eq__(self, other):
        if not hasattr(other, 'surname'):
            if not hasattr(other, 'firstname'):
                return NotImplemented
            return self.surname == str(other)
        return self.surname == other.surname

        #
        # Old cmp code, just for comparision purpose (ICO bug)
        #
        # if hasattr(other,'surname'):
        #    return self.surname == other.surname
        # elif other:
        #    return self.surname == str(other)
        # else:
        #    return self.surname == other

    def __lt__(self, other):
        if not hasattr(other, 'surname'):
            if not hasattr(other, 'firstname'):
                return NotImplemented
            return self.surname < str(other)
        return self.surname < other.surname

    def __hash__(self):
        return hash(str(self))


class Image(Base):
    __tablename__ = 'image'
    id = sql.Column(sql.Integer, primary_key=True)
    name = sql.Column(sql.String)
    time = sql.Column(sql.DateTime)
    mime = sql.Column(sql.String)
    _site = sql.Column("site", sql.Integer, sql.ForeignKey('site.id'))
    site = orm.relationship("Site", backref=orm.backref(
        'images', lazy='dynamic', order_by=sql.desc(time)))
    _by = sql.Column("by", sql.ForeignKey('person.username'))
    by = orm.relationship("Person", backref=orm.backref(
        'images', lazy='dynamic', order_by=sql.desc(time)))
    image = sql.Column(sql.LargeBinary)
    thumbnail = sql.Column(sql.LargeBinary)
    imageheight = 1024
    thumbnailheight = 72

    def thumbnail64(self):
        return memoryview_to_b64str(self.thumbnail)

    def image64(self):
        return memoryview_to_b64str(self.image)

    def __PIL_to_stream(self, img, height, format):
        from PIL import Image as pil
        print('piltostream %s' % self.id)
        lores = img.resize(
            (height * img.size[0] // img.size[1], height), pil.ANTIALIAS)
        buffer = BytesIO()
        lores.save(buffer, format)
        return buffer

    def __str__(self):
        return "Image at site #%i by %s from %s" % (self.site.id, self.by, self.time)

    def __repr__(self):
        return "<db.Image(site=%i,by=%s,time=%s)>" % (self.site.id, self.by, self.time)

    def __init__(self, site=None, time=None, by=None, format='jpeg', imagefile=""):
        from PIL import Image as pil
        img = pil.open(imagefile)
        self.mime = 'image/' + format
        self.image = self.__PIL_to_stream(
            img, self.imageheight, format).getvalue()
        self.thumbnail = self.__PIL_to_stream(
            img, self.thumbnailheight, format).getvalue()
        self.by = by
        if not time:
            try:
                # Get original data
                info = img._getexif()
                # Get DateTimeOriginal from exifdata
                time = datetime.strptime(info[0x9003], '%Y:%m:%d %H:%M:%S')
            except:
                time = None
        self.time = time
        self.site = site






@total_ordering
class Project(Base):
    """
    SqlAlchemy Object for holding project information
    """
    __tablename__ = 'project'

    id = sql.Column(sql.Integer, primary_key=True)
    _person_responsible = sql.Column('person_responsible', sql.String,
                                     sql.ForeignKey('person.username'))
    person_responsible = sql.orm.relationship(
        "Person",
        primaryjoin='Project._person_responsible==Person.username',
        backref=orm.backref('leads_projects', lazy='dynamic')
    )
    name = sql.Column(sql.String)
    comment = sql.Column(sql.String)

    def __str__(self):
        return " %s %s: %s %s" % (self.id, self.name, self.person_responsible,
                                  self.comment)

    def __repr__(self):
        return "<Project(id=%s, name=%s, person=%s)>" % \
               (self.id, self.name, self.person_responsible)

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
                    name=self.name,
                    person_responsible=self.person_responsible,
                    comment=self.comment)

# Creating all tables those inherit Base
# print "Create Tables"
# Base.metadata.create_all(engine)
