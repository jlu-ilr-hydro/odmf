# !fa-upload Importing records

**Import** in ODMF means to add records to [timeseries datasets](../datasets). As your data source varies, ODMF provides several methods for importing data.
Most import methods need alerady existing datasets. Datasets are created with the "new dataset" button in the dataset list or imported from a table. 

## For manual measurements

### Using direct input

If you need to write down a single record (or very few) and you have online access, use **direct input**. Goto the [!fa-clipboard -dataset page](/dataset) and navigate to the dataset, you want to add the record. Goto record --> add record, put in date, time and value, and you are done.

### Using log-import Excel template

If you have a field computer but no online access, note your records in an excel sheet with a special structure, to use help:import/log  into **existing datasets**. Note that the **log-import** allows also the import of log messages and provides extensive sanity checks.

## Import large prepared datasets with a record table

If you can design a workflow (eg. in Python or R) to assemble measurements in a predefined form, you can create
a table that is exactly like the the internal help:import/record table to import data into **existing datasets**. The tabular format can be Excel, CSV or Parquet (recommended). The method assumes your workflow does check your data.

## For sensors / instruments with tabular output

If your sensors produces many values in a uniform way, like eg. 
soilmoisture sensors with soilmoisture and soiltemperature data that is
logged by a recorder, you can use .conf-files to describe the files
produced by the logger. Refer to the help:import/conf.

## For measurements recorded for several sites within the same table (e.g. excel output of lab analyser)

If you have the possibility to define the structure of the table in the simple way required by the **log import**,
you can use this. If you have a different structure and/or a combined column for site/date/level, the **lab import**
can be a good choice. See help:import/lab

# What do I need to do before I can import data?

Make sure that all sites (help: datasets/site), at which you recorded your data, all valuetypes (help: datasets/valuetype) 
you recorded, all instruments you used (help: datasets/instrument), and (for direct import, log-import and lab-import), 
the corresponding dataset (help: datasets) have been created in ODMF.

