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
    messages: orm.Mapped[List['Message']] = orm.relationship(secondary=publishs_table)

    def __str__(self):
        return self.name


class Message(Base):
    """
    A message send for a topic. Database objects like jobs and datasets can publish messages
    and users can create messages on the website.
    """
    __tablename__ = 'message'
    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    date: orm.Mapped[datetime]
    topics: orm.Mapped[List['Topic']] = orm.relationship(secondary=publishs_table)
    subject: orm.Mapped[str]
    content: orm.Mapped[str]
    data: orm.Mapped[NestedMutableJson] = orm.mapped_column(NestedMutableJson)

    def send(self):
        """
        Sends the message to all email addresses  subscribed to the topics. Resolves cross-posting
        """
        receivers = set(chain(*[t.subscribers for t in self.topics]))

        with Mailer(conf.mailer_config) as mailer:
            mailer.send(
                subject=self.subject,
                body=self.content,
                receivers=[r.email for r in receivers]
            )




