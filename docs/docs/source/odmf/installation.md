# Installation

ODMF is known to run on Linux and Windows.  

We recommend to deploy ODMF on an actual Ubuntu or Debian system with postgreSQL as the 
database backend. The ODMF server (cherrypy) can be run as a systemd service, 
to let your OS manage restarts.

## Prepare OS

On Ubuntu, you can install all dependencies using 

    sudo odmf-src/bin/ubuntu_setup.sh

## Use a name for your ODMF instance

    export NAME=test

## Install ODMF

### Create the ODMF-Home directory

We recommend to install your ODMF instance (except for test purposes) to `/srv/odmf/$NAME`, but any directory is ok.
Make sure there is enough disk space at the target. You can also create a link at /srv to the installation

For later use, create a dedicated user for your odmf instance, with a home directory:

    sudo adduser --system  --gecos "ODMF/$NAME Service" --disabled-password --group --home /srv/odmf/$NAME odmf-$NAME

Change the mode of the home directory, to allow group members to write and execute everything:

    sudo chmod g+rwxs /srv/odmf/$NAME 
    
Add your user to the odmf-$NAME group (as well as any co-admin of odmf). Co-Admins do not need sudo rights.

    sudo adduser $USER odmf-$NAME

To make the new group active, you need to log out of your current shell and relogin.

### Create a virtual environment

A virtual environment contains a link or copy to a Python-interpreter with its
own and independent set of libraries. It is strongly recommended to use a virtual
environment, either the built-in `venv` or a `conda` environment. In this tutorial 
we are using `venv`, since no additional installations are necessary.

The Python interpreter used for the next command, will be used as the basis for the virtual 
environment.

    python3.9 -m venv /srv/odmf/$NAME/venv

Now you should set the path to use any Python related commands from that venv, by activating it. Install the
wheel package and upgrade pip.

    source /srv/odmf/$NAME/venv/bin/activate
    pip install --upgrade wheel pip

### Install ODMF source code in the virtual environment

ODMF can **either** be installed from GitHub directly (a) **or** installed from a local copy of the source code (b)

#### a) install directly from GitHUB

You can install ODMF directly from GitHUB into your venv, if you do not expect to change the source code

    pip install git+https://github.com/jlu-ilr-hydro/odmf --upgrade

#### b) clone the source and install from a local copy

Clone to a source directory

    git clone https://github.com/jlu-ilr-hydro/odmf /srv/odmf/$NAME/src

Install from that directoy
  
    pip install -e /srv/odmf/$NAME/src

### Check installation

Check the installation with the following command

    odmf version

### Enable code completion (bash in Debian / Ubuntu) 

[source](https://click.palletsprojects.com/en/8.0.x/shell-completion/)

Creates a bash file to enable code completion and alters the venv/bin/activate script to start ODMF's code completion
on activating the venv

    _ODMF_COMPLETE=bash_source odmf > venv/bin/odmf-complete.sh
    chmod ug+x venv/bin/odmf-complete.sh
    echo "source odmf-complete.sh" >> venv/bin/activate


## Create database

Install postgresql on your machine. Your database will grow, think about the physical location of the database 
and configure postgresql to store databases on your largest HDD. Read postgresql.md for information about tuning postgresql 

### Create a database user 

Make the UNIX-user a postgresql role with the privilege to create a database. If you want to connect to the database
over a network, the user needs to get a password. Create that with a `-P`-flag.
The `-d` flag enables the user to create databases

    sudo -u postgres createuser odmf-$NAME -d

Create (as the new user) the database. 

    sudo -u odmf-$NAME createdb

It is a good idea to make your own user a database super user, for administrative work
with ODMF

    sudo -u postgres createuser $USER -s

### Create a config.yml file

Create a configuration file with the database url. How to retreive the
URL is explained here: https://docs.sqlalchemy.org/en/13/core/engines.html, however the version below works for postgresql databases at the local host, using UNIX sockets

    odmf configure postgresql:///odmf-$NAME --port 8081

Edit the config file. Special care is needed for the root_url and the Google Maps API-Key and the `user`

    nano config.yml

Check, if the config.yml is working with 

    odmf test-config

### Create database tables

    odmf make-db

you will be promepted for a password of the first user (odmf.admin).

Check the database connection with

    odmf test-db

## First start

For a first try, do `odmf start`. It starts the website server at the given port in your shell. If you close your shell, the server will be
shut down, too.

It is possible to run the server in a detached terminal (like screen),
but it is recommended to run the server as a service (next step).

## Create a systemd service

If your OS should handle restart of the ODMF server after a reboot or a hang up,
systemd can manage in most Linux-Systems ODMF as a service. You need a service file,
that is copied to /etc/systemd/system. The service file is created with the command

    odmf systemd-unit

It creates 2 files, one to enable the service, the second to allow Co-Admins
to start, restart and stop the service. You are prompted on how to use the files.

## Setup of an Apache-Proxy

Create a local apache2 conf file:

    odmf apache2-conf

creates odmf-instance.conf with the following content

If you have your server files installed at /srv/odmf/instance and you plan to install
other odmf instances at the same place, we recommend to alter your default-site.conf
at `/etc/apache2/default-ssl.conf` with this line in the virtual host definition:

    IncludeOptional /srv/odmf/*/odmf-*.conf

