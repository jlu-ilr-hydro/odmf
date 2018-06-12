#!/bin/bash
#
# Update the materialized view series in schema schwingbach

LOGFILE=./db.log
DATABASE=schwingbach

psql -c "REFRESH MATERIALIZED VIEW series; REFRESH MATERIALIZED VIEW _variables; REFRESH MATERIALIZED VIEW seriescatalog;" -L $LOGFILE $DATABASE

# checks status
if [ "$?" -ne 0 ]; then
    time=`date +%Y-%m-%d\ %H:%M:%S`
    echo "Materializing exited with $status at $time" >> error.log
fi

