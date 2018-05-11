-- This view is materialzed because of its size and slow computation performance

CREATE MATERIALIZED VIEW _dataset_tt AS
  SELECT
    d.id as id,
    ''::varchar as name,
    ''::varchar as filename,
    MIN(time) as start,
    MAX(time) as end,
    d.source as source,
    d.site as site,
    d.valuetype as valuetype,
    ''::varchar as measured_by,
    d.quality as quality,
    d.comment as comment,
    d.calibration_offset as calibration_offset,
    d.calibration_slope as calibration_slope,
    'transformed_timeseries'::varchar as type,
    d.uses_dst as uses_dst,
    d.level,
    d.access,
    d.project,
    d.timezone,
    d.cv_valuetype,
    d.cv_datatype,
    d.datacollectionmethod
  FROM transformed_timeseries tt
    LEFT JOIN transforms t ON tt.id = t.target
    LEFT JOIN dataset d ON t.source = d.id
  GROUP BY d.id, tt.id