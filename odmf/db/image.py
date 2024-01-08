import sqlalchemy as sql
import sqlalchemy.orm as orm
from datetime import datetime
from base64 import b64encode
from io import BytesIO
from PIL import Image as pil
from .base import Base
from ..tools.migrate_db import new_column
from logging import getLogger
logger = getLogger(__name__)


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
    comment = new_column(sql.Column(sql.String))
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
        lores = img.resize(
            (height * img.size[0] // img.size[1], height), pil.LANCZOS)
        buffer = BytesIO()
        lores.save(buffer, format)
        return buffer

    def __str__(self):
        return "Image at site #%i by %s from %s" % (self.site.id, self.by, self.time)

    def __repr__(self):
        return "<db.Image(site=%i,by=%s,time=%s)>" % (self.site.id, self.by, self.time)

    def __init__(self, site=None, time=None, by=None, format='jpeg', imagefile="", comment=None):
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
        self.comment = comment

    def rotate(self, degrees=90):
        """
        Rotates the image in 90deg parts using PIL.Image.transpose method

        Raises if degrees is not dividable by 90
        """
        if degrees not in (90, 180, 270, -90):
            raise ValueError('Can only rotate image by 90, 180 or 270 degrees')
        # Get transpose method, 2 => ROTATE_90, 3 => ROTATE_180, 4 => ROTATE_270
        # See here: https://pillow.readthedocs.io/en/stable/reference/Image.html#transpose-methods
        if degrees < 0:
            degrees += 360
        rotation = degrees // 90 + 1
        img = pil.open(BytesIO(self.image))
        img_transposed = img.transpose(method=rotation)
        buffer = BytesIO()
        format = self.mime.replace('image/', '')
        img_transposed.save(buffer, format)
        self.image = self.__PIL_to_stream(img_transposed, img_transposed.height, format).getvalue()
        self.thumbnail = self.__PIL_to_stream(img_transposed, self.thumbnailheight, format).getvalue()

