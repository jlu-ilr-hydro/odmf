create materialized view _variables as
SELECT DISTINCT concat(v.id, '-', upper(d.cv_datatype::text), '-',
                       CASE
                           WHEN d.type::text = 'timeseries'::text THEN 'FIELDOB'::text
                           WHEN d.type::text = 'transformed_timeseries'::text THEN 'DERIVED'::text
                           ELSE 'Unknown'::text
                           END)                   AS variablecode,
                row_number() OVER (ORDER BY v.id) AS variableid,
                v.id                              AS _sbo_valuetype,
                d.type                            AS _sbo_dataset_type,
                ve.cv_variable_name                AS variablename,
                ve.cv_speciation                   AS speciation,
                ve.cv_unit                         AS variableunitsid,
                ve.cv_sample_medium                AS samplemedium,
                CASE
                    WHEN d.type::text = 'timeseries'::text THEN 'Field Observation'::text
                    WHEN d.type::text = 'transformed_timeseries'::text THEN 'Derived Value'::text
                    ELSE 'Unknown'::text
                    END                           AS valuetype,
                false                             AS isregular,
                0                                 AS timesupport,
                103                               AS timeunitsid,
                d.cv_datatype                     AS datatype,
                v.cv_general_category             AS generalcategory,
                '-9999'::text                     AS nodatavalue
FROM dataset d
         LEFT JOIN valuetype v ON d.valuetype = v.id LEFT JOIN valuetype_extension ve on v.id = ve.id
WHERE NOT (v.id IN (SELECT sbo_odm_invalid_valuetypes.id
                    FROM sbo_odm_invalid_valuetypes))
  AND NOT (d.id IN (SELECT sbo_odm_invalid_datasets.id
                    FROM sbo_odm_invalid_datasets))
GROUP BY v.id, d.cv_datatype, d.type
ORDER BY row_number() OVER (ORDER BY v.id);

comment on materialized view _variables is 'inner view for wrapper view "variables"';

alter materialized view _variables owner to "schwingbach-user";

