-- Summarizes validity invariant in sql view
--  Where clause formulates the validity of odm series

CREATE OR REPLACE VIEW sbo_odm_invalid_datasets AS
  SELECT * FROM dataset
    WHERE start = "end";

ALTER VIEW sbo_odm_invalid_datasets OWNER TO "schwingbach-user";