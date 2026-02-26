# !fa-clipboard Datasets

Datasets are the core feature of the structured database in ODMF. A dataset is a collection of metadata:

- [!fa-ruler What is measured?](valuetype) 
- !fa-user Who did it? Person 
- [!fa-map-location Where is the data located?](site), Level  
- [!fa-thermometer-half How is it measured?](instrument) 
- !fa-star What is the data quality? 
- !fa-key Who can use the data? 
- !fa-clock When?

## Dataset types

### Timeseries

The standard type, useful numerical values at a site. The timeseries dataset owns records, that can be plotted, calibrated and transformed. Timeseries datasets are created with the "new dataset" button or via tabular import.

### File-dataset

File datasets have the same meta data as timeseries, but never have record. Instead, they have a link to a file that contains the data of the
dataset. This data can have any form, qualitative data, arrays, images, text etc, as long as the value type can be definetly described. Use long term open formats for the files. Data from file datasets cannot be plotted and mixed with other data. If your data has a form of numerical timeseries, import as records (see: help:import) is stongly encouraged for plotting, aggregation, interpolation and mixing. File datasets are created from an uploaded file using the !fa-clipboard !fa-plus button in the  help:file-manager .


### Transformed timeseries

If you want to derive data from measured timeseries, you can apply any function to timeseries to create a transformation as an additional form. Until now, only one valuetype can be transformed. Transformed timeseries are created from the source timeseries with the [$f(x)$ transform] button.

Example: you have a timeseries dataset showing the level of a slurry tank below the edge in m and you want to have the information of stored m³. If the base area is 10m² and the storage height is 3m, the transformation would be 

$$V [m^3] = 10 [m^2] \cdot (3 [m] - x [m]) $$

### Log book entries (logs) for qualitative data

To record qualitative data, like event descriptions without numeric data or with a complex data structure, you are
going to add [log-entries](log) to sites

## Dataset properties

![dataset](dataset.svg)

[Valuetype](valuetype), [location](site) and [instrument/ data source](instrument) are described on their subpages.
The level is a vertical offset of the given location, eg. if you have a soil moisture sensor profile in 10, 30 and 60 cm
depth, tag the datasets with the levels in m below ground as -0.1, -0.3 and -0.6 respectively (can be left empty).

Please indicate the data quality as one of the possible values: 0: raw, 1: formal checked, 2: quality checked, 
3: calibrated, 4: derived value

The start and end time is adjusted when adding records.

The access level is used to prevent users of the database to see your data, if they are from another project or
do not have enough privileges to see the data: 0: public dataset, 1: only known users and project members 
(enter the project id of your project in the project field), 2: only users with editing privileges, 
3: only employees and data managers, 4: only administrators.
ODMF is not a repository - data in the database is not licenced to be used in any publication. 
You must always contact the data owner prior to usage in a publication. It is best practice to publish data 
in a repository like [zenodo.org](https://zenodo.org) and let your colleagues cite that data with a doi.

The filename should contain a link to where the raw data or information about how the data imported from
a datalogger is stored in ODMF. The comment section can contain e.g. a device id of the data logger, the crop
species which was sampled, links to a protocols how the measurements where taken, 
important information how to use the data (e.g. to be aware of repeated measurements), ...

If applicable, you can add a calibration regression by its offset and slope, otherwise keep the defaults.

## How many datasets do I need?

This is heavily depending on your use case. See [examples](dataset-examples). New datasets should be created as soon as
anything relevant changed during the time series of one valuetype (e.g. a new instrument is used, 
a different crop is grown,...).

## How do I create new datasets?

For adding one or few datasets, click the "new dataset" button on the !fa-clipboard page and enter the metadata.
If you have many similar datasets, for example when the same measurement is taken at multiple sites, you can create
an excel list of datasets import it. Export a dataset list to get a template. Delete the "id" column 
as the ids will be given automatically. The columns measured_by, start, end, type, level and comment are optional.
A table describing all columns of the dataset import excel sheet can be found by clicking "import datasets".
