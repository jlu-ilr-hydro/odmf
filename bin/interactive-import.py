"""
This file teaches how to do a dataimport from the interactive shell, useful for debugging
"""

# In the shell
# $ cd /srv/odmf/XXX/
# $ source venv/bin/activate
# $ odmf interactive

# Python from here on
# Import what we need
from odmf.dataimport import ImportDescription, pandas_import as pi
# Path to the datafile (relativ zu datafiles)
path = 'lab/Weekly_sampling_ECSF/RESPECT/WeeklySampling_ECSF_RESPECT_076-151_DW.xlsx'
# ImportDescription (.conf-Datei) laden
idescr = ImportDescription.from_file('datafiles/' + path)

# Load dataframe, using the relative path
df = pi.load_dataframe(idescr, path)

print('df-columns')
print('\n'.join(df.columns))


