-- Materialized View: _variables

-- DROP MATERIALIZED VIEW _variables;

CREATE MATERIALIZED VIEW _variables AS
 SELECT DISTINCT concat(v.id, '-', upper(d.cv_datatype::text), '-',
        CASE
            WHEN d.type::text = 'timeseries'::text THEN 'FIELDOB'::text
            WHEN d.type::text = 'transformed_timeseries'::text THEN 'DERIVED'::text
            ELSE 'Unknown'::text
        END) AS variablecode,
    row_number() OVER (ORDER BY v.id) AS variableid,
    v.id AS _sbo_valuetype,
    d.type AS _sbo_dataset_type,
    v.cv_variable_name AS variablename,
    v.cv_speciation AS speciation,
    v.cv_unit AS variableunitsid,
    v.cv_sample_medium AS samplemedium,
        CASE
            WHEN d.type::text = 'timeseries'::text THEN 'Field Observation'::text
            WHEN d.type::text = 'transformed_timeseries'::text THEN 'Derived Value'::text
            ELSE 'Unknown'::text
        END AS valuetype,
    false AS isregular,
    0 AS timesupport,
    103 AS timeunitsid,
    d.cv_datatype AS datatype,
    v.cv_general_category AS generalcategory,
    '-9999'::text AS nodatavalue
   FROM dataset d
     LEFT JOIN valuetype v ON d.valuetype = v.id
     -- restrict from invalid datasets and valuetypes
  WHERE NOT (v.id IN (SELECT sbo_odm_invalid_valuetypes.id FROM sbo_odm_invalid_valuetypes))
    AND NOT (d.id IN (SELECT sbo_odm_invalid_datasets.id   FROM sbo_odm_invalid_datasets))
  GROUP BY v.id, d.cv_datatype, d.type
  ORDER BY row_number() OVER (ORDER BY v.id)
WITH DATA;

ALTER TABLE _variables
  OWNER TO "schwingbach-user";

COMMENT ON MATERIALIZED VIEW _variables IS 'inner view for wrapper view "variables"';