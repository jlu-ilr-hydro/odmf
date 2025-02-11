import sqlalchemy as sql
import sqlalchemy.orm as orm
from datetime import datetime, timedelta
from traceback import format_exc as traceback
from functools import total_ordering
from itertools import chain

from sqlalchemy import ForeignKey
from sqlalchemy_json import NestedMutableJson

from typing import Optional, List

from ..config import conf
from ..tools.mail import Mailer
from .base import Base, newid
from .person import Person

from ..tools.migrate_db import new_column

from logging import getLogger
logger = getLogger(__name__)


subscription_table = sql.Table(
    'subscribes',
    Base.metadata,
    sql.Column('topic', ForeignKey('topic.id'), primary_key=True),
    sql.Column('subscriber', ForeignKey('person.username'), primary_key=True)
)

publishs_table = sql.Table(
    'publishs', Base.metadata,
    sql.Column('topic', ForeignKey('topic.id'), primary_key=True),
    sql.Column('publishs', ForeignKey('message.id'), primary_key=True)
)

@total_ordering
class Topic(Base):
    """
    Describes a conversation topic. Users can subscribe to a topic and receive all messages send for topic.

    Inspired by MQTT
    """
    __tablename__ = 'topic'

    id: orm.Mapped[str] = orm.mapped_column(primary_key=True)
    name: orm.Mapped[str]
    description: orm.Mapped[Optional[str]]
    _owner: orm.Mapped[str] = orm.mapped_column(sql.ForeignKey('person.username'))
    owner: orm.Mapped["Person"] = orm.relationship()
    subscribers: orm.Mapped[List[Person]] = orm.relationship(secondary=subscription_table, back_populates='topics')
    # messages: orm.Mapped[List['Message']] = orm.relationship(secondary=publishs_table, back_populates='topics', order_by='desc(Message.date)')

    def __repr__(self):
        return f"topic:{self.id}"

    def __jdict__(self):
        return dict(
            id=self.id,
            name=self.name,
            description=self.description,
            owner=self._owner,
        )


def subscribers(topics: List[Topic])-> List[Person]:
    receivers = set(chain(*[t.subscribers for t in topics]))
    return sorted([r for r in receivers if r.active])


class Message(Base):
    """
    A message send for a topic. Database objects like jobs and datasets can publish messages
    and users can create messages on the website.
    """
    __tablename__ = 'message'
    id: orm.Mapped[int] = orm.mapped_column(primary_key=True, autoincrement=True)
    date: orm.Mapped[Optional[datetime]]
    topics: orm.Mapped[List['Topic']] = orm.relationship(secondary=publishs_table)
    subject: orm.Mapped[str]
    content: orm.Mapped[str]
    source: orm.Mapped[Optional[str]]

    def footer(self):
        """Returns a footer for the message."""
        url = conf.url()
        topics = ', '.join(f'topic:{t.id}' for t in self.topics)
        text = ('\n---\n'
                f'You receive this mail, because you are a user of the ODMF-Database {url}.\n'
                f'You have subscribed to any of these topics: {topics}\n'
                f'To change your subscriptions, go to your user page of the ODMF-Database {url}.\n'
        )
        return text

    def to(self):
        """Returns a list of all receivers of the messages"""

        return subscribers(self.topics)

    def send(self, with_footer=True):
        """
        Sends the message to all email addresses subscribed to the topics. Resolves cross-posting.
        If date is not set, send will set the date to now
        """
        content = self.content
        if with_footer:
            content += '\n' + self.footer()
        self.date = self.date or datetime.now()
        receivers = self.to()
        with Mailer(conf.mailer_config) as mailer:
            mailer.send(
                subject=self.subject,
                body=content,
                receivers=[r.email for r in receivers]
            )
        return receivers

    def __str__(self):
        return '\n'.join([
            '- **To:** ' + ', '.join(f'user:{r.username}' for r in self.to()),
            '- **Subject**: ' + self.subject,
            f'- **Source**: {self.source}',
            '\n\n**Content**:\n' + self.content + self.footer(),
            ])

    def __jdict__(self):
        return dict(
            id=self.id,
            date=self.date,
            subject=self.subject,
            content=self.content,
            source=self.source,
            topics=[t.id for t in self.topics],
        )

    @classmethod
    def from_dict(cls, session: orm.Session, **d):
        topics = d.pop('topics', [])
        stmt = sql.select(Topic).where(Topic.id.in_(topics))
        topics = session.scalars(stmt).all()
        d['topics'] = topics

        return cls(**d)








