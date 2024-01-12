# .conf files

Data-Loggers usually create tabular data for a number of sensors at the same site. One can create .conf-files 
(in [INI-format](https://en.wikipedia.org/wiki/INI_file)), that describe the tabular format of the data logger.
The .conf file is either in the same directory as the data file or in a directory above. Excel and CSV-Files with
a .conf file in the same directory or in a directory above can be imported. The .conf file consists of a general section
describing the data format and sections for each column that should be imported. Each data column creates a new dataset,
except the column is declared to append to an existing dataset.


### Configuration files

The import saves the measured data into a structured database schema. Unfortunately all measurement output of
instruments in the field have different structures. Therefore a solution is that the user has to provide a configuration
file, for each instrument-specific structure. A configuration file specify a key-value pairs-like mapping of
instruments data schema that's about to be written into the database schema.
The pair of keywords and their values (full list see below) have to be consistent, so the server can import the measured data.

The configuration file is a definition of the import process of all files in a directory.
The concept of a configuration file assumes, that in general each data files import information can be covered by a
description and multiple column descriptions.
A `import description` contains information that depict the import on file level and the `column descriptions` on column level.
All descriptions of the configuration, are made by the user once, contain all information to automatically import the data of multiple files.
So the user is able to omit most of the configuration of future imports for data files in this folder.


#### Import description keywords

* **instrument** *int*: The database id from the instrument that produces that file. Is Mandatory and has no default.
* **skiplines** *int*: The amount of lines, which the import algorithm will skip, before reading data rows. Is optional
  and default ist 0.
* **delimiter** *str*: Symbol used to separate the columns. Is Optional and default is `,`.
* **decimalpoint** *str*: Symbol used to separate decimal place. Is Optional and defalt is `.`.
* **dateformat** *str*: Format of the date in the **datecolumns**. Default is `%d/%m/%Y %H:%M:%S`
* **datecolumns** *list or int*: Number of column(s), which contains the date in **dateformat**, first column is 1.

* **project** *str*: Links to project from database
* **timezone** *str*: In pytz format
* **nodata** *list*: list of values that don't represent valid data. E.g. ['NaN']

* **worksheet** *int*: *XlsImport only* The position of the worksheet of an excel file. Optional and default is the first (1)


#### Column description keywords

* **name** *str*: Name of the column and name of the dataset. Also name of the type of data, as defined for the [value type number](wiki.html#valuetypes)
* **column** *int*: Position of the column in the file. Note: The first column is 0
* **valuetype** *int*: Id of the value type stored in the column.
* **factor** *float*: If the units of the column and the valuetype differ, use factor for conversion
* **comment** *str*: The new dataset can be commented by this comment
* **difference** *str*: If True, the stored values will be the difference to the value of the last row
* **minvalue** *float*: This is the allowed lowest value (not converted). Lower values will not be imported
* **maxvalue** *float*: This is the allowed highest value. Higher values will not be converted
* **append** *int*: For automatic import, append to this datasetid
* **level** *float*: Level property of the dataset. Use this for Instruments measuring at one site in different depth
* **access** *int*: Access property of the dataset. See [wiki](wiki.html#access-levels) for a list of all access levels.

* **ds_column** *int*: *ManualMeasurementImport only* explicit dataset for the uploading column
* **sample_mapping** *dict*: *ManualMeasurements and LogImport only* Special keyword for manual measurements to map
  labcodes to site ids. E.g. `{'keywords': 'value'}`

If no `{*}.conf` file is present in a folder, the parent directory is searched for a configuration file.

There should be only one configuration file per folder.

### Example

The ini-file consists of `[sesction]` rows, that start a new section. In a section are the key/value pairs
`key = value`. Comment lines (ignored by the program) start with a semicolon `;`, comments can also
start after the key/value pair.

```
[instrument name]
instrument = 1
skiplines = 3
delimiter = ,
decimalpoint = .
dateformat = %d.%m.%Y %H:%M
datecolumns = 0
encoding=latin1

[Name of column 1]
; 0 based column number
column = 1
; name of the field, will become name of the dataset
name = soil moisture Port 1
; soil moisture in m3/m3
valuetype = 2
; factor for unit conversion
factor = 1.0
comment = 5TM Sensor
; lowest allowed value in m3/m3, use this for nodata values
minvalue = 0
; highest allowed value in m3/m3, use this for nodata values
maxvalue = 1
;depth of the installed Sensor in m
level=-0.1

[Name of column 2 1]
; 0 based column number
column = 2
; name of the field, will become name of the dataset
name = soil temperature Port 1
; soil temperature in degC
valuetype = 3
; factor for unit conversion
factor = 1.0
comment = 5TM Sensor
; lowest allowed value in m3/m3, use this for nodata values
minvalue = -50
; highest allowed value in m3/m3, use this for nodata values
maxvalue = 100
;depth of the installed Sensor in m
level=-0.1

```