# lab-import

- for small (<1000) rows, because it is slow
- repeated imports of the same format
- files contain data for multiple sites

!!! alert alert-info "Table of contents"
    [TOC]

Analysis carried out in a lab usually result in Excel files with a somewhat encoded sample name with multiple values per sample. If multiple values for the same dataset and the same time exist, this method is building the mean value
The samples in one batch can origin from multiple sites. Such files can be described with `.labimport` file, that follow the [YAML](https://yaml.org/) format. This import 
is ment for rather small datafiles, like a couple of hundred rows, as it is rather slow. 



The `.labimport` file consists of two main parts: 
1. The description of the **file format** eg. how to interprete the file as a table
2. the description of **each column**. For each value in the table a fitting **dataset must exist**. 
   If you create new datasets, the start and end must be set to a timerange inside the time range covered by the data.

Creating a `.labimport` file is difficult and should be mentored by a person with programming experience.

## File format

The lab import uses the file reading capacity of the Python library [pandas](https://pandas.pydata.org/docs/reference/io.html).
The keyword driver is the pandas function to read the tabular data, and driver-options are the keywords of that function.
If you know how to load tables in `R` - this is quite similar.

### Common driver functions

#### [read_excel](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html)

Reads excel files (.xlsx, .xlsb, .xls). Typical keywords are `sheet_name` and `index_col`. If your data is in the only 
worksheet and all data is well formatted, you do not need any options. If you have multiple header lines use `skiprows`
to skip those.

#### [read_csv](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html)

Reads tabular text files with a seperator. Default is `,` as the variable seperator and `.` as the
decimal sign. This can be changed with `sep: ";"` and `decimal: ","`, the quotes are important here.
If you have date/time column, make sure to use the date parsing options of read_csv with the keywords date_format 
and parse_dates, as described in the link. If the date of the sample can be inferred from the sample name, this is not necessary.

#### [read_parquet](https://pandas.pydata.org/docs/reference/api/pandas.read_parquet.html)

Read tabular data in the Apache parquet format. The parquet format is not that well known, but fast, reliable and compact.
Best suited for datasets created in Python or R.

#### General options

`skiprows`, `nrow`, `usecols` and `skipfooter` are keywords that can be used in every table format to ignore
unnecessary data. `na_values` is used to name conventions of N/A-Values in the file. If the file does not have column headers, 
or the column headers are in the  skipped rows, please indicate it with `header: null`. In that case, you refer to the columns by its position (starting with 0) or you can give column names with a list: `names: [A, B, C, D]`

## aggregate

In many cases, samples are measured more than once to get a more reliable result. With the aggregate keyword, values for
duplicated samples can be aggregated, usually as mean value. If no aggregation is given, the values will be imported as duplicate
records.

## columns

Each column is addressed by its name or by postion. The columns are treated differently by its type. The data file can contain more columns than
specified in the .labimport file, which will be ignored during the import.

### type: value

This is the standard type, and there can be multiple value columns in a file. Value columns contain the value and 
the valuetype (as id number, eg 1 for Air Temperature in °C). To scale values for measurements for units a factor
can be given (optional).

### type: time [optional]

If a column with the time of sampling is given, that column is marked as `type: time`. A well formatted excel column
is directly understood as as a date/time field, csv files often needs a translation with the file format (see above).
Do not include a time column, if the time should be inferred from the sample name.

### type: dataset [optional]

A column with the target dataset id. The dataset is often inferred from additional information (site, level, time, valuetype), 
and then no dataset column is given. The additional information can be given in explicit columns or can be encoded in the
sample name. If the dataset is also encoded in the sample, this column is taken first 

### type: site [optional]

A column with the site of sampling. If the dataset is given or if the site is inferred from the sample, do not specify a site column

### type: level [optional]

A column indicating the level (eg. depth) of a sampling. If the dataset is given or the level is encoded in the sample, this is not necessary

### type: sample [optional]

This is a very complex type and can be used to derive metadata like site, time, level from a sample name (this is called parsing). 
If additional columns for this information exists already, use the type `samplename`, then no parsing takes place and the
name is only copied. This is not easy - if you are no programmer, you might need help from someone with programming knowledge

The sample column contains a regex-pattern to describe the content of the sample name. 
[Regular expression (regex)](https://en.wikipedia.org/wiki/Regular_expression) is
a mini language to find parts in a text. Groups are in parenthesis and numbers, alphanumeric characters etc can be used 
to identifiy the parts. You can test a regex beforehand here: https://regex101.com/. The pattern in the example file

`(\w+?)_([0-9\.]+_[0-9]+\:[0-9]+)_?([-+]?[0-9\.]+)?`

means there are three groups, each seperated with underscore

1) (\w+?)
2) ([0-9\.]+_[0-9]+\:[0-9]+)
3) ([-+]?[0-9\.]+)?

