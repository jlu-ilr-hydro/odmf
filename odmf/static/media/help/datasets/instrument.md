# !fa-thermometer-half Instrument

For the interpretation of datasets, the used methodology is important. The instrument feature of ODMF is for the description of the used instruments or methodology. If you have used a field installation of a device eg. soil moisture probes, you can save where and when this field device have been deployed in the field. For lab instruments or mobile instruments an installation makes of course not sense.

## Properties

An instrument / methodology is described with its name, an informal description and a link to a detailed description. The instrument type is used to describe the instrument category - mobile field instrument, logger, lab instrument, manual measurement etc.

A new instrument is created using the "new instrument" button and the properties are filled out by hand.

## Import value types from tables

It is yet not possible for web users to import lists of instruments. However, admins
with access to the ODMF-Python interface can easily create intruments from tables
if the columns name and type are given - or even better the comment and link to the detailed description also. If you would like to import instruments from tables like sites, logs and datasets create an issue on GitHub.