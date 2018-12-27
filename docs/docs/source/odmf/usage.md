## Usage/ Tutorial/ Wiki

How to use the html/views and functionalities

### Views

All links from the leftside navigation bar are listed:

* `download` (see the datafiles section in )

### Folders

#### `datafiles` folder
Here all users can upload files for importing or just uploading
#### `media` folder
#### `preferences` folder

### Customization
#### Logo and image

The user can customize the logo (1) and the background image (2).

<!--<img src="../../images/landing-page.png" alt="landing page" width="550"/>-->

![landing page](../../images/installation/landing-page.png "Landing page")


Therefore to change (1) the path `webpage/media/schwingbach-logo.png` and for (2) the path at
`webpage/media/navigation-background.jpg` has to be altered.


### Import data

The data import is one of the core features of the platform.
The process consists of several steps, (1) upload files into the file system of the server and
(2) create import configuration file and (3) import via configuration into database.
Already imported data can be further altered (split) and reused (transformations).

#### Upload datafiles

Data files are uploaded via the `datafiles` tab. A data file has a maximum file size that it cannot exceed, otherwise
the import algorithm will time out.

#### Import

It's only possible to import files with `xls`,`xlsx`,`csv` as file extension.

#### Manipulate datasets
##### Split datasets

#### `.conf` files

The configuration file is a definition of the import process of all files in a directory.
This file includes variable attributes that all import data files have in common.
The concept of a configuration file assumes, that in general each data files import information can be covered by a
description and multiple column descriptions.
A description contains information that depict the import on file level and the column descriptions on column level.
The descriptions made by the user once, contain all information to automatically import the data of multiple files.
So the user is able to omit most of the configuration of future imports for this folder.

File specific attributes of the import process are `skiplines`.
Data specific attributes are `dateformat`, `datecolumn` or `sitecolumn`
If no `{*}.conf` file is present in a folder, the parent directory is searched for a configuration file.

<!-- standard configuration (?) -->

These files are processed with the `configparser` module, the module requires that a file is encoded in `utf-8` or a subset.
If a config file is not encoded in `utf-8` or a subset, when the file import is initiated with this kind of config file,
a error message is displayed to the user.

```pacmanconf
TBD.
; description part
[IC]
; TBD
instrument = 30
skiplines = 1
dateformat = %d_%m_%Y
datecolumns = 2
sitecolumn = 3
sample_mapping = {'A1W': '112',
 'A2W': '113',
 'A3W': '114',
 'B1': '85',
 'B2': '86',
 'B3': '87',
 'E1': '88',
 'E2': '89',
 'E3': '90',
 'F1': '79',
 'F2': '80',
 'F3': '81',
 'FF1': '91',
 'FF2': '92',
 'GL1': '109',
 'GL2': '110',
 'GL3': '111',
 'K1': '82',
 'K2': '83',
 'K3': '84'}

; column part
[N-Nitrat]
column = 5
name = N-Nitrat
valuetype = 16
factor = 1
minvalue = 0
maxvalue = 100
```
