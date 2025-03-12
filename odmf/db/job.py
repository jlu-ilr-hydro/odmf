import sqlalchemy as sql
import sqlalchemy.orm as orm
from datetime import datetime, timedelta
from collections import deque
from traceback import format_exc as traceback
from functools import total_ordering
from sqlalchemy_json import NestedMutableJson
from typing import Optional

from ..config import conf
from .base import Base, newid
from .site import Log, Site
from .person import Person
from .message import Message, Topic
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
    mailer: orm.Mapped[NestedMutableJson] = sql.Column(NestedMutableJson)
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
        msg = (self.log or {}).get('message') or self.description
        logcount = 0
        if logsites:
            sites = session.scalars(sql.select(Site).where(Site.id.in_(logsites)))
            for site in sites:
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
            return [site.id for site in sites]
        else:
            return []

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
                                        http://fb09-pasig.umwelt.uni-giessen.de:8081/job/%(id)s\n\n''' \
                                       + '''%(text)s\n\n''' \
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

    def as_message(self, by=None, time=None) -> Message:
        """Creates a message from this job"""

        by = by or self.author
        if not time:
            time = datetime.now()

        subject = f'ODMF-{conf.root_url}: {self.name}'
        topics = (self.mailer or {}).get('topics', [])
        if self.done:
            content = (
                f'Job {self.name} is finished at {self.donedate} by {by}\n'
            )
        else:
            content = (
                f'{self.name} is due at {self.due}\n\n'
                f'{self.description}\n'
            )
        topics = self.session().scalars(sql.select(Topic).where(Topic.id.in_(topics))).all()

        return Message(subject=subject, content=content, topics=topics, date=time, source=f'job:{self.id}')

    def make_done(self, by, time=None):
        """Marks the job as done and performs effects of the job"""
        self.done = True
        if not time:
            time = datetime.now()
        self.donedate = time
        msg = []
        session = self.session()
        if self.repeat:
            newjob = Job(
                id=newid(Job, session),
                name=self.name,
                description=self.description,
                due=self.due + timedelta(days=self.repeat),
                author=self.author,
                duration=self.duration,
                responsible=self.responsible,
                repeat=self.repeat,
                link=self.link,
                type=self.type,
                log=self.log,
                mailer=self.mailer
            )
            session.add(newjob)
            msg.append('Added new job %s' % newjob)
        if self.log:
            logsites = self.log_to_sites(by, time)
            if logsites:
                msg.append(f'Added {len(logsites)} log messages to sites: ' + ', '.join(f'site:{s}' for s in logsites))
        if self.mailer and self.mailer.get('when') and 'done' in self.mailer.get('when'):
            mail = self.as_message(by, time)
            self.session().add(mail)
            receivers = mail.send()
            msg.append(f'send {len(receivers)} mails')
        return '\n'.join(msg)

    def create_message_by_time(self) -> Optional[Message]:
        """
        Creates a message for this job if needed by the when flag of the mailer

        Will be called by a periodic process
        """
        if self.done:
            return None
        session = self.session()
        now = datetime.now()
        # Get timedeltas for each 'when' entry, that is a number
        when_dates = [timedelta(days=when) for when in (self.mailer or {}).get('when', []) if type(when) is int]
        # Remove entries, that are not yet due
        when_dates = [when for when in when_dates if now + when >= self.due]

        if not when_dates:
            return None

        # Remove when-dates for each existing message of this job
        messages = session.scalars(sql.select(Message).where(Message.source == f'job:{self.id}'))
        for msg in messages:
            when_dates = [when for when in when_dates if not msg.date + when >= self.due]

        if when_dates:
            return self.as_message()
        else:
            return None





    def end(self):
        return self.due + timedelta(days=self.duration or 0)

