-- Materialized view to gain more control over published valuetypes in case of updates of the tables
--  dataset or valuetype

CREATE MATERIALIZED VIEW _variables AS
SELECT DISTINCT concat(v.id, '-', upper((d.cv_datatype)::text), '-',
                        CASE WHEN "type" = 'timeseries'
                          THEN 'FIELDOB'
                          WHEN "type" = 'transformed_timeseries'
                            THEN 'DERIVED'
                          ELSE 'Unknown' END) as variablecode,
    ROW_NUMBER() OVER (ORDER BY v.id) AS variableid,
    v.id as _sbo_valuetype,
    d.type as _sbo_dataset_type,
    v.cv_variable_name AS variablename,
    v.cv_speciation AS speciation,
    v.cv_unit AS variableunitsid,
    v.cv_sample_medium AS samplemedium,
    CASE WHEN "type" = 'timeseries'
     THEN 'Field Observation'
     WHEN "type" = 'transformed_timeseries'
      THEN 'Derived Value'
      ELSE 'Unknown' END AS valuetype,
    false AS isregular,
    0 AS timesupport,
    103 AS timeunitsid,
    d.cv_datatype AS datatype,
    v.cv_general_category AS generalcategory,
    '-9999'::text AS nodatavalue
   FROM dataset d
   LEFT JOIN valuetype v ON d.valuetype = v.id
  WHERE ((v.id <> 30) AND (v.cv_variable_name <> ''))
  GROUP BY v.id, d.cv_datatype, d.type
  ORDER BY variableid;
