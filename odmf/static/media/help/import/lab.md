# lab-import

- for small (<1000) rows, because it is slow
- repeated imports of the same format
- files contain data for multiple sites


Analysis carried out in a lab usually result in Excel files with a somewhat encoded sample name with multiple values per sample. If multiple values for the same dataset and the same time exist, this method is building the mean value
The samples in one batch can origin from multiple sites. Such files can be described with `.labimport` file. This import 
is ment for rather small datafiles, like a couple of hundred rows, as it is rather slow. 

The `.labimport` file consists of two main parts: The decription of the **file format** eg. how to interprete the file as a table
and the decription of the meaning of each column. For each value in the table a fitting dataset **must** exist. Creating 
a `.labimport` file is difficult and should be mentored by a person with programming experience.

## File format

The lab import uses the file reading capacity of the Python library [pandas](https://pandas.pydata.org/docs/reference/io.html).
The keyword driver is the pandas function to read the tabular data, and driver-options are the keywords of that function.
If you know how to load tables in `R` - this is quite similar.

### Common driver functions

#### [read_excel](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html#pandas.read_excel)

Reads excel files (.xlsx, .xlsb, .xls). Typical keywords are `sheet_name` and `index_col`. If your data is in the only 
worksheet and all data is well formatted, you do not need any options. If you have multiple header lines use `skiprows`
to skip those.

##### [read_csv](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html#pandas.read_csv)

Reads tabular text files with a seperator. Default is `,` as the variable seperator and `.` as the
decimal sign. This can be changed with `sep: ";"` and `decimal: ","`, the quotes are important here.
If you have date/time column, make sure to use the date parsing options of read_csv with the keywords date_format 
and parse_dates, as described in the link. If the date of the sample can be inferred from the sample name, this is not necessary.

#### General options

`skiprows`, `nrow`, `usecols` and `skipfooter` are keywords that can be used in every table format to ignore
unnecessary data. `na_values` is used to name conventions of N/A-Values in the file. If the file does not have column headers, 
or the column headers must be skipped, please indicate it with `headers: null` or give each column its own name

## Columns

Each column is addressed by its name (or in few cases postion). The columns are treated differently by its type.

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

This is a very complex type and can be used to derive metadata like site, time, depth from a sample name (this is called parsing). 
If additional columns for this information exists already, use the type `samplename`, then no parsing takes place and the
name is only copied. This is not easy - if you are no programmer, you might need help from someone with programming kno

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
(in the example 2) and the date format, in the example %d.%m.%Y_%H:%M using Pythons notation of date formats 
(which is used by a number of other programming languages). The site needs also the right group (in the example 1),
and you can add a map to translate site names into site id's of the database. If your data uses already the official
site id's, that map can be left out.

The level is derived from group 3 in our example and can be transformed with a factor. In the example the level 60 for
60cm depth, we use the factor -0.01 to translate it as depth (negative number) and in m. '60' -> -0.6.

If additional markers are needed, please post an issue in github (https://github.com/jlu-ilr-hydro/odmf/issues)

### type: row-factor

If the samples have been diluted, the row-factor in this column can be used to scale all values in that row. 

# Example 1

~~~~~~~~~~~~~~~~~~~~~~~~~~.yaml
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
        date:
            group: 2
            format: "%d.%m.%y_%H:%M"
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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~