

Configuration History
**********************

*2017-07-07* - *Registered cronjob for materializing series view* - chrisw

    Path to cronjob script `/home/gh1961/schwingbach/odm/bin/refresh_series.sh`
    The job is registered to execute on every midnight

*2017-06-27* - **UPDATE TO POSTGRES 9.3** - chrisw

    Updated from 9.1 to 9.3. Backup file remains at `/media/hd70GB/backup/pg_all.bak.sql` (7.2 Gigabyte).

    * Servers 9.1 and 9.5 disabled, with `/etc/postgresql/9.[1/5]/main/start.conf`
      changed from `auto` to `disabled`. 9.1 will be deleted in the future.

    *Note:* https://www.postgresql.org/docs/9.1/static/upgrading.html
