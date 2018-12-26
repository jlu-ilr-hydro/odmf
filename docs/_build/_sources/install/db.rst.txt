Installation
============

Installation of the schwingbach observatory software.

You can run the `` install.sh `` script in the root directory or you can work through
this installation instructions. If you run into errors while executing `` install.sh ``,
check out the :ref:`Troubleshoot <installation-troubleshooting>`.

Requirements
*************

1. Linux packages
    * ``python-cherrypy{3}`` - if your Python version is 2 or 3.
2. Postgres-Server is 9.1 minimum, but we recommend to install the most recent version.

In order to setup the SBO database application, navigate to the root directory of
your source directory and just do ``pip install -r requirements.txt``. Now you have
all packages in place to run the server and its database.

Now you need to initialize the database structure. To do this, execute the following script ``database.sh``.

Follow :ref:`HydroServer installation <hs-installation>` for instructions to setup the WaterOneFlow Interface.

Configuration
**************

This part describes the how to configure the server for your special needs.

Hydroserver-Installation
************************
.. _hs-installation:

Installation is only recommended if you decide to share data with the CUAHSI data network. Note that for this purpose
you configure how the access to what kind of data is done.

Download PHP-Repository

1. Extend the SQL-Schema (if needed)

1.1 Enrich your data with MasterCV from CUAHSI (recommended)

2. Deploy the PHP Server

Requirements
*************

1. All server functions of HydroServerLite work without a problem with PHP Verision ``5.5.9``

Troubleshooting
***************
.. _installation-troubleshooting:
