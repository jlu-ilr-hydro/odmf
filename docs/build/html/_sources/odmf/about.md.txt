# What is ODMF
Who can use it etc.pp.

TBD by Philipp

## Features of ODMF

* Upload measurement data for future use
* Data is persisted in an Postgres database in special schema structure
* Analyze data via the platform or export in csv or plot format
* Organization of different user roles within the online system
* Augment measurement data gathered from the work in the field via meta data, such as logs and pictures
* Integration of Google Maps UI panel

Also it can be integrated into the [CUAHSI](https://www.cuahsi.org) network and used with the tools provided by
the CUAHSI organization. For example to inspect or download data via the [Data.CUAHSI](https://data.cuahsi.org) page.

## Development

Further explanation of the code structure and the software components can be found in the [development chapter](development.html).
(Architecture/ Components) Link to Development
Mentales Gerüst (optional)


* Schwingbach FMC (Overall)

![Picture of the ODMF architecture]( ../../images/schwingbach-architecture.svg "ODMF architecture")

## CUAHSI WaterOneFlow Interface

### How does it work

The important elements, to understand the interface are the HydroServerLite (a), which implements the WaterOneFlow
interface, the PostgreSQL database (b) which fullfills the ODM schema via SQL views and additionally there
is the ODMF (c) server, which is mainly used to write data into the database.

![FMC diagram of whole system]( ../../images/fmc-cuahsi.png "Different components (FMC diagram)")

1. A request is send the HydroServer instance. This request can be one of the methods of the endpoint, e.g.
   `GetSites` which will return all published [Site](views.html#sites) objects.

2. The XML response is build out calls to PHP methods [(see implementation chapter)](#implementation), which will fetch
   data from one or more tables of the database. In the case of the Schwingbach project, instead of SQL tables, SQL  
   views are in use.

3. The database then uses the corresponding tables of the respective views to provide the data.

Data writes from the import mechanism from the ODMF server are an ongoing process and can result in an hourly changing
data base.

![UML transaction diagram]( ../../images/fmc-wof-views-2.png "UML transactions from request (FMC Diagram)")

### Implementation

Details on this topic are written down in [development chapter](development.html#wateroneflow)

### Configuration

The configuration of the WaterOneFlow interface can be found in the [installation](installation.html#wateroneflow) chapter.
