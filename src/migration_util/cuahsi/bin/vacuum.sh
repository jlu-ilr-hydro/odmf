#!/bin/bash
# Optimize database relations

LOGFILE=./db.log
DATABASE=schwingbach

psql -c "VACUUM (VERBOSE, ANALYZE) record;" -L $LOGFILE $DATABASE

status=$?

if [[$status -ne 0]]; then
    time=`date +%Y-%m-%d\ %H:%M:%S`
    echo "Vacuum-ing exited with $status at $time" >> error.log
fi
