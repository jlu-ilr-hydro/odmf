# Installation

1. Clone github repository and install python dependencies
    ```
    $ git clone https://github.com/jlu-ilr-hydro/odmf.git
    $ cd odmf;
    $ pip install -r requirements.txt # if you want a dev install
    $ python setup.py install
    ```
    or install via pip
    ```
    $ pip install odmf
    ```

    After this create a directory, for later use we name it `odmf-server` and place a `conf.py` into it.
    Your directory looks like this:
    ```
    $ tree .
    odmf-server/
    └── conf.py
    ```
2. Install Postgres database

    We recommend the latest version but at least 9.5

    ```
    $ sudo apt-get install postgresql-dev-9.5
    ```
3. Optional you can set up the HydroServerLite too, if you want to publish your data into the CUAHSI network.
See the HydroServerLite tutorial for this.

When all prerequesites are met, you navigate to the `odmf-server` folder and type:
```
$ odmf-install .
```
Note the `.` at the end.
If you set everything up correctly, this script should set up (1) you initial database contents and (2) the folder
structure for your server-files.

Your directory should now look like this:
```
$ tree .
odmf-server/
├── conf.py
└── webpage
    ├── datafiles
    ├── preferences
    └── sessions

```

We have now finished the installation process and are able to start the server with:
```
$ odm-start
```

More details on the usage of the platform can be found in the [usage chapter](usage.html).

## Configuration

Describes more sophisticated server configurations via one file.

* Configure database connections, timezones, admin accounts, host/wsdl urls

* whats with media, css, images, logos

### The ```conf.py``` File

In the root directory there is the main configuration file, called `.conf.py`. Via this file you configure the variable
parts of the ODMF installation.


## WaterOneFlow

This covers the installation of the PHP server [HydroServerLite](https://github.com/CUAHSI/HydroServerLite)
and the deployment of SQL Views. This views are used on the side of the ODMF schema to map it to the relations which
are used with the HydroServer.

### HydroServerLite

The code is downloaded from Github and exposed via an Apache instance.

Possible alternative to PHP based server is this python solution [WOFpy](https://github.com/ODM2/WOFpy). It relies on
the ODM schema 2.0.
