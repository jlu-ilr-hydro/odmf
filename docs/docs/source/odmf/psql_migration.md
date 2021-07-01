# How to migrate a PostgreSQL database to another server

## On the current server

    pg_dump -abvOxFc -Z3 -t dataset -t datasource -t image -t installation -t job -t log -t person -t project -t quality -t record -t site -t transformed_timeseries -t transforms -t unit -t valuetype $NAME >$NAME.pg_dump
     


## On the new server

Copy the data from the old server
    
    scp YOU@old_server.com:$NAME.pg_dump .


    