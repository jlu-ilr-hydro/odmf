import typing

import sqlalchemy as sql
import sqlalchemy.orm as orm
from functools import total_ordering
import typing as t

from .base import Base

from logging import getLogger
logger = getLogger(__name__)


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
    access_level = sql.Column(sql.INTEGER, nullable=False, default=0)
    active = sql.Column(sql.Boolean, default=True, nullable=False)

    topics: orm.Mapped[t.List['Topic']] = orm.relationship(secondary='subscribes', back_populates='subscribers')

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

    def __lt__(self, other):
        if not hasattr(other, 'surname'):
            if not hasattr(other, 'firstname'):
                return NotImplemented
            return self.surname < str(other)
        return self.surname < other.surname

    def projects(self):
        """
        Yields Project, access_level tuples
        :return:
        """
        from .project import ProjectMember, Project
        from ..webpage.auth import Level
        if not self.session():
            return None
        else:
            pm: ProjectMember
            for pm in (
                    self.session().query(ProjectMember)
                        .filter(ProjectMember.member == self)
                        .order_by(ProjectMember.access_level.desc(), ProjectMember._member)
            ):
                yield pm.project, Level(pm.access_level)
            for project in self.session().query(Project).filter(Project.person_responsible == self):
                yield project, Level.admin


    def add_project(self, project, access_level: int=0):
        from .project import ProjectMember
        pm = ProjectMember(member=self, project=project, access_level=access_level)
        self.session().add(pm)
        return pm
