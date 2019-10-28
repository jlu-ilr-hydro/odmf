"""
This file contains the administrator interface,
created with click, which is used as the entry poit of odmf


"""

import click
import humanize

@click.group()
def cli():
    ...


@cli.command()
@click.option('--dbname', help='Name of the database', prompt='database name')
@click.option('--dbuser', help='Name of the database user', prompt='database user')
@click.option('--dbpass', help='Password for the user', prompt='database password')
@click.option('--dbhost', default='127.0.0.1',
              help='IP-Adress or DNS-Hostname of the database host. Default: localhost', prompt='database hostname:')
@click.option('--port', default=8080, help='Port to run the standalone server', type=int, prompt='server port')
def configure(dbname, dbuser, dbpass, dbhost, port):
    """
    Creates a new configuraton file (./config.yml) using the given database credentials.
    """
    new_config = dict(database_name=dbname, database_username=dbuser, database_password=dbpass,
                      database_host=dbhost, server_port=port)
    import yaml
    from pathlib import Path
    conf_file = Path('config.yml')
    with conf_file.open('w') as f:
        yaml.dump(new_config, stream=f)
    from .config import conf
    conf.to_yaml(conf_file.open('w'))


@cli.command()
@click.option('--new_admin_pass', '-p', help='Password of the new admin',
              prompt=True, hide_input=True, confirmation_prompt=True)
def make_db(new_admin_pass):
    """
    Creates in the database: all tables, a user odmf.admin
    and fills the data-quality table with some usable input
    """
    from . import create_db as cdb
    cdb.create_all_tables()
    cdb.add_admin(new_admin_pass)
    cdb.add_quality_data(cdb.quality_data)


@cli.command()
def test_config():
    """
    Tests the configuration and prints it, if it works
    """
    from .config import conf
    conf.to_yaml()


@cli.command()
def test_db():
    """
    Tests if the system can be connected to the database
    """
    from .. import db
    with db.session_scope() as session:
        tables = [
            (n, c)
            for n, c in vars(db).items()
            if (isinstance(c, type) and
                issubclass(c, db.Base) and
                c is not db.Base
                )
        ]
        for name, table in tables:
            print(f'db.{name}: ', end='')
            q = session.query(table)
            print(f'{humanize.intword(q.count())} {name} objects in database')


if __name__ == '__main__':
    cli()
