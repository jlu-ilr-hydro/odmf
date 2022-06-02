import sqlalchemy as sql
import sqlalchemy.orm as orm
from .base import Base

from functools import total_ordering

from logging import getLogger
logger = getLogger(__name__)


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
        "Person",
        primaryjoin='Project._person_responsible==Person.username',
        backref=orm.backref('leads_projects', lazy='dynamic')
    )
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
