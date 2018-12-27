Database schema
********************

The schwingbach database schema is build around the central *dataset* table.

.. image:: ../../images/schwingbach.png
   :alt: Picture of database schema schwingbach

The schwingbach database schema definition is a subset of the
Observation Data Model (ODM_) specification.
developed by the organization `CUAHSI <https://cuahsi.org>`_.

A extended version of the schwingbach schema (:ref:`documentation <odm-extension>`)
is enhanced by SQL tables, views and triggers to make use of the
`HydroServer <http://hydroserver.cuahsi.org/Account/Login>`_ `Lite <https://github.com/CUAHSI/HydroServerLite>`_
to provide the `WaterOneFlow <http://his.cuahsi.org/wofws.html>`_ interface.

For an complete overview of the original version, ODM extension and its
differences `see PDF <http://fb09-pasig.umwelt.uni-giessen.de/>`_.

**Table** *dataset*
===================
.. _schema-dataset:

A dataset entry has 0-n :ref:`transformed_timeseries <table-trans_timeseries>`
attached to it. And it should hold 1-* records.

+-----------+-----------------------------------------------------------+
| Attribute | Definition                                                |
+===========+===========================================================+
| type      | 'timeseries' or 'transformed_timeseries'                  |
|           |                                                           |
|           | See :ref:`transformed_timeseries <table-trans_timeseries>`|
+-----------+-----------------------------------------------------------+
| access    | integer 0-4                                               |
|           |                                                           |
|           | See :ref:`Person access levels <access_levels>`           |
|           | for further information                                   |
+-----------+-----------------------------------------------------------+



**dataset.type** *transformed_timeseries*
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _table-trans_timeseries:

*Note*: A transformed timeseries has an entry in the dataset table, but won't
have any entries in ``record`` attached to it.

**Table** *transforms*
=======================

Consists of two main columns, ``source`` and ``target``. So it can be read as
``source`` transforms into ``target``. Third column ``automatic_added`` is set
``true``, when the ``trans_dataset_id`` keyword in the config file is used.

**Table** *person*
===================

**Access levels**
^^^^^^^^^^^^^^^^^^
.. _access_levels:

Access levels define the access on datasets and their records, wheter the users
intention is to read or to write. The levels have an integer range from 0 to 4.

* **Level 0:** Guest
* **Level 1:** Editor
* **Level 2:** Logger
* **Level 3:** Supervisor
* **Level 4:** Admin



ODM DDL extension
^^^^^^^^^^^^^^^^^^
.. _odm-extension:

**Tables**

Most tables are part of the *ControlledVocabulary* which defines a shared definition
of all ODM databases. See the ODM_ design specs or the master controlled vocabulary
`website <http://his.cuahsi.org/mastercvreg/cv11.aspx>`_ for more information.

**Views**

* **seriescatalog**: Holds all ``odm.series`` of ``odm.datavalues``. To build the
  analogy to Schwingbach. All ``sbo.dataset`` s grouped by its ``site``, ``valuetype``,
  ``source``, ``quality``, ``project`` and ``datacollectionmethod``.

\

  - *except*:

    * dataset.type = 'transformed_timeseries' (at the moment)
    * dataset.access = 0 (Only guestlevel, **NOT** higher)
    * valuetype.id = 30 (see variables for more information)

* **variables**: Provides the content defined by ``odm.variables``. Therefore it
  fetches it out of ``sbo.valuetype`` and ``sbo.dataset``.

\
  - *excludes* (Note this also affects the code of seriescatalog):

    * specific valuetypes that are not compatible with odm: ATM the following valuetypes:

      - 30 - water amount

**Materialized Views**

There are views that are updated or materialized by a daily cronjob, to keep
the data recent.

  * ``/home/gh1961/schwingbach/odm/bin/refresh_series.sh`` for `sbo.series` for the valuecount data of series_catalog.

Differences that affect the implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* ``siteid`` is an number attribute in all extending usages and not as the design document of ODM 1.1 states, a string

.. _ODM: https://www.cuahsi.org/uploads/pages/img/ODM1.1DesignSpecifications_.pdf
