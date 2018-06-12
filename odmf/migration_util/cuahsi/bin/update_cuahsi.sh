#!/bin/bash
# update_cuahsi.sh

#change working dir
cd $(dirname "$0")

# Refresh rows of materialized view series
./refresh_series.sh

# Force a renewal of the transformed dataset records
./../update_transformedvalues.py

# Optimize datastructure of new records
./vacuum.sh

# TODO
# Validate the CUAHSI/SBO data
#./check_validity.py
