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
from ..tools.mail.mail import Mailer
from .base import Base, newid
from .person import Person


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


def subscribers(topics: List[Topic], cc: Optional[List[Person]] = None) -> List[Person]:
    receivers = set(chain(*[t.subscribers for t in topics]))
    if cc:
        receivers.update(cc)
    return sorted([r for r in receivers if r.active])

def link2href(s: str) -> str:
    """Return url from an ODMF-Markdown link, eg. `site:1` returns http://localhost/root_url/site/1"""
    from ..webpage.markdown import MarkDown
    import re
    md = MarkDown()(s)
    m = re.search('href="(.*?)"', md)
    if m:
        return m[1]
    else:
        return None



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
        from ..webpage.markdown import MarkDown
        
        url = conf.hostname + conf.url()
        source = conf.hostname + link2href(self.source)

        topics = ', '.join(f'topic:{t.id}' for t in self.topics)
        text = ('\n---\n'
                f'This message is sent from ODMF: {source}\n'
                f'to these topics: {topics}\n'
                f'You can change your topics here: {url}user/\n'
        )
        return text

    def to(self, cc: Optional[List[Person]]=None):
        """Returns a list of all receivers of the messages"""

        return subscribers(self.topics, cc)

    def send(self, *cc: Optional[List[Person]], with_footer=True):
        """
        Sends the message to all email addresses subscribed to the topics. Resolves cross-posting.
        If date is not set, send will set the date to now
        """
        content = self.content
        if with_footer:
            content += '\n' + self.footer()
        self.date = self.date or datetime.now()
        receivers = [r.email for r in self.to(cc)]
        with Mailer(conf.mailer_config) as mailer:
            mailer.send(
                subject=self.subject,
                body=content,
                receivers=receivers
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








