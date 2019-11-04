"""
This file contains the administrator interface,
created with click, which is used as the entry poit of odmf


"""

import click
import humanize
import sys
import os

@click.group()
def cli():
    ...

@cli.command()
@click.argument('workdir', default='.')
@click.option('--autoreload/--no-autoreload', '-a', default=False, show_default=True,
              help='Switch autoreload on for an automatic restart of the server if the code changes')
def start(workdir, autoreload):
    """
    Starts a cherrypy server, with WORKDIR as the working directory (local ressources and configuration)
    """
    from glob import glob
    os.chdir(workdir)
    print("Starting odmf:\n",
          f"  - interpreter: {sys.executable}\n",
          f"  - workdir: {os.getcwd()}\n")

    if sys.version_info[0] < 3:
        raise Exception("Must be using Python 3")

    # System checks !before project imports
    from .config import conf
    if conf:
        # Check for mandatory attributes
        print("✔ Config is valid")
    else:
        print("Error in config validation")
        exit(1)

    # Start with project imports
    from odmf.webpage import Root
    from odmf.webpage import lib

    print("autoreload =", autoreload)

    print("Kill session lock files")
    for fn in glob('sessions/*.lock'):
        os.remove(fn)

    # Create the URL root object
    root = Root()

    # Start the server
    lib.start_server(root, autoreload=autoreload, port=conf.server_port)


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
    from .tools import create_db as cdb
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
    from . import db
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


@cli.command()
def test_static():
    from pathlib import Path
    from .config import conf
    candidates = Path(sys.prefix), Path(__file__).parents[2], Path(conf.static)

    for c in candidates:
        p = c / 'odmf.static'
        if p.exists():
            if all((p / d).exists() for d in ('templates', 'datafiles', 'media')):
                sys.stdout.write(f'OK: Global static files found at: {p}\n')
                break
            else:
                sys.stderr.write(f'Incomplete static file directory found at: {p}, searching further\n')
        else:
            sys.stderr.write(f'{p} - does not exist\n')


if __name__ == '__main__':
    cli()
