# Direct input

You can add directly records to datasets on the add-record page. Go to the timeseries dataset, where the record should be added and click on !fa-circle-plus add record. The address of the add-record page can be copied and used any where for a shortcut link.

To make adding records easy in the field, you can prepare your field trip by preparing a file with links, or you can produce QR ocdes with the links.

## A shortcut text file

Create in your user directory a new text file with links to the datasets you want to fill. For larger text in the field format the links as heading (see: help:odmf-markdown) to your taste.
The ODMF-markdown has a special link form for adding records to a dataset. The link form for datset 0000 is 

!!! light ""
        add-record:0000 "A text that describes what you want to do"

and is shown as:

!!! light ""
    add-record:0000 "A text that describes what you want to do"

### Example

As an example, we assume you will need to take measurements for the datasets ds:15, ds:16, ds:30 and ds:31. A file with links to the add-record page of the datasets would be written like:

!!! light "Write file as"
        # Field X, NE corner
        ## add-record:15 "Add plant height"
        ## add-record:16 "Add stem width"
        # Field Y, center
        # add-record:30 "Add plant height"
        # add-record:31 "Add stem width"

And the file is shown as:

!!! light "File output"
    # Field X, NE corner
    ## add-record:15 "Add plant height"
    ## add-record:16 "Add stem width"
    # Field Y, center
    ## add-record:30 "Add plant height"
    ## add-record:31 "Add stem width"
