# -*- coding:utf-8 -*-
'''
Created on 31.01.2012

@author: philkraf
'''
import sqlalchemy as sql
import sqlalchemy.orm as orm
from .base import Base, newid
from datetime import datetime, timedelta
from .projection import LLtoUTM, dd_to_dms
from collections import deque
from traceback import format_exc as traceback
from base64 import b64encode


from ..tools.mail import EMail

from functools import total_ordering

from io import BytesIO

def memoryview_to_b64str(mview):
    if type(mview) is not bytes:
        mview = mview.tobytes()
    return b64encode(mview).decode('ascii')


@total_ordering
class Site(Base):
    """All locations in the database. The coordiante system is always geographic with WGS84/ETRS"""
    __tablename__ = 'site'
    id = sql.Column(sql.Integer, primary_key=True)
    lat = sql.Column(sql.Float)
    lon = sql.Column(sql.Float)
    height = sql.Column(sql.Float)
    name = sql.Column(sql.String)
    comment = sql.Column(sql.String)
    icon = sql.Column(sql.String(30))

    def __str__(self):
        return "#%i - %s" % (self.id, self.name)

    def __jdict__(self):
        return dict(id=self.id,
                    lat=self.lat,
                    lon=self.lon,
                    height=self.height,
                    name=self.name,
                    comment=self.comment,
                    icon=self.icon)

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
    def active(self):
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
        return "%s, %s: %s (id:%i)" % (self.user, self.time, self.message, self.id)

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


