import sqlalchemy as sql
import sqlalchemy.orm as orm
from .base import Base
from .person import Person
from functools import total_ordering

from logging import getLogger
logger = getLogger(__name__)


@total_ordering
class Project(Base):
    """
    SqlAlchemy Object for holding project information
    """
    __tablename__ = 'project'

    id = sql.Column(sql.Integer, primary_key=True, autoincrement=True)
    _person_responsible = sql.Column('person_responsible', sql.String,
                                     sql.ForeignKey('person.username'))
    person_responsible = sql.orm.relationship(
        "Person",
        primaryjoin='Project._person_responsible==Person.username',
        backref=orm.backref('leads_projects', lazy='dynamic')
    )
    name = sql.Column(sql.String)
    comment = sql.Column(sql.String)
    sourcelink = sql.Column(sql.String)
    organization = sql.Column(sql.String, default='uni-giessen.de')
    datasets = sql.orm.relationship('Dataset')

    @property
    def members_query(self):
        """Returns a query object with all ProjectMember object related to this project"""
        return self.session().query(ProjectMember).filter(ProjectMember._project==self.id)
    def members(self, access_level=0):
         for pm in (
                 self.members_query.filter(ProjectMember.access_level>=access_level)
                     .order_by(ProjectMember.access_level.desc(), ProjectMember._member)
         ):
             yield pm.member, pm.access_level

    def add_member(self, person: Person|str, access_level: int=0):
        if pm:=self[person]:
            pm.access_level = access_level
        else:
            if not type(person) is Person:
                person = Person.get(self.session(), person)
            pm = ProjectMember(member=person, project=self, access_level=access_level)
            self.session().add(pm)
        return pm

    def remove_member(self, username: Person|str):
        if type(username) is Person:
            username = username.username
        n=self.members_query.filter_by(_member=username).delete()
        if not n:
            raise ValueError(f'{username} was not a member of {self}, cannot remove')

    def __getitem__(self, username):
        if type(username) is Person:
            username = username.username
        return self.members_query.filter_by(_member=username).first()


    def get_access_level(self, user: Person|str):
        if not type(user) is Person:
            user = Person.get(self.session(), user)

        if user == self.person_responsible:
            return 4
        elif user.access_level>=4:
            return user.access_level
        for member, level in self.members():
            if member == user:
                return level
        else:
            return 0


    def __str__(self):
        return f'prj:{self.id} {self.name} ({self.person_responsible})'

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


class ProjectMember(Base):
    """
    n:n Association object between projects and their members.

    TODO: Write tests
    """
    __tablename__ = 'project_member'

    _project = sql.Column('project', sql.ForeignKey('project.id', ondelete='CASCADE'), primary_key=True)
    _member = sql.Column('member', sql.ForeignKey('person.username', ondelete='CASCADE'), primary_key=True)

    project = sql.orm.relationship('Project')
    member = sql.orm.relationship('Person')

    access_level = sql.Column(sql.Integer, nullable=False, default=0)

