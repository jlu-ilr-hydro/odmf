# -*- coding:utf-8 -*-
'''
Created on 31.01.2012

@author: philkraf
'''
import sqlalchemy as sql
import sqlalchemy.orm as orm
from base import Base,Session,engine,metadata
from sqlalchemy.schema import ForeignKey
from datetime import datetime,timedelta
def newid(cls,session=None):
    "Creates a new id for all mapped classes with an field called id, which is of integer type"
    if not session:
        session=Session()
    max_id = session.query(sql.func.max(cls.id)).select_from(cls).scalar()
    if not max_id is None:
        return max_id+1
    else:
        return 1

#class InstrumentAtSite(Base):
#    
#    __tablename__ = 'instrument_at_site'
#    instrument=sql.Column('instrument_id',sql.Integer,sql.ForeignKey('instrument.id'),primary_key=True)
#    site=sql.Column('site_id',sql.Integer,sql.ForeignKey('Site.id'),primary_key=True)
#    installdate = sql.Column(sql.DateTime,nullable=True)
#    removedate = sql.Column(sql.DateTime,nullable=True)
#    comment = sql.Column(sql.String)
    
class Site(Base):
    "All locations in the database. The coordiante system is always geographic with WGS84/ETRS"
    __tablename__ = 'site'
    id = sql.Column(sql.Integer,primary_key=True)
    lat = sql.Column(sql.Float)
    lon = sql.Column(sql.Float)
    height = sql.Column(sql.Float)
    name = sql.Column(sql.String)
    comment = sql.Column(sql.String)
    def __str__(self):
        E='E' if self.lon>0 else 'W'
        N='N' if self.lat>0 else 'S'
        return "%s (#%i,%0.3f%s,%0.3f%s)" % (self.name,self.id,abs(self.lon),E,abs(self.lat),N)
    


class Instrument(Base):
    __tablename__= 'instrument'
    id = sql.Column(sql.Integer,
                    #sql.ForeignKey("datasource.id"),
                    primary_key=True)
    name=sql.Column(sql.String)
    comment=sql.Column(sql.String)

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


class Quality(Base):
    __tablename__= 'quality'
    id=sql.Column(sql.Integer,primary_key=True)
    name=sql.Column(sql.String)
    comment=sql.Column(sql.String)
    def __str__(self):
        return self.name

class ValueType(Base):
    __tablename__= 'valuetype'
    id=sql.Column(sql.Integer,primary_key=True)
    name=sql.Column(sql.String)
    unit=sql.Column(sql.String)
    comment=sql.Column(sql.String)
    def __str__(self):
        return "%s [%s]" % (self.name,self.unit)
    def records(self):
        session= Session.object_session(self)
        return Record.query(session).filter(Dataset.valuetype==self)

class DataGroup(Base):
    __tablename__ = 'datagroup'
    id = sql.Column(sql.Integer,primary_key=True)
    name = sql.Column(sql.String,unique=True)
    _valuetype=sql.Column("valuetype",sql.Integer,sql.ForeignKey('valuetype.id'))
    valuetype = orm.relationship("ValueType")
    _site=sql.Column("site",sql.Integer, sql.ForeignKey('site.id'))
    site = orm.relationship("Site")
    comment=sql.Column(sql.String)
    def append(self,dataset):
        if (dataset.valuetype is self.valuetype and
            dataset.site is self.site):
            dataset.group = self
        
    