@total_ordering
class Job(Base):
    __tablename__ = 'job'
    id = sql.Column(sql.Integer, primary_key=True)
    name = sql.Column(sql.String)
    description = sql.Column(sql.String)
    # Date to which the job needs to be done
    due = sql.Column(sql.DateTime)
    # The author of the job
    _author = sql.Column('author', sql.String,
                         sql.ForeignKey('person.username'))
    author = orm.relationship(
        "Person", primaryjoin='Job._author==Person.username')
    # Responsible person to execute job
    _responsible = sql.Column(
        'responsible', sql.String, sql.ForeignKey('person.username'))
    responsible = orm.relationship("Person", primaryjoin='Job._responsible==Person.username',
                                   backref=orm.backref('jobs', lazy='dynamic'))
    # Marks the job as done
    done = sql.Column("done", sql.Boolean, default=False)
    # Number of days to repeat this job, if NULL, negetative or zero, the job is not repeated
    # The new job is generated when this job is done, due date is the number of days after this due date
    repeat = sql.Column(sql.Integer)
    # A http link to help with the execution of the job
    link = sql.Column(sql.String)
    # A job type
    type = sql.Column(sql.String)
    # The date the job was done
    donedate = sql.Column(sql.DateTime)

    def __str__(self):
        return "%s: %s %s" % (self.responsible, self.name, ' (Done)' if self.done else '')

    def __repr__(self):
        return "<Job(id=%s,name=%s,resp=%s,done=%s)>" % (self.id, self.name, self.responsible, self.done)

    def __jdict__(self):
        return dict(id=self.id,
                    name=self.name,
                    description=self.description,
                    due=self.due,
                    donedate=self.donedate,
                    author=self.author,
                    responsible=self.responsible,
                    done=self.done,
                    link=self.link,
                    repeat=self.repeat,
                    label=str(self)
                    )

    def __eq__(self, other):
        if not hasattr(other, 'id'):
            return NotImplemented
        return self.id == other.id

    def __lt__(self, other):
        if not hasattr(other, 'id'):
            return NotImplemented
        return self.id < other.id

    def is_due(self):
        return (not self.done) and (self.due + timedelta(days=1) < datetime.today())

    def parse_description(self, by=None, action='done', time=None):
        """Creates jobs, logs and mails from the description
        The description is parsed by line. When a line "when done:" is encountered
        scan the lines for a trailing "create".
        to create a follow up job:
        create job after 2 days:<job description>
        create log at site 64:<message>
        create mail to philipp:<message>
        """
        session = self.session()
        lines = deque(self.description.lower().split('\n'))
        while lines:
            if lines.popleft().strip() == 'when %s:' % action:
                break
        errors = []
        objects = []
        msg = []
        while lines:
            try:
                line = lines.popleft().strip(',.-;: ')
                if line.startswith('when'):
                    break
                elif line.startswith('create'):
                    if line.count(':'):
                        cmdstr, text = line.split(':', 1)
                        cmd = [w.strip(',.-;:_()#') for w in cmdstr.split()]
                        if cmd[1] == 'log':  # log something
                            try:  # find the site
                                siteid = int(cmd[cmd.index('site') + 1])
                            except:
                                raise RuntimeError(
                                    'Could not find a valid site in command "%s"' % cmdstr)
                            objects.append(Log(id=newid(Log, session),
                                               user=self.responsible,
                                               time=time,
                                               message=text,
                                               _site=siteid,
                                               type=self.type
                                               ))
                        # Create a follow up job
                        elif cmd[1] == 'job':
                            if 'after' in cmd:
                                after = int(cmd[cmd.index('after') + 1])
                            else:
                                after = 0
                            objects.append(Job(id=newid(Job, session),
                                               name=text,
                                               due=time +
                                               timedelta(days=after),
                                               author=self.author,
                                               responsible=self.responsible,
                                               link=self.link,
                                               type=self.type))
                        # Write a mail
                        elif cmd[1] == 'mail':
                            try:
                                if by:
                                    by = Person.get(session, by)
                                else:
                                    by = self.author
                                to = cmd[cmd.index('to') + 1:]
                                to = session.query(Person).filter(
                                    Person.username.in_(to))
                                to = to.all()
                                msgdata = dict(id=self.id, action=action, text=text, name=str(self),
                                               description=self.description, by=str(by))
                                text = '''The job %(name)s is %(action)s by %(by)s
                                        http://fb09-pasig.umwelt.uni-giessen.de:8081/job/%(id)s\n\n'''\
                                    + '''%(text)s\n\n'''\
                                    + '''%(description)s\n''' % msgdata
                                subject = 'Studienlandschaft Schwingbach: job #%(id)s is %(action)s' % msgdata
                                EMail(by.email, list(set([you.email for you in to] + [
                                      self.responsible.email, self.author.email])), subject, text).send()
                            except:
                                raise RuntimeError(
                                    '"%s" is not a valid mail, problem: %s' % (line, traceback()))
                    else:
                        raise RuntimeError(
                            '"%s" is not an action, missing ":"' % line)
            except Exception as e:
                errors.append(e.message)
        return objects, errors

    def make_done(self, by, time=None):
        "Marks the job as done and performs effects of the job"
        self.done = True
        if not time:
            time = datetime.now()
        self.donedate = time
        msg = []
        session = self.session()
        if self.repeat:
            newjob = Job(id=newid(Job, session),
                         name=self.name,
                         description=self.description,
                         due=self.due + timedelta(days=self.repeat),
                         author=self.author,
                         responsible=self.responsible,
                         repeat=self.repeat,
                         link=self.link,
                         type=self.type)
            session.add(newjob)
            msg.append('Added new job %s' % newjob)
        if self.description:
            objects, errors = self.parse_description('done', by, time)
            session.add_all(objects)
            session.commit()
            msg.extend(str(o) for o in objects)
            if errors:
                msg.append('ERRORS:')
                msg.extend(errors)
        return '\n'.join(msg)

    @property
    def color(self):
        if self.done:
            return '#FFF'
        dt = (self.due - datetime.now()).days
        if dt < 0:
            return '#F00'
        elif dt == 0:
            return '#F80'
        elif dt < 2:
            return '#8F4'
        else:
            return '#8F8'


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
        "Person", primaryjoin='Project._person_responsible==Person.username')
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
