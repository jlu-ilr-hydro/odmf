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
    os.chdir(workdir)
    # coloredlogs.install(level='DEBUG', stream=sys.stdout)

    logger.info(f"interpreter: {sys.executable}")
    logger.info(f"workdir: {os.getcwd()}")
    from .tools import server
    server.prepare_workdir()
    server.start(autoreload)


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
def systemd_unit():
    """
    Makes a systemd service description file. Usage:
    odmf systemd-unit
    """
    from .config import conf
    bin_path = os.path.abspath(os.path.dirname(sys.executable))
    cwd = os.path.abspath(os.getcwd())
    content = f"""
[Unit]
Description={conf.description}
After=network.target

[Service]
User={conf.user}
WorkingDirectory={conf.home}
ExecStart={bin_path}/odmf start
Restart=always

[Install]
WantedBy=multi-user.target
    """
    open(f'odmf-{conf.name}.service', 'w').write(content)
    print(f'Created file: odmf-{conf.name}.service')
    print()
    print('For Debian-line systems do:')
    print(f'    adduser --system  --gecos "ODMF/$NAME Service" --disabled-password --group --home {cwd} {conf.user}')
    print("Add your own user to the group of this service to act as an admin with this command:")
    print(f'    sudo adduser USER {conf.user}')
    print(f'    sudo cp odmf-{conf.name}.service /etc/systemd/system')
    print(f'    sudo systemctl enable odmf-{conf.name}.service')
    print(f'    sudo systemctl start odmf-{conf.name}.service')


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
@click.argument('uri', default='')
def make_apache_conf(uri: str):
    """
    Creates a apache2 .conf file to run this odmf instance as a wsgi server.
    Use as:

    """
    from pathlib import Path
    uri = uri or Path('.').resolve().name
    if uri.startswith('/'):
        uri = uri[1:]
    name = uri.replace('/', '.')
    path = Path('.').resolve().as_posix()
    aconf = f"""
    WSGIDaemonProcess {name} python-home={path}/venv
    WSGIProcessGroup {name}
    WSGIScriptAlias /{uri} /var/wsgi/{uri}/odmf.wsgi
    <Directory {path}>
        Require all granted
    </Directory>
"""

    fn = f'/etc/apache2/conf-available/{name}.conf'
    fn_enabled = fn.replace("available", "enabled")

    sys.stderr.write(f'''
Created .conf file for apache for usage as a conf-file for all hosts. 
Copy content into a site .conf file to make it specific for a virtual host

Optimal Usage:

  odmf make-apache-conf {name} >{name}.conf
  sudo cp {name}.conf {fn}
  sudo ln -s {fn} {fn_enabled} 

''')

    sys.stdout.write(aconf)



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
            print(f'{humanize.intword(q.count())} {name} objects in database', end=' - ')
            print(repr(q.first()))


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
@click.argument('filename')
def import_config(filename):
    """
    Imports a configuration from a conf.py file 
    """
    from .config import import_module_configuration
    conf = import_module_configuration(filename)
    conf.to_yaml(open('config.yml', 'w'))


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


if __name__ == '__main__':
    cli()
