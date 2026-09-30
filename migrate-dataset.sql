/*
 Migrate Job
 */

/* Add delete cascade to site_geometry */
alter table site_geometry drop constraint site_geometry_id_fkey, add constraint site_geometry_id_fkey foreign key (id) references site(id) on delete cascade;

/* Update new Person #200 */
    ALTER TABLE person    ADD COLUMN orcid VARCHAR NULL;
    ALTER TABLE person ADD COLUMN last_login TIMESTAMP NULL;

/* Update dataset #257 and #191*/
ALTER TABLE dataset    ADD COLUMN license VARCHAR NULL;
ALTER TABLE dataset ADD COLUMN doi VARCHAR NULL;   
ALTER TABLE dataset ALTER COLUMN uses_dst DROP NOT NULL;
ALTER TABLE datasetalarm    ADD COLUMN name VARCHAR NULL;
ALTER TABLE datasetalarm    ADD COLUMN message VARCHAR NULL;


ALTER TABLE dataset DROP COLUMN uses_dst;
ALTER TABLE person
    DROP COLUMN supervisor,
    DROP COLUMN telephone,
    DROP COLUMN can_supervise,
    DROP COLUMN mobile,
    DROP COLUMN car_available;
