import sqlalchemy as sql
import sqlalchemy.orm as orm
from datetime import datetime, timedelta
from collections import deque
from traceback import format_exc as traceback
from functools import total_ordering
from sqlalchemy_json import NestedMutableJson

# from ..tools.mail import EMail
from .base import Base, newid
from .site import Log, Site
from .person import Person
from ..tools.migrate_db import new_column

from logging import getLogger
logger = getLogger(__name__)

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
    # Job duration in days after due
    duration: orm.Mapped[int] = new_column(sql.Column(sql.Integer))
    # Number of days to repeat this job, if NULL, negetative or zero, the job is not repeated
    # The new job is generated when this job is done, due date is the number of days after this due date
    repeat = sql.Column(sql.Integer)
    # A http link to help with the execution of the job
    link = sql.Column(sql.String)
    # A job type
    type = sql.Column(sql.String)
    # The date the job was done
    donedate = sql.Column(sql.DateTime)
    # Contains data to create logs on done
    log: orm.Mapped[NestedMutableJson] = sql.Column(NestedMutableJson)
    def __str__(self):
        return "%s: %s %s" % (self.responsible, self.name, ' (Done)' if self.done else '')

    def __repr__(self):
        return "<Job(id=%s,name=%s,resp=%s,done=%s)>" % (self.id, self.name, self.responsible, self.done)

    def __jdict__(self):
        return dict(id=self.id,
                    name=self.name,
                    type=self.type,
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
        return self.due is not None and (not self.done) and (self.due + timedelta(days=1) < datetime.today())

    def log_to_sites(self, by=None, time=None):
        session = self.session()
        logsites = (self.log or {}).get('sites', [])
        msg = (self.log or {}).get('messsage', '')
        logcount = 0
        for siteid in logsites:
            site = Site.get(session, siteid)
            if site:
                session.add(
                    Log(
                        id=newid(Log, session),
                        _user=by or self.responsible.username,
                        time=time or datetime.now(),
                        message=msg,
                        site=site,
                        type=self.type
                    )
                )
                logcount += 1
        return logcount

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
                            objects.append(
                                Job(id=newid(Job, session),
                                    name=text,
                                    due=time + timedelta(days=after),
                                    author=self.author,
                                    responsible=self.responsible,
                                    link=self.link,
                                    type=self.type)
                            )
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
                                #EMail(by.email, list(set([you.email for you in to] + [
                                #      self.responsible.email, self.author.email])), subject, text).send()
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
        """Marks the job as done and performs effects of the job"""
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
                         duration=self.duration,
                         responsible=self.responsible,
                         repeat=self.repeat,
                         link=self.link,
                         type=self.type,
                         data=self.data)
            session.add(newjob)
            msg.append('Added new job %s' % newjob)
        if self.log:
            log_count = self.log_to_sites(by, time)
            if log_count:
                msg.append(f'Added {log_count} log messages to sites.')
        return '\n'.join(msg)

    def end(self):
        return self.due + timedelta(days=self.duration or 0)