class Dataset(Base):
    __tablename__= 'dataset'
    id=sql.Column(sql.Integer,primary_key=True)
    name=sql.Column(sql.String, unique=True)
    filename=sql.Column(sql.String, nullable=True)
    start=sql.Column(sql.DateTime, nullable = True)
    end=sql.Column(sql.DateTime, nullable = True)
    #_source = sql.Column("source",sql.Integer, sql.ForeignKey('datasource.id'))
    #source = orm.relationship("DataSource")
    _site=sql.Column("site",sql.Integer, sql.ForeignKey('site.id'))
    site = orm.relationship("Site",backref='datasets')
    _valuetype=sql.Column("valuetype",sql.Integer,sql.ForeignKey('valuetype.id'))
    valuetype = orm.relationship("ValueType",backref='datasets')
    _measured_by=sql.Column("measured_by",sql.String,sql.ForeignKey('person.username'))
    measured_by = orm.relationship("Person",backref='datasets',
                                   primaryjoin="Person.username==Dataset._measured_by")
    _quality=sql.Column("quality",sql.Integer,sql.ForeignKey('quality.id'))
    quality = orm.relationship("Quality")
    _group = sql.Column("group",sql.Integer,sql.ForeignKey('datagroup.id'),nullable=True)
    group = orm.relationship("DataGroup",backref='datasets')
    #_instrument = sql.Column("instrument",sql.Integer,sql.ForeignKey('instrument.id'),nullable=True)
    #instrument = orm.relationship("Instrument",backref='datasets')
    comment=sql.Column(sql.String)
    def __str__(self):
        return str(self.name)
    def maxrecordid(self):
        session = self.session()
        return session.query(sql.func.max(Record.id)).select_from(Record).filter_by(dataset=self.id).scalar()
        
    def addrecord(self,Id=None,value=None,time=None):
        value=float(value)
        session = self.session()
        if Id is None:
            maxid = self.maxrecordid()
            Id=maxid+1
        if time is None:
            time = datetime.now()
        if not (self.start <= time <= self.end):
            raise RuntimeError('RECORD does not fit DATASET: You tried to insert a record for date %s ' +
                               'to dataset %s, which allows only records between %s and %s' 
                               % (time,self,self.start,self.end))
        result = Record(id=Id,time=time,value=value,dataset=self)
        session.add(result)
    def potential_groups(self,session):
        q = session.query(DataGroup)
        q=q.filter_by(valuetype = self.valuetype)
        q=q.filter_by(site = self.site)
        return q
        

            
            
        
            

class Record(Base):
    __tablename__= 'record'
    id=sql.Column(sql.Integer, primary_key=True)
    _dataset=sql.Column("dataset", sql.Integer, sql.ForeignKey('dataset.id'), primary_key=True)
    dataset=orm.relationship("Dataset", backref= orm.backref('records',lazy='dynamic'),lazy='joined')
    time=sql.Column(sql.DateTime)
    value=sql.Column(sql.Float)
    sample=sql.Column(sql.String)
    comment = sql.Column(sql.String)
        
        
    def __str__(self):
        return "%s[%i] = %g %s" % (self.dataset.name,self.id,
                                      self.value,self.dataset.valuetype.unit)
    @classmethod
    def query(cls,session):
        return session.query(cls).select_from(Dataset).join(Dataset.records)

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
    
    def send_mail(self):
        if ((not self.done) and 
            (self.due<datetime.now()) and
            (self.nextreminder<datetime.now())):
            
            # Import smtplib for the actual sending function
            import smtplib
            
            # Import the email modules we'll need
            from email.mime.text import MIMEText
            msgtemplate = u"""
Liebe/r %(you)s,

am %(due)s sollte "%(job)s" erledigt werden und Du bist dafür eingetragen.
Falls etwas unklar ist, bitte nachfragen. Wenn Du die Aufgabe schon erledigt hast
gehe bitte auf http://fb09-pasig.umwelt.uni-giessen.de:8081/job/%(id)s 
und hake den Job ab.

Danke und Schöne Grüße

%(me)s

P.S.: Diese Nachricht wurde automatisch im Namen des Job-Erstellers generiert

Dear %(you)s,

the task "%(job)s" in the Schwingbach area was due at %(due)s, and you have been assigned
for it. If you have any questions regarding this task, co not hesitate to ask. If you have already 
finished the tasked, please mark it as done at http://fb09-pasig.umwelt.uni-giessen.de:8081/job/%(id)s.

Thank you,

with kind regards

%(me)s

This mail has been generated automatically from the Schwingbach database 
            """
            msgdata = dict(id=self.id,you=self.responsible.firstname,due=self.due,job=self.name,descr=self.description,
                                me=self.author.firstname)
            msg = msgtemplate % msgdata
 
            # Create a text/plain message
            msg = MIMEText(msg.encode('utf-8'),'plain','utf-8')
            
            me = self.author.email
            you = self.responsible.email
            msg['Subject'] = 'Automatic reminder for Schwingbach-Job %s' % self.name
            msg['From'] = me
            msg['To'] = you
            print "Send %s reminder to %s from %s" % (self.name,self.responsible,self.author)
            # Send the message via our own SMTP server, but don't include the
            # envelope header.
            s = smtplib.SMTP('mailout.uni-giessen.de')
            s.sendmail(me, [you], msg.as_string())
            s.quit()
                
    
    
if __name__ == '__main__':
    Dataset.metadata.create_all(engine)
