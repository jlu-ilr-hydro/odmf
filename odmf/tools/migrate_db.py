"""
Migrates the database

Changes to the db schema of existing tables should be reflected here.

New tables get added by create tables. Changes to columns should be described here.
"""
import sqlalchemy as sql
from sqlalchemy.sql.type_api import TypeEngine as SqlTypeEngine
import logging
import dataclasses
logger = logging.getLogger(__name__)

@dataclasses.dataclass
class NewColumn:
    table: str
    column: str
    type: SqlTypeEngine
    contraint: str = ''
    _instances = []
    
    def execute(self):
        from .. import db
        inspector = sql.inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns(self.table)]
        if self.column not in columns:
            cmd = f'ALTER TABLE {self.table} ADD COLUMN {self.column} {self.type.compile()} {self.constraint};'
            logger.debug(cmd)
            db.engine.execute(cmd)
            logger.info(f'added {self.table}.{self.column}')

    def __init__(self, table: str, column: str, type: SqlTypeEngine, constraint=''):
        self.table = table
        self.column = column
        self.type = type
        self.constraint = constraint
        NewColumn._instances.append(self)

    @classmethod
    def execute_all(cls):
        for obj in cls._instances:
            obj.execute()

new_column_list = []
def new_column(column: sql.Column):
    new_column_list.append(column)
    return column



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
    for col in new_column_list:
        expr = col.expression
        print(expr)
        NewColumn(expr.table.name, expr.name, expr.type, ' '.join(expr.constraints)).execute()

    # NewColumn.execute_all()
    # Migrator().run()



