#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''
Created on 13.02.2012

@author: philkraf
'''

import sqlalchemy as sql
import sqlalchemy.orm as orm
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
from functools import total_ordering

from ..config import conf

from logging import getLogger
logger = getLogger(__name__)


def newid(cls, session):
    """Creates a new id for all mapped classes with an field called id, which is of integer type"""
    max_id = session.query(sql.func.max(cls.id)).select_from(cls).scalar()
    if max_id is not None:
        return max_id + 1
    else:
        return 1


def get_session_class():

    # check for sqlite in engine
    if conf.database_url.startswith('sqlite://'):
        from sqlalchemy.pool import StaticPool
        engine = sql.create_engine(conf.database_url,
                               connect_args={'check_same_thread': False},
                               poolclass=StaticPool)
    else:
        engine = sql.create_engine(conf.database_url)
    # Try to connect to engine
    with engine.connect():
        ...
    return engine, orm.sessionmaker(bind=engine)


engine, Session = get_session_class()


@contextmanager
def session_scope() -> orm.Session:
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def table(obj) -> sql.Table:
    """
    Returns the sql.Table of a ORM object
    """
    try:
        return getattr(obj, '__table__')
    except AttributeError:
        raise TypeError(f'{obj!r} is not a mapper class')


@total_ordering
class Base(object):
    """Hooks into SQLAlchemy's magic to make :meth:`__repr__`s."""

    def __repr__(self):
        def reprs():
            for col in table(self).c:
                try:
                    yield col.name, str(getattr(self, col.name))
                except Exception as e:
                    yield col.name, f'<unknown value: {type(e)}>'

        def formats(seq):
            for key, value in seq:
                yield f'{key}={value}'

        args = ', '.join(formats(reprs()))
        classy = type(self).__name__
        return f'{classy}({args})'

    def __lt__(self, other):
        if isinstance(other, type(self)) and hasattr(self, 'id'):
            return self.id < other.id
        else:
            raise TypeError(
                f'\'<\' not supported between instances of {self.__class__.__name__} and {other.__class__.__name__}')

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return hash(repr(self))

    def session(self) -> Session:
        return Session.object_session(self)

    @classmethod
    def query(cls, session):
        return session.query(cls)

    @classmethod
    def get(cls, session, id):
        return session.query(cls).get(id)


Base = declarative_base(cls=Base)
metadata = Base.metadata


def primarykey():
    return sql.Column(sql.Integer, primary_key=True)


def stringcol():
    return sql.Column(sql.String)


class ObjectGetter:
    """
    A helper class for interactive environments for simple access to orm-objects

    Usage:

    >>> ds = ObjectGetter(db.Dataset, session)
    >>> print(ds[10])
    >>> ds.q.filter_by(measured_by='philipp')
    """
    def __init__(self, cls: type, session: orm.Session):
        self.cls = cls
        self.session = session

    @property
    def q(self) -> orm.Query:
        return self.session.query(self.cls)

    def __getitem__(self, item):
        return self.q.get(item)

    def __repr__(self):
        return 'ObjectGetter(' + self.cls.__name__ + ')'



