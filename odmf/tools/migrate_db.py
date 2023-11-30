"""
Migrates the database

Changes to the db schema of existing tables should be reflected here.

New tables get added by create tables. Changes to columns should be described here.
"""
import sqlalchemy as sql
from sqlalchemy.sql.type_api import TypeEngine as SqlTypeEngine
import logging
logger = logging.getLogger(__name__)
class Migrator:
    """
    A class to migrate the database by adding necessary columns
    """
    def __init__(self):
        from .. import db
        self.db = db

    def add_column(self, table: str, column: str, type: SqlTypeEngine, constraint=''):
        inspector = self.db.sql.inspect(self.db.engine)
        columns = [c['name'] for c in inspector.get_columns(table)]
        if column not in columns:
            self.db.engine.execute(f'ALTER TABLE {table} ADD COLUMN {column} {type.compile()} {constraint};')
            logger.info(f'added {table}.{column}')

    def run(self):
        self.add_column('project', 'organization', sql.String(), "default 'uni-giessen.de'")
        self.add_column('project', 'sourcelink', sql.String())
        logger.info('migration complete')

    def ___run_all(self):
        """
        Just an idea - not tested, do not use

        Should do the following - traverse all tables and columns, check if they exist in database and
        add them as needed.

        sqlalchemy.sql.ddl.CreateColumns does not respect ForeignKeys, defaults, etc.
        One idea would be: run CreateTable on the table and parse the sql columns output
        :return:
        """
        inspector = self.db.sql.inspect(self.db.engine)
        from sqlalchemy.sql import ddl
        for table_name, table in self.db.Base.metadata.tables.items():
            columns = [c['name'] for c in inspector.get_columns(table)]
            for c in table.columns:
                if c.name not in columns:
                    cc = ddl.CreateColumn(c)
                    self.db.engine.execute(f'ALTER TABLE {table_name} ADD COLUMN {cc}')


def migrate():
    Migrator().run()



