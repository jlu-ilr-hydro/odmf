# Installation

ODMF is known to run on Linux and Windows.  

We recommend to deploy ODMF on an actual Ubuntu or Debian system with postgreSQL as the 
database backend. The ODMF server (cherrypy) can be run as a systemd service, 
to let your OS manage restarts.

## Prepare OS
On Ubuntu, you can install all dependencies using 

    sudo odmf-src/bin/ubuntu_setup.sh

## Make your config.yml file

    odmf configure --dbname instance --dbuser instance-user --port 8081

## Setup of a Apache-Proxy

Create a local apache2 conf file:

    odmf apache2-conf

creates odmf-instance.conf with the following content

If you have your server files installed at /srv/odmf/instance and you plan to install
other odmf instances at the same place, we recommend to alter your default-site.conf
at `/etc/apache2/default-ssl.conf` with this line in the virtual host definition:

    IncludeOptional /srv/odmf/*/odmf-*.conf

