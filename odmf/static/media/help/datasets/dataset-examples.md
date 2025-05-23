# Example applications

## Example 1 - weather station

A cheap compact weather station measures air temp, humidity, wind speed and rain.
You have 1 site, 1 person responsible, 1 instrument, 1 quality, 1 accessability rules, but 4 different value types.
You need 4 datasets, for each value type its own. To create your datasets, go to dataset / new and type your
information in. The station is mounted in 2m height, so use a level of "2" in each dataset. Click save and the first one is created. If you click on copy, you need only change what is different
for the next dataset, this is easier. 

If you have life telemetry access to your weather station - cool, use the API of ODMF and probably the 
[odmfclient](https://github.com/jlu-ilr-hydro/odmfclient) to upload your data automatically. If you need guidance, 
raise an issue in github. We have experience with Lora, Meteosol, ADCON and Campbell-Systems.

If you have an offline logger, upload your data tables from the logger to the file-manager and use an 
[import strategy](/help/import). For logger data you will probably write a .conf file.

## Example 2 - Soil moisture network

20 locations are equipped with soil moisture profiles with 3 depths each (eg. TEROS 12 in 10, 30 and 60cm depth), in total 60 sensors. 
Each sensor measures 3 values, soil moisture RAW, soil temperature, electric conductivity. You need to create 180 datasets
all a bit similar but not always.

First create your [sites](site), either by hand or import them, note their ID's. 
Then create 3 datasets for the first depth (level=-0.1) by hand with the copy button. Use calibration slope and offset
to convert the raw soil moisture data into something meaningful.

Export the dataset meta data on the dataset list page for the 3 new datasets. Use a spreadsheet software (Excel, LibreOffice Calc etc.)
to fill all missing 177 rows for the missing datasets - copy & paste is your friend here. Make sure every column stays intact
and do not change the column headers. Then import the datasets from your spreadsheet. 

Afterwards create either [.conf files](../../import/conf.md) to import your logger data or write a script to use telemetry. The ODMF authors
can provide examples for integration with the Chirpstack Lora-Server, Campbell-Loggers and OTT Adcon-Telemetry systems.

## Example 3 - Saving direct field observations

The crop height or the stream depth is measured with a ruler once a week. Create the fitting datasets eg with the copy 
button, for each value type and each location. 

### Mobile internet

If you have a mobile internet connection in the field and you can access the ODMF server, you can use a tablet or field 
laptop to enter the data directly at the dataset and make it easier by a file with links to the datasets, that you just need to click on
or take a sheet with qr-codes pointing to the correct datasets with you.

### Offline

You can fill out an Excel template while your in the field and upload it accordingly. The file should end with _log.xlsx, 
then you can import your data using the [log-import strategy](/help/import/log) 

## Example 4 - A one time snapshot sampling over multiple sites

In a measurement campaign, you are going to sample at multiple locations soil samples and analyze them for Nmin. The
locations are randomly distributed over a study area and the same locations will never be sampled again. For one value
you do not want to create a complete site.

This type of data is yet not really fitting into ODMF. The best workaround is: Upload your tabular data to the filemanager
with all locations in WGS84 / geographical coordinates and the values.

Create a site with a polygon-geometry for the whole study area. Create a dataset for each value type (eg 2 for Nmin and 
bulk density) using the study area. Link your file-data (a good idea any way) and your data is findable, accessible and
with some hand work reusable. It lacks interoperability. Of course, you can import the records to the dataset with one
of the [import strategies](/help/import), probably .conf again. 


## Example 5 - regular sampling with lab analysis

As part of your protocol, you collect every 2 weeks at 17 sites samples and bring them into the lab and run analysis there.
As the software of the lab device cannot handle multiple columns as the sample name, you mangle the collection site
and date somehow in the sample name. The lab-analyzer produces a list of values with the sample names and their 
meaasured values. For example we have a ion chromatograph producing the concentrations of a number of ions in a
water sample. We need for the 5 ions at the 17 sites 85 datasets created as in example 1 or 2. Using the 
[lab importer](/help/import/lab), the sample name can be unmangled and the values from the table can be imported into
the correct datasets.