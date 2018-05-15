#!/bin/bash
# update_cuahsi.sh

# Refresh series view
./refresh_series.sh

# Force a renewal of the transformed dataset records
./../update_transformedvalues.py

# Validate the CUAHSI/SBO data
/check_validity.py
