-- script to extend the schwingbach database tables to
-- serve the same information as the odm schema

ALTER TABLE valuetype
    ADD COLUMN cv_variable_name varchar(32) default NULL,
    ADD COLUMN cv_speciation varchar(32) default 'Not Applicable',
    ADD COLUMN cv_sample_medium varchar(32) default 'Not Relevant',
    ADD COLUMN cv_general_category varchar(32) default 'Hydrology',
    ADD COLUMN cv_unit varchar(32) default NULL;

ALTER TABLE dataset
    ADD COLUMN cv_valuetype varchar(32) default 'Unknown',
    ADD COLUMN cv_datatype varchar(32) default 'Sporadic';

CREATE VIEW variable AS
    SELECT distinct CONCAT(v.id, '-', UPPER(d.cv_datatype)) as variable_id, v.*, d.cv_valuetype, d.cv_datatype 
      FROM dataset d, valuetype v 
      WHERE d.valuetype = v.id 
      ORDER BY id;
