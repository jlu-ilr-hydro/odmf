# .conf files

Data-Loggers usually create tabular data for a number of sensors at the same site. One can create .conf-files 
(in [INI-format](https://en.wikipedia.org/wiki/INI_file)), that describe the tabular format of the data logger.
The .conf file is either in the same directory as the data file or in a directory above. Excel and CSV-Files with
a .conf file in the same directory or in a directory above can be imported. The .conf file consists of a general section
describing the data format and sections for each column that should be imported. Each data column creates a new dataset,
except the column is declared to append to an existing dataset.
