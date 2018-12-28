# Development

This chapter is intended to give an overview about the source code structure and the server stack used for ODMF. Also
it let you understand the database schema which is essential to the development, since a ORM framework is in use.
So this chapter should be referred to, when developing the platform.
At the beginning there is a brief introduction to the design of the server system. After getting a overview of the
platform and its coherences, the [database](development.html#database-erm) is described briefly and the
[ORM mapping](development.html#database-orm-mapping) is explained in detail, so when developing you can make use of
the `odmf.db`-package.

In the following picture the server stack, consisting of the backend framework [cherrypy](https://cherrypy.org), which
connects the [postgres](https://postgres.org) database and renders with the help of templating engine
[genshi](https://genshi.edgewall.org/) the HTML content and a bit of [jquery](https://jquery.org).
Speaking of the server code, the database is accessed consistently via the ORM-mapping framework [sqlalchemy](https://www.sqlalchemy.org).
The Cherrypy server also exposes some methods as JSON exports for a rest-like use of data retrieval.

![Picture of the ODMF database schema]( ../../images/umls/server-stack.jpg "ODMF server stack")

The development was done between 2013-today partially by a team of one or two developers. There are some acceptance
and ui tests, but no unit tests.

The code base is divided in three main parts. **Server**, **automated import** and
**database communication**.

* Most of the **server** functionality is in the `webpage` module. It covers starting
  and stopping the server. Exposing of webpages and data endpoints.

  * Module `pages` contains all pages, unless they are `plot`, `site`, `upload`, `dataset` or `map`.
    In `webpage/lib.py` is utility code.
  * The `auth` module is based on the `bcrypt` hashing implementation.

* **automated import** functions reside in `dataimport` module.

* **database** and ORM code is in `db` the module.

Utility code for calibration, conf and markdown parsing are saved in the `tools` module.

## Core thoughts behind design decisions

To connect more of the ideas under the hood of the server there are diagrams describing the user interaction for the most important functions of the platform.

* Schwingbach FMC (Detail)
  - User interaction (WOF)
  - User interaction (data import)
  - ...
* CUAHSI WOF transactions diagram
* Views a. CV-Tables extending ODMF data schema

### Database (ERM)

![Picture of the ODMF database schema]( ../../images/schwingbach.png "ODMF database schema")


## Database (ORM mapping)

The Python ORM framework [SQLalchemy](https://www.sqlalchemy.org) is used for handling data transactions for user
administration, field data import and metadata annotation.

In the relation `dataset` many foreign keys are stored, which point to other relations and additional metadata.
The most important are `site`, `valuetype` and `source`, of which the primary key of dataset consists.
The other foreign keys affiliation is straight forward.

The `record` relation keeps the essential data rows, that describe the measured data. Each row belongs to a `dataset` relation, which then extends the known data about it.

In the relation `person` all the user data is stored. Further the relation `job` contains a metadata to tasks, that are
assigned to a person. A element of relation `dataset` is assigned via `measured_by` to a `person` too.

### Dataset
Distinction between `timeseries` and `transformed_timeseries`.

A dataset object has a so called back reference to records with a `lazy` join on the records, regarding the dataset.
[See sqlalchemy docs](http://docs.sqlalchemy.org/en/latest/orm/backref.html) on backref.

### Valuetype

### Job


## Database (SQL)
### ODMF Schema Model
Elaborate on the ODMF (NOT ODM Schema model)

### View `ODM.Seriescatalog`
To provide the `begindatetimeutc` and `enddatetimeutc` of `SBO.seriescatalog`, the attributes `start` and `end` of
`SBO.dataset` are totalled up with `timezone` of `dataset` and the `pg_timezone_names.utc_offset`.
[See Postgresql docs](https://www.postgresql.org/docs/current/static/datatype-datetime.html#DATATYPE-TIMEZONES) on
timezones.



## Upload or Dataimport
Corresponds to the `/odmf/dataimport` directory.

This directory holds the files `__init__.py` and `base.py` which mainly provide some kind of abstract skeleton for the
data import. The other files go along with a descriptive filename, which is similar to names of the file including
class. For example `XlsImport` is for the import of `xls(x)` files.

Upload and data import is part of the *automated import* and is further explained in the
 [usage](usage.html#import-data) chapter.

[//]: # (TODO: Add UML diagram of LogImport etc.)

### Import process

### XlsImport
Corresponds to `odmf/dataimport/xls.py`



### `.conf`-files
The conf file upload is implemented in `dataimport.ImportDescription` and `dataimport.ImportColumn`.

If the configparser module cannot parse a file, the `UnicodeDecodeError` is catched and a the estimated encoding
is returned to the user, as part of an error message.


## Migration
Differences of the database schemas of ODMF and ODM:
* odmf.dataset attributes start and end, can be identical in the rare case of a size of just one record.

### WaterOneFlow

Details on the implementation of the WaterOneFlow interface for ODMF server software.

* What parts communicate how
* SQL Views as mapping from ODMF schema to ODM schema

### Schema mapping validity

It's important to check on the schema mapping validity, since the Schwingbach database schema is extended through different
database views to fit CUAHSI ODM schema, which is used with the HydroServerLite instance.

The helper view `sbo_odm_invalid_datasets` returns all `dataset`s which will break the ODM schema constraints, when these
datasets are extended through the database views. To prevent this break, the view `seriescatalog` filters based on
this helper view invalid datasets from being published through itself.

### Daily jobs

Creation of the transformed timeseries
