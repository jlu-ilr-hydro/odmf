import sqlalchemy as sql
import sqlalchemy.orm as orm
from datetime import datetime, timedelta
from functools import total_ordering
from sqlalchemy_json import NestedMutableJson
from typing import Optional, List

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
        msg = (self.log or {}).get('message') or self.name
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


    def as_message(self, by=None, time=None) -> Message:
        """Creates a message from this job"""

        by = by or self.author
        if not time:
            time = datetime.now()

        subject = f'ODMF-{conf.root_url}: {self.name}'
        topics = (self.mailer or {}).get('topics')
        if self.done:
            content = (
                f'Job {self.name} is finished at {self.donedate} by {by}\n'
            )
        else:
            content = (
                f'{self.name} is due at {self.due}\n\n'
                f'{self.description}\n'
            )
        topics = self.session().scalars(sql.select(Topic).where(Topic.id.in_(topics or []))).all()

        return Message(subject=subject, content=content, topics=topics, date=time, source=f'job:{self.id}')

    def as_overdue_message(self) -> (Message, list[Person]):
        reminder = self.mailer.get('reminder') or []
        msg = Message(
            subject=f'ODMF-{conf.root_url}: Reminder - {self.name}',
            content=f'{self.name} by {self.author} is due since {self.due:%d.%m.%Y} but not done yet. If nothing happens you will receive this email every day. '
                    f'To stop the reminder emails, you need to log into the ODMF database and change the job properties:\n\n'
                    f'- if you have finished the job, mark it as done\n'
                    f'- if it is delayed, change the due date\n'
                    f'- if you delegate the job, change the responsible person (they will get the emails)\n'
                    f'- if the job is obsolete, remove it\n'
                    f'- if the job is still valid, but you do not need any reminders, change the reminder settings\n'
                    f'- if you need any help, contact {self.author.email} or one of the ODMF admins (see login page)\n',
            source=f'job:{self.id}',
            topics=self.mailer.get('topics') if 'subscribers' in reminder else []
        )
        cc = []
        if 'author' in reminder:
            cc.append(self.author)
        if 'responsible' in reminder:
            cc.append(self.responsible)

        return msg, cc

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
            receivers = mail.send(self.author, self.responsible)
            msg.append(f'send {len(receivers)} mails')
        return '\n'.join(msg)

    def message_dates(self) -> List[datetime]:
        """
        Returns the dates in the past, where messages should have been sent out
        """
        when = list(self.mailer.get('when') or []) if self.mailer else []
        # Get all due dates of the job messages (only for int entries)
        dates = [self.due - timedelta(days=days) for days in when if type(days) is int]
        # Filter only the dates that are in the past
        return [d for d in dates if d < datetime.now()]

    def end(self):
        return self.due + timedelta(days=self.duration or 0)

