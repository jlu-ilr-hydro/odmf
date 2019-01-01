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

Further explanation on the code structure and software components in [development chapter](development.html).
(Architecture/ Components) Link to Development
Mentales Gerüst (optional)


* Schwingbach FMC (Overall)

![Picture of the ODMF architecture]( ../../images/schwingbach-architecture.svg "ODMF architecture")

## CUAHSI WaterOneFlow Interface

### How does it work

The important elements are HydroServerLite (a) which implements the WaterOneFlow interface,
the PostgreSQL database (b) which fullfills the ODM schema, via SQL views. Additionally there
is the ODMF (c) server, which is mainly used to write data into the database.

![FMC diagram of whole system]( ../../images/fmc-cuahsi.png "Different components (FMC diagram)")

1. A request is send to the HydroServer.

2. The responses are build of information from one ore more views, which the server middleware will compose.

3. The middleware calls request the database for the respective views.

Data writes from the import mechanism from the ODMF server are an ongoing process and can result in an hourly changing
data base.

![UML transaction diagram]( ../../images/fmc-wof-views-2.png "UML transactions from request (FMC Diagram)")

### Implementation

Details on this topic are written down in [development chapter](development.html#wateroneflow)

### Configuration

The configuration of the WaterOneFlow interface can be found in the [installation](installation.html#wateroneflow) chapter.
