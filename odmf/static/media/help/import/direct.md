# Direct input

You can add directly records to datasets on the add-record page. To make this easy in the field, you can prepare your field trip by setting shortcuts.

## A shortcut text file

Create in your user directory a new text file with links to the datasets you want to fill. For easy selection in the field format the link as haeading 1 or 2, to your taste.
The ODMF-markdown has a special link form for adding records to a dataset. The link form for datset 0000 is `add-record:0000 "A text that describes what you want to do"`

### Example

As an example, we assume you will need to take measurements for the datasets ds:15, ds:16, ds:30 and ds:31. A file with links to the add-record page of the datasets would
be written like:

!!! x "Write file as"
        # Field X, NE corner
        ## add-record:15 "Add plant height"
        ## add-record:16 "Add stem width"
        # Field Y, center
        # add-record:30 "Add plant height"
        # add-record:31 "Add stem width"

And the file is shown as:

!!! x "File output"
    # Field X, NE corner
    ## add-record:15 "Add plant height"
    ## add-record:16 "Add stem width"
    # Field Y, center
    ## add-record:30 "Add plant height"
    ## add-record:31 "Add stem width"
