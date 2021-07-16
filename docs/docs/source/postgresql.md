# Prepare and tune your PostgreSQL server for ODMF

For this guide, we assume you are using Ubuntu 20.04 LTS and postgresql 12. Other OS may
behave differently, for other versions of PostgreSQL change the directories.

The machine to be considered has 16GB of RAM and multiple cores. Serving data is the most demanding
job of the server.

## Move data files

If you have multiple HDD's or partions on your machine, the datafiles of 
PostgreSQL should reside on the largest filesystem. On systems with continuous 
file systems this step is not necessary.

As a target for the datafiles we will use /mnt/largeHDD/postgresql

### Source: 

https://www.digitalocean.com/community/tutorials/how-to-move-a-postgresql-data-directory-to-a-new-location-on-ubuntu-18-04

### Summary

For more explanations, see the [original source](https://www.digitalocean.com/community/tutorials/how-to-move-a-postgresql-data-directory-to-a-new-location-on-ubuntu-18-04)

#### Step 1 - Moving the PostgreSQL Data Directory

Stop postgresql

    sudo systemctl stop postgresql.service
    sudo systemctl status postgresql.service

Copy datafiles to target location, and rename the files at the old location

    sudo rsync -av /var/lib/postgresql /mnt/largeHDD
    sudo mv /var/lib/postgresql/12/main /var/lib/postgresql/12/main.bak

#### Step 2 - Pointing to the New Data Location

Edit postgresql.conf 

    sudo nano /etc/postgresql/12/main/postgresql.conf

Find the line that begins with data_directory and change the path which follows to reflect the new location.

    data_directory = '/mnt/largeHDD/postgresql/12/main'

Keep the editor open, more tuning can be done in that file

## Tune memory usage for PostgreSQL

PostgreSQL can run on many different systems and has quite conservative memory settings. By allowing PgSQL 
to use more RAM, many processes can be sped up. You can generate a tuned postgresql.conf with this online
tool: https://pgtune.leopard.in.ua/

### Source:

https://blog.crunchydata.com/blog/optimize-postgresql-server-performance

### Summary

Set values in postgresql.conf, for explanations see the source. The [tool](https://pgtune.leopard.in.ua) 
recommends the following

    # DB Version: 12
    # OS Type: linux
    # DB Type: dw
    # Total Memory (RAM): 16 GB
    # CPUs num: 12
    # Data Storage: hdd
    
    max_connections = 40
    shared_buffers = 4GB
    effective_cache_size = 12GB
    maintenance_work_mem = 2GB
    checkpoint_completion_target = 0.9
    wal_buffers = 16MB
    default_statistics_target = 500
    random_page_cost = 4
    effective_io_concurrency = 2
    work_mem = 8738kB
    min_wal_size = 4GB
    max_wal_size = 16GB
    max_worker_processes = 12
    max_parallel_workers_per_gather = 6
    max_parallel_workers = 12
    max_parallel_maintenance_workers = 4
