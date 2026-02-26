# !fa-upload Importing records

**Import** in ODMF means to add records to [timeseries datasets](../datasets). As your data source varies, ODMF provides several methods for importing data.
Most import methods need alerady existing datasets. Datasets are created with the "new dataset" button in the dataset list or imported from a table.

## Import methods overview

- help:import/direct : Enter values directly in a dataset from the web site. For single manual measurements
- help:import/log : Import values and logs from a templated Excel file, with extensive error checking. Ideal to import offline notes from Excel
- help:import/lab : Import values from tabular data using a description file. Eg. for output from lab analyzers or other predefined templates
- help:import/conf : Use this method for tabular output from loggers / field sensors 
- help:import/record : For large prepared data tables

# Import method selection guide

## For manual measurements

### Single records with online access

If you need to write down a single record (or very few) and you have online access, use **direct input**. Goto the [!fa-clipboard -dataset page](/dataset) and navigate to the dataset, you want to add the record. Click on add record and add your value. For tricks to make this convinient see: help:import/direct

### A few records from offline notes

If you have a field computer but no online access, note your records in an excel sheet with a special structure, to use help:import/log  into **existing datasets**. Note that the **log-import** allows also the import of log messages and provides extensive sanity checks.

## For sensors / instruments with tabular output

If your sensors produces many values in a uniform way, like eg. 
soilmoisture sensors with soilmoisture and soiltemperature data that is
logged by a recorder, you can use .conf-files to describe the files
produced by the logger. This method can create new dataset by itself during the import. Refer to the help:import/conf.

## For records from fixed table formats, eg. output from a lab analyzer

If your data source produces data for several datasets in a fixed template, the **lab import**
can be a good choice. This could be the output of a lab analyzer, or an already defined template for routine measurements.
See help:import/lab

## Import large prepared datasets with a record table

If you can design a workflow (eg. in Python or R) to assemble measurements in a predefined form, you can create
a table that is exactly like the the internal help:import/record table to import data into **existing datasets**. The tabular format can be Excel, CSV or Parquet (recommended). The method assumes your workflow does check your data.

# What do I need to do before I can import data?

Make sure that all sites (help: datasets/site), at which you recorded your data, all valuetypes (help: datasets/valuetype) 
you recorded, all instruments you used (help: datasets/instrument), and (for direct import, log-import and lab-import), 
the corresponding dataset (help: datasets) have been created in ODMF.