- The first group consists of some characters (\w), at least one but stopping as early as possible (+?). 
- The second group consists of numbers and stops [0-9\.]+, an underscore _, more numbers [0-9]+,
  a colon \: and numbers again [0-9]+. This regex matches dates, eg. 4.12.2024_12:54
- The third group is optional (? in the end) and consists of numbers and stops [0-9\.]+ eventually with a
  sign ([-+]?). As the group is optional, the leading underscore is also optional (_?)

This pattern matches sample names like F1_4.12.2023_12:54_60 and can mean a sample take at site F1 in December 4th 2023
at 12:54 in a depth of 60 cm.

To derive the site, date and level, the parts must be translated. The date can be translated by the group number 
(in the example 2) and the date format, in the example %d.%m.%Y_%H:%M using [Pythons notation of date formats](https://docs.python.org/3/library/datetime.html#format-codes)
(which is used by a number of other programming languages). The site needs also the right group (in the example 1),
and you can add a map to translate site names into site id's of the database. If your data uses already the official
site id's, that map can be left out.

The level is derived from group 3 in our example and can be transformed with a factor. In the example the level 60 for
60cm depth, we use the factor -0.01 to translate it as depth (negative number) and in m. '60' -> -0.6.

If additional markers are needed, please [post an issue in github](https://github.com/jlu-ilr-hydro/odmf/issues)

### type: row-factor

#### NOTE: Not implemented yet, do not use

If the samples have been diluted, the row-factor in this column can be used to scale all values in that row. 

## steps towards the import

Upload your data to a folder within the downloads section of ODMF. Only data that can be imported with the same .labimport
file can be in the same folder. Create the labimport file according to the examples below and the information above in an IDE 
(e.g. visual studio code with YAMl plugin) or text editor (e.g. notepad) and save it with the extension .labimport 
(select all files as type and enter something.labimport as filename). Upload the labimport file into the same folder 
(or a higher order folder) as your data. Click the data file in ODMF and click the "lab" button on the top right. 
If unexpected errors or warnings are displayed or you are unsure whether you did everything correctly, contact an experience person, 
because after import errors are difficult to correct. When you are sure that everything is fine, click the import button.

# Example 1

This is an example for an excel file with the data in `Table 1` and the named columns `Sample`, `N_NO3` and `N_NH4`.
The sample includes a site name (not a site id!), the sampling time and eventually the level. The site names are
mapped to numeric site ids in the database.

The table may look like:

!!! table table-striped "Example table"
    | Sample               | N_NO3 | N_NH4 | remarks
    |----------------------|-------|-------|--------
    | F1_6.5.2023_11:15_60 |2.5785|0.9456  | Site: F1 (#137), time: May 6th, 2023 in 60cm depth
    | B1_7.5.2023_12:45    |2.5785|0.9456  | Site: B1 (#123), time: May 7th, 2023 no level

Note that the date/time is encoded in the sample with a 4-digit year (6.5.2023_11:15 => Myy 6th, 2023, 11:15) and uses
as a date format `%d.%m.%Y_%H:%M`. The upper case `%Y` is the 4-digit year. [More about date formats...](https://docs.python.org/3/library/datetime.html#format-codes)


## `.labimport` file
```
driver: read_excel   # pandas function to read the table. See: https://pandas.pydata.org/docs/reference/io.html
driver-options:  # keyword args for the pandas function. See: https://pandas.pydata.org/docs/reference/io.html
    sheet_name: Table 1   # Sheet name

columns:                 # Description of each column, use the column name as object name
    Sample:              # Name of the sample column, in this case Sample. You can also
        type: sample     # Necessary to understand column as sample names
        pattern: (\w+?)_([0-9\.]+_[0-9]+\:[0-9]+)_?(?:[-+]?[0-9\.]+)  
        site:
            group: 1
            map:
                F1: 137
                F2: 147
                F3: 201
                B1: 123
                B2: 138
                B3: 203
        time:
            group: 2
            format: "%d.%m.%Y_%H:%M"
        level:
            group: 3
            factor: -0.01
    N_NO3:  # The name
        type: value
        factor: 1.0
        valuetype: 3
    N_NH4:
        type: value
        factor: 14.3
        valuetype: 4
```

# Example 2

This example is for data produced by an ioc chromatograph. There are multiple header rows to be skipped. The sample
name contains the site id (as in the database, no translation needed), and the sampling time (seperated by _).
Since the column headers are skipped, new column names are assigned in the .labimport file. Every sample is measured 
twice, for higher accuracy. The duplicated measurements should be aggregated as the mean value.

!!! table table-striped "Example table"
    | Sample | Name             | Amount | Amount | Amount | Amount | Amount | Amount | Amount
    |--------|------------------|--------|--------|--------|--------|--------|--------|-----
    | No.|                  | mg/l  |mg/l| mg/lmg/l | mg/l   | mg/l | mg/l| mg/l
    | |                  | Fl   |Cl|No2| Br    |No3|SO4|PO4
    || 13_030321_10:30 |0.1187|19.13|n.a.|        |19.798|44.2271|0.6177
    | | 13_030321_10:30  | 0.1165| 18.7297| n.a.| | 19.4155| 43.516| 0.6174
    | | 19_030321_10:42  | 0.1165           | 24.7767| n.a.| | 16.731| 26.7428| 0.6313
    | | 19_030321_10:42  | 0.1213           | 25.5579| n.a.| | 17.2184| 27.4383| 0.6143
    | | 134_030321_11:28 | 0.1544           | 5.9271| n.a.| | 18.0146| 11.4721| n.a.

Note that the date/time is encoded in the sample with a 2-digit year (030321_10:30 => March 3rd, 2021, 10:30) and uses
as a date format `%d%m%y_%H:%M`. The lower case `%y` is the 2-digit year. [More about date formats...](https://docs.python.org/3/library/datetime.html#format-codes)

## `.labimport` file

```
driver: read_excel   # pandas function to read the table. See: https://pandas.pydata.org/docs/reference/io.html
aggregate: mean
driver-options:
    skiprows: 4   # skip the for header rows
    header: null  # do not expect any column names (they are skipped)
    na_values: ['n.a.', 'N/A']    #  Value to understand as no-data
    names: [_, sample, F, Cl, NO2, Br, NO3, SO4, PO4]

columns:                 # Description of each column, use the column name as object name
    sample:              # Name of the sample column
        type: sample     # Necessary to understand column as sample names
        pattern: ([0-9]+)_([0-9\.]+_[0-9]+\:[0-9]+)
        site:
            group: 1
        time:
            group: 2
            format: "%d%m%y_%H:%M"
    F:  # Floride
        type: value
        valuetype: 10
    Cl:  # Chloride
        type: value
        valuetype: 11
    NO2: # No2
        type: value
        valuetype: 12
        factor: 0.3032   # conversion in NO2-N
    Br: # Br
        type: value
        valuetype: 13
    NO3: # No3
        type: value
        valuetype: 14
        factor: 0.2259   # conversion to NO3-N
    SO4: # SO4
        type: value
        valuetype: 15
        factor: 0.334    # conversion to SO4-S
    PO4: # PO4
        type: value
        valuetype: 16
        factor: 0.3261   # conversion to PO4-P
```
