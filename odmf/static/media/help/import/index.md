# Importing records

There are several ways to get data into the structured timeseries system.

- **Direct input** (for a single record)
- Import a list of records from an excel file with a special structure (so called **log import**) into exisiting datasets
- Import a raw csv or excel file from a logger or other measurement intstrument using an extra file to describe the file organization (so called .conf-file, the **conf-import**)
- You want to write a python script to upload data automatically, use the **API-import**

## Which method is the right for me?

The methods are described in detail below.

### For manual measurements:
If you need to write down a single record (or very few) and you have online access, use **direct input**. 
If you have a field computer but no online access, note your records in an excel sheet with a special structure, to perform the **log-import**.

### For sensors / instruments with tabular output

If your sensors produces many values in a uniform way, like eg. 
soilmoisture sensors with soilmoisture and soiltemperature data that is
logged by a recorder, you can use .conf-files to describe the files
produced by the logger. Refer to the **conf-import**, but it is best to
get this a first time explained, but someone with experience in the 
field.

If you are a Python programmer, you can very simply write a program 
that creates a pandas dataframe in a special format and send the
dataframe directly to the ODMF database via the **API** using the
Python package
[odmfclient](https://github.com/jlu-ilr-hydro/odmfclient)
[![PyPI](https://img.shields.io/pypi/v/odmfclient?logo=pypi)](https://pypi.org/project/odmfclient/)

# Direct import

Goto the [!fa-clipboard -dataset page](/dataset) and navigate to the dataset, you want to add the record. Goto record --> add record, put in
date, time and value, and you are done.

# Log-Import

You can write down your findings in a specially formatted excel file (or transform your data in that format) to import records
and log messages from the field. Create an excel file that has the following column names in the first row, no other header row is allowed:

- time (actual date and time, _required_, **must** be a real date/time format)
- site (site id, _required_)
- dataset (dataset id, _optional_)
- value (the actual value in the unit of the dataset, _optional_)
- logtype (the type of message, _optional_)
- message (a message, _optional_)

Each row in the file is either imported as a record, (dataset id and value must be provided), or as a log message for the 
site (logtype and message are required). A record can get an extra comment with the message. You should find a 
template here file:template/import-template-log.xlsx folder

When you open the file, a button [!fa-upload log] is there, to start the import. 

#### NOTE: 

Only completely correct files can be used for import. If any row is not suitable, you **MUST** correct or delete that row for import. Because **log import** can scatter values around in the database, errors are very difficult to correct.
#### BE CAREFUL!

# Conf-Import

Data-Loggers usually create tabular data for a number of sensors at the same site. One can create .conf-files 
(in [INI-format](https://en.wikipedia.org/wiki/INI_file)), that describe the tabular format of the data logger.
The .conf file is either in the same directory as the data file or in a directory above. Excel and CSV-Files with
a .conf file in the same directory or in a directory above can be imported. The .conf file consists of a general section
describing the data format and sections for each column that should be imported. Each data column creates a new dataset,
except the column is declared to append to an existing dataset.



