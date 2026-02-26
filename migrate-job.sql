/*
 Migrate Job
 */

ALTER TABLE job ADD COLUMN log JSON;
ALTER TABLE job ADD COLUMN duration INT;
ALTER TABLE job ADD COLUMN mailer JSON;

/* Add delete cascade to site_geometry */
alter table site_geometry drop constraint site_geometry_id_fkey, add constraint site_geometry_id_fkey foreign key (id) references site(id) on delete cascade;

/* Update new Person #200 */
ALTER TABLE person
    DROP COLUMN supervisor,
    DROP COLUMN telephone,
    DROP COLUMN can_supervise,
    DROP COLUMN mobile,
    DROP COLUMN car_available,
    ADD COLUMN orcid VARCHAR NULL,
    ADD COLUMN last_login TIMESTAMP NULL;

/* Update dataset #257 and #191*/
ALTER TABLE dataset
    ADD COLUMN license VARCHAR NULL,
    ADD COLUMN doi VARCHAR NULL;
    DROP COLUMN uses_dst;

ALTER TABLE alarm
    ADD COLUMN name VARCHAR NULL,
    ADD COLUMN message VARCHAR NULL;