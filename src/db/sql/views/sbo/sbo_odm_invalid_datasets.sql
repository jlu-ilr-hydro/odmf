-- Summarizes validity invariant in sql view
--  Where clause formulates the validity of odm series

DROP VIEW IF EXISTS sbo_odm_invalid_datasets;

CREATE OR REPLACE VIEW sbo_odm_invalid_datasets AS
  SELECT * FROM dataset
    WHERE start = "end"
      OR access = 0
      OR project is NULL;

ALTER VIEW sbo_odm_invalid_datasets OWNER TO "schwingbach-user";