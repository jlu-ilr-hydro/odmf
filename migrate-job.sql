ALTER TABLE job ADD COLUMN log JSON;
ALTER TABLE job ADD COLUMN duration INT;
ALTER TABLE job ADD COLUMN mailer JSON;

/* Add delete cascade to site_geometry */
alter table site_geometry drop constraint site_geometry_id_fkey, add constraint site_geometry_id_fkey foreign key (id) references site(id) on delete cascade;

