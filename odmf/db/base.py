#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''
Created on 13.02.2012

@author: philkraf
'''

import sqlalchemy as sql
import sqlalchemy.orm as orm
from sqlalchemy.ext.declarative import declarative_base
from io import StringIO
import os.path as op
from .. import conf

from contextlib import contextmanager
from cherrypy import log


def abspath(fn):
    "Returns the absolute path to the relative filename fn"
    basepath = op.abspath(op.dirname(__file__))
    normpath = op.normpath(fn)
    return op.join(basepath, normpath)


def newid(cls, session=None):
    "Creates a new id for all mapped classes with an field called id, which is of integer type"
    if not session:
        session = Session()
    max_id = session.query(sql.func.max(cls.id)).select_from(cls).scalar()
    if max_id is not None:
        return max_id + 1
    else:
        return 1


def connect():
    log("Connecting with database %s at %s ..." %
        (conf.CFG_DATABASE_NAME, conf.CFG_DATABASE_HOST))
    import psycopg2
    return psycopg2.connect(user=conf.CFG_DATABASE_USERNAME,
                            host=conf.CFG_DATABASE_HOST,
                            password=conf.CFG_DATABASE_PASSWORD,
                            database=conf.CFG_DATABASE_NAME)


# FIXME: allow test suite to load sqlite
# TODO: allow test suite to load postgres and import all sql files (compliance test for sql)
if conf.DATABASE == 'postgres':
    engine = sql.create_engine('postgresql://', creator=connect)
elif conf.DATABASE == 'sqlite':
    if op.exists(conf.SQLITE_PATH):
        engine = sql.create_engine('sqlite:///%s' % conf.SQLITE_PATH)
    else:
        raise RuntimeError('Couldn\'t find offline database at \'%s\'.' % conf.SQLITE_PATH)

Session = orm.sessionmaker(bind=engine)
scoped_session = orm.scoped_session(Session)


@contextmanager
def session_scope():
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


class Base(object):
    """Hooks into SQLAlchemy's magic to make :meth:`__repr__`s."""

    def __repr__(self):
        def reprs():
            for col in self.__table__.c:
                try:
                    yield col.name, str(getattr(self, col.name))
                except:
                    pass

        def formats(seq):
            for key, value in seq:
                yield '%s=%s' % (key, value)

        args = '(%s)' % ', '.join(formats(reprs()))
        classy = type(self).__name__
        return "<%s%s>" % (classy, args)

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
