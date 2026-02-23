# !fa-upload Importing records

**Import** in ODMF means to add records to [timeseries datasets](../datasets). Most import methods need alerady existing datasets. Datasets are created with the "new dataset" button in the dataset list or imported from a table.

- **Direct input** (for a single record)
- Import a list of records from an excel file with a special structure into exisiting datasets, see help:import/log
- Import a raw csv or excel file for one site from a logger or other measurement instrument using an extra file to describe the file organization: so called .conf-file, see help:import/conf
- Import a csv or excel file with few (<1000) records for several sites (e.g.result lab analysis or handheld sensor measurements): so called .labimport file, see help:import/lab
- Import large prepared datalists from a workflow help:import/record

## Which method is the right for me?

The methods are described in detail below.

### For manual measurements

If you need to write down a single record (or very few) and you have online access, use **direct input**. 
If you have a field computer but no online access, note your records in an excel sheet with a special structure, to use help:import/log to import into **existing datasets**. Note that the **log-import** allows also the import of log messages and provides extensive sanity checks.

### Import large prepared datasets with a record table

If you can design a workflow (eg. in Python or R) to assemble measurements in a predefined form, you can create
a table that is exactly like the the internal help:import/record table to import data into **existing datasets**. The tabular format can be Excel, CSV or Parquet (recommended). The method assumes your workflow applies sanity checks etc. 

### For sensors / instruments with tabular output

If your sensors produces many values in a uniform way, like eg. 
soilmoisture sensors with soilmoisture and soiltemperature data that is
logged by a recorder, you can use .conf-files to describe the files
produced by the logger. Refer to the help:import/conf.

### For measurements recorded for several sites within the same table (e.g. excel output of lab analyser)

If you have the possibility to define the structure of the table in the simple way required by the **log import**,
you can use this. If you have a different structure and/or a combined column for site/date/level, the **lab import**
can be a good choice.

## What do I need to do before I can import data?

Make sure that all sites (help: datasets/site), at which you recorded your data, all valuetypes (help: datasets/valuetype) 
you recorded, all instruments you used (help: datasets/instrument), and (for direct import, log-import and lab-import), 
the corresponding dataset (help: datasets) have been created in ODMF.

# Direct import

Goto the [!fa-clipboard -dataset page](/dataset) and navigate to the dataset, you want to add the record. Goto record --> add record, put in
date, time and value, and you are done.

# help:import/log

You can write down your findings in a specially formatted excel file (or transform your data in that format) to import records
and log messages from the field to **append existing datasets**.

more: help:import/log

# help:import/conf

Data-Loggers usually create tabular data for a number of sensors at the same site. One can create .conf-files 
(in [INI-format](https://en.wikipedia.org/wiki/INI_file)), that describe the tabular format of the data logger.
The .conf file is either in the same directory as the data file or in a directory above. Excel and CSV-Files with
a .conf file in the same directory or in a directory above can be imported. The .conf file consists of a general section
describing the data format and sections for each column that should be imported. Each data column **creates a new dataset**,
except the column is declared to append to an existing dataset.

more: help:import/conf

# help:import/lab

Lab analysis devices usually produce result lists with a mangled sample name and several columns of results. With an
`.labimport` file in [yaml format](https://en.wikipedia.org/wiki/YAML), the file structure and a method how to unmangle
the sample name can be provided. This is not simple and one should seek help from a person who knows a bit about 
[RegEx](https://en.wikipedia.org/wiki/Regular_expression). 

 more: help:import/lab

