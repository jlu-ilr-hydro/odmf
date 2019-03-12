# Installation

## ODMF Server

How to install the ODMF server software to maintain measurement data.

1. Clone the github repository and install python dependencies

    ```
    $ git clone https://github.com/jlu-ilr-hydro/odmf.git
    $ cd odmf
    $ pip install -r requirements.txt
    $ cd odmf
    $ cp conf-template.py conf.py
    ```

2. If you havn't already, install a postgres database.
   We recommend the latest version but at least 9.5

    ```
    $ sudo apt-get install postgresql-dev-9.5
    ```

3. Change the config with the instructions from [conf.py](https://jlu-ilr-hydro.github.io/odmf/source/conf.py) wiki page. When the configuration is changed to meet your requirements, start the server and browse to https://localhost:8080

    ```
    $ python3 start.py
    ```
### Configuration

Describes more sophisticated server configurations via one file.

* Configure database connections, timezones, admin accounts, host/wsdl urls

* whats with media, css, images, logos

#### The ```conf.py``` File

In the root directory is the main configuration file located. It's called `.conf.py` and it configures the variable
parts of the ODMF installation.

**Keywords**:

*Mandatory Keywords*
* **CFG_SERVER_PORT**: Port number where the server instance is listening for requests.
* **CFG_DATABASE_NAME**: Database name where schema is deployed and used.
* **CFG_DATABASE_USERNAME**: Database user credentials name.
* **CFG_DATABASE_PASSWORD**: Database user credentials password.
* **CFG_DATABASE_HOST**: Database host url.

*Optional Keywords*
* **CFG_DATETIME_DEFAULT_TIMEZONE**: Timezone in pytz compatible format
* **CFG_MEDIA_IMAGE_PATH**: Path relative to server script. See [usage](usage.html#media-folder)
* **CFG_MANUAL_MEASUREMENTS_PATTERN**: Regular expression pattern, where in the relative path of datafiles
  ([see usage](usage.html#datafiles-folder)) manual measurements files are stored. This folder and the subfolders
  get a special treatment from dataimport/mm.py
* **CFG_MAP_DEFAULT**: Default location where the map is pointing when hitting the landing page
* **CFG_UPLOAD_MAX_SIZE**: Maximum file size for files uploaded into the [download view](views.html#download).

Now your server is configured and you can start [using](usage.html) it.

## WaterOneFlow

Optional you can set up the HydroServerLite too, if you want to publish your data via the CUAHSI network using
the WaterOneFlow interface.

This covers the installation of the PHP server [HydroServerLite](https://github.com/CUAHSI/HydroServerLite)
and the deployment of SQL Views. This views are used on the side of the ODMF schema to map it to the relations
which are used with the HydroServer.

### HydroServerLite

If you set everything up correctly, this script should set up (1) you initial database contents and (2) the folder
structure for your server-files.

1. Migrate ODMF schema to ODM
2. Create SQL views, materialized views and helper tables
3. Register cron jobs for daily update of transformed timeseries

Possible alternative to PHP based server is this python solution [WOFpy](https://github.com/ODM2/WOFpy).
It relies on the ODM schema 2.0.
