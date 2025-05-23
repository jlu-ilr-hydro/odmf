# !fa-ruler Value Type

The value type describes **what** is measured, eg.:

- the Nitrate-N concentration in soil water in mg/l
- the air temperature in °C
- the rainfall intensity over a certain time period in mm/day
- the absolute rainfall amount in a certain time period in mm
- the isotopic difference for deuterium from the deep sea water standard in &delta;&permil;

To create a new value type, select "new valuetype" on the !fa-ruler value type page and give it name, unit and a description. The value range can help when importing 
records from external sources to prevent unit problems.

## Import value types from tables

It is yet not possible for web users to import lists of value types. However, admins
with access to the ODMF-Python interface can easily create valuetypes from tables
if the columns name and unit are given - or even better the comment and value range columns (minvalue, maxvalue) also. If you would like to import valuetypes like sites, logs and datasets create an issue on GitHub.