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
