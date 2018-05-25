-- Summarizes validity invariant in sql view
--  Where clause formulates the validity of odm series

DROP VIEW IF EXISTS sbo_odm_invalid_valuetypes;

CREATE OR REPLACE VIEW sbo_odm_invalid_valuetypes AS
  SELECT * FROM valuetype
      WHERE id in (30)
        OR cv_variable_name = ''
        OR cv_unit is NULL;

ALTER VIEW sbo_odm_invalid_valuetypes OWNER TO "schwingbach-user";