"""
This file contains the administrator interface,
created with click, which is used as the entry poit of odmf


"""

import click
import humanize
import sys
import os
import logging

logger = logging.getLogger(__name__)


@click.group()
@click.option('-v', '--verbose', count=True)
def cli(verbose):
    levels = {0: logging.ERROR, 1: logging.WARNING, 2: logging.INFO, 3: logging.DEBUG}
    logging.basicConfig(
        format='%(levelname)-8s: %(asctime)s %(name)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
        level=levels.get(verbose, logging.WARNING)
    )


@cli.command()
@click.argument('workdir', default='.')
@click.option('--autoreload/--no-autoreload', '-a', default=False, show_default=True,
              help='Switch autoreload on for an automatic restart of the server if the code changes')
def start(workdir, autoreload):
    """
    Starts a cherrypy server, with WORKDIR as the working directory (local ressources and configuration)
    """
    os.chdir(workdir)

    logger.info(f"interpreter: {sys.executable}")
    logger.info(f"workdir: {os.getcwd()}")
    from .tools import server
    server.prepare_workdir()
    server.start(autoreload)


@cli.command()
@click.argument('db_url')
@click.option('--port', default=8080, type=int, envvar='ODMF_PORT',
              help='Port to run the standalone server')
@click.option('--root_url', default='/', envvar='ODMF_ROOT_URL',
              help='URL of the root')
@click.option('--default_timezone', default='Europe/Berlin', envvar='ODMF_DEFAULT_TIMEZONE',
              help='Default timezone for all dates')
def configure(db_url, port, root_url, default_timezone):
    """
    Creates a new configuraton file (./config.yml) using the given database url and a port to run the server on

    Parameters
    ----------
        db_url:
            A URL to a database. See: https://docs.sqlalchemy.org/en/13/core/engines.html

            File access databases or unix-socket database are connected like this
            - postgresql:///odmf-NAME
            - sqlite:///srv/odmf/NAME/data.sqlite

            Access to a database over a network works generally like this:
            - postgresql://odmf-NAME:ThePassword@example.com:5432/odmf-NAME
    """

    from odmf.config import conf
    conf.database_url = db_url
    conf.server_port = port
    conf.root_url = root_url
    conf.datetime_default_timezone = default_timezone

    from pathlib import Path
    conf_file = Path('config.yml')
    conf.to_yaml(conf_file.open('w'))
    logger.info('config.yml written')


@cli.command()
def systemd_unit():
    """
    Creates a systemd service file and a /etc/sudoers.d file to allow non-sudoers to start / restart / stop the service
    """
    from .tools.systemctl import make_service
    # Writes the service files and returns a text explaining how to install the systemd service
    print(make_service())


@cli.command()
@click.option('--admin-pw', '-p', envvar='ODMF_ADMIN_PW', help='Password of the new odmf.admin')
@click.option('--db_waittime', '-t', envvar='ODMF_DB_WAITTIME', type=float, default=20,
              help='Seconds to wait for the database')
def db_create(admin_pw, db_waittime):
    """
    Creates in the database: all tables, a user odmf.admin
    and fills the data-quality table with some usable input
    """
    from .tools import create_db as cdb
    cdb.init_db(admin_pw, db_waittime)


@cli.command()
def db_test():
    """
    Tests if the system can be connected to the database
    """
    from . import db
    import sqlalchemy.orm as orm
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
            q: orm.Query = session.query(table)
            print(f'{humanize.intword(q.count())} {name} objects in database')


@cli.command()
def db_tables():
    """
    Returns the tables in the ORM system as a space seperated list
    """

    from . import db
    print(' '.join(db.Base.metadata.tables))


@cli.command()
def test_config():
    """
    Tests the configuration and prints it, if it works
    """
    from .config import conf
    conf.to_yaml()



@cli.command()
def test_static():
    from pathlib import Path
    from .config import conf
    candidates = Path(sys.prefix), Path(__file__).parents[2], Path(conf.static)

    for c in candidates:
        p = c / 'odmf.static'
        if p.exists():
            if all((p / d).exists() for d in ('templates', 'datafiles', 'media')):
                logger.info(f'OK: Global static files found at: {p}\n')
                break
            else:
                logger.warning(f'Incomplete static file directory found at: {p}, searching further\n')
        else:
            logger.warning(f'{p} - does not exist\n')


@cli.command()
@click.option('--only_navigatable/--any', '-n', default=False)
@click.option('--level', '-l', type=int, help='Admission level (0-4)', default=0)
def uri_tree(only_navigatable, level):
    """
    Prints the tree of available resources of odmf
    """
    import yaml
    from .webpage import Root
    from .webpage.lib import Resource
    if not only_navigatable:
        level = None
    res = Resource(Root()).create_tree(navigatable_for=level, recursive=True)
    for r in res.walk():
        print(f'{r.uri}: {r.doc}')


@cli.command()
def interactive():
    """
    Launches an IPython shell with odmf related symbols. Needs IPython
    """
    from textwrap import dedent
    from IPython import start_ipython
    # https://stackoverflow.com/a/36699427/3032680
    from traitlets.config.loader import Config as IPythonConfig
    from .config import conf
    from . import db
    import pandas as pd
    import numpy as np
    greetings = dedent("""
        
        Imported modules
        ----------------
        
        pd, np, conf, db
        
        Defined symbols
        ---------------
        session: a SQLAlchemy session to load Database objects
        q: a shortcut for session.query
        ds: An ObjectGetter for datasets
        person: An ObjectGetter for persons
        site: An ObjectGetter for sites

        Usage of a ObjectGetters: 
        
        Get dataset with id=1
        >>>ds_one = ds[1]
        Query sites:
        >>>site.q.filter(db.Site.lat > 50.5).count()        
        """)
    with db.session_scope() as session:
        user_ns= dict(
            session=session,
            q=session.query,
            ds=db.base.ObjectGetter(db.Dataset, session),
            person=db.base.ObjectGetter(db.Person, session),
            site=db.base.ObjectGetter(db.Site, session),
            pd=pd, np=np, conf=conf, db=db
        )
        print('\n\n================================================')
        print(f'  ODMF:{conf.root_url} {conf.version} interactive IPython shell')
        print('================================================')
        print(greetings)
        start_ipython(argv=[], user_ns=user_ns, display_banner=False)

@cli.command()
@click.option('--verbose/--terse', '-v', default=False)
def version(verbose: bool):
    """
    Prints the actual odmf version
    """
    from . import __version__
    print('odmf', __version__)
    if verbose:
        import sys
        print('Python executable:', sys.executable)
        print('Python version:', sys.version)


if __name__ == '__main__':
    cli(auto_envvar_prefix='ODMF')
