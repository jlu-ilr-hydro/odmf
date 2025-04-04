# Importing records

There are several ways to get data into the structured timeseries system.

- **Direct input** (for a single record)
- Import a list of records from an excel file with a special structure (so called **log import**) into exisiting datasets
- Import a raw csv or excel file from a logger or other measurement intstrument using an extra file to describe the file organization (so called .conf-file, the **conf-import**)
- You want to write a python script to upload data automatically, use the [odmfclient](https://github.com/jlu-ilr-hydro/odmfclient)

## Which method is the right for me?

The methods are described in detail below.

### For manual measurements:
If you need to write down a single record (or very few) and you have online access, use **direct input**. 
If you have a field computer but no online access, note your records in an excel sheet with a special structure, to use 
help:import/log.

### For sensors / instruments with tabular output

If your sensors produces many values in a uniform way, like eg. 
soilmoisture sensors with soilmoisture and soiltemperature data that is
logged by a recorder, you can use .conf-files to describe the files
produced by the logger. Refer to the help:import/conf.

If you are a Python programmer, you can very simply write a program 
that creates a pandas dataframe in a special format and send the
dataframe directly to the ODMF database via the **API** using the
Python package
[odmfclient](https://github.com/jlu-ilr-hydro/odmfclient)
[![PyPI](https://img.shields.io/pypi/v/odmfclient?logo=pypi)](https://pypi.org/project/odmfclient/)

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

