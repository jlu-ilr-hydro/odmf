#!/bin/bash
#
# Update the materialized view series in schema schwingbach

psql -c "REFRESH MATERIALIZED VIEW series;" schwingbach

status=$?

if [[$status -ne 0]]
    time=`date +%Y-%m-%d\ %H:%M:%S`
    echo "Materializing exited with $status at $time" >> error.log
fi