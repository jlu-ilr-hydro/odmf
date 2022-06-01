import sqlalchemy as sql
import sqlalchemy.orm as orm
from .base import Base, newid
from datetime import datetime, timedelta
from base64 import b64encode

from io import BytesIO


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

    @staticmethod
    def memoryview_to_b64str(mview):
        if type(mview) is not bytes:
            mview = mview.tobytes()
        return b64encode(mview).decode('ascii')

    def thumbnail64(self):
        return self.memoryview_to_b64str(self.thumbnail)

    def image64(self):
        return self.memoryview_to_b64str(self.image)

    def __PIL_to_stream(self, img, height, format):
        from PIL import Image as pil
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
        self.mime = 'image/' + format
        with pil.open(imagefile) as img:
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
