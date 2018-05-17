#!/bin/bash
#
# Update the materialized view series in schema schwingbach

LOGFILE=./db.log
DATABASE=schwingbach

psql -c "REFRESH MATERIALIZED VIEW series;" -L $LOGFILE $DATABASE

status=$?

if [[$status -ne 0]]; then
    time=`date +%Y-%m-%d\ %H:%M:%S`
    echo "Materializing exited with $status at $time" >> error.log
fi

