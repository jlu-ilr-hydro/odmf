#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''
Created on 13.02.2012

@author: philkraf
'''

import sqlalchemy as sql
import sqlalchemy.orm as orm
from sqlalchemy.ext.declarative import declarative_base

import os.path as op
from ..config import conf

from contextlib import contextmanager
from logging import info
from functools import total_ordering

def newid(cls, session):
    """Creates a new id for all mapped classes with an field called id, which is of integer type"""
    max_id = session.query(sql.func.max(cls.id)).select_from(cls).scalar()
    if max_id is not None:
        return max_id + 1
    else:
        return 1


def connect():
    info(f"Connecting with database {conf.database_name} at {conf.database_host} ..." )
    import psycopg2
    return psycopg2.connect(user=conf.database_username,
                            host=conf.database_host,
                            password=conf.database_password,
                            database=conf.database_name)


# FIXME: allow test suite to load sqlite
# TODO: allow test suite to load postgres and import all sql files (compliance test for sql)
if conf.database_type == 'postgres':
    engine = sql.create_engine('postgresql://', creator=connect)
elif conf.database_type == 'sqlite':
    if op.exists(conf.sqlite_path):
        engine = sql.create_engine('sqlite:///%s' % conf.sqlite_path)
    else:
        raise RuntimeError('Couldn\'t find offline database at \'%s\'.' % conf.sqlite_path)

Session = orm.sessionmaker(bind=engine)


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
        if isinstance(other, type(self)) and hasattr('id', self):
            return self.id < other.id
        else:
            raise TypeError(
                f'\'<\' not supported between instances of {self.__class__.__name__} and {other.__class__.__name__}')

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return hash(repr(self.__class__.__name__))

    def session(self):
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
    def __init__(self, cls, session: orm.Session):
        self.cls = cls
        self.session = session

    @property
    def q(self) -> orm.Query:
        return self.session.query(self.cls)

    def __getitem__(self, item):
        return self.q.get(item)



