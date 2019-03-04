--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

--
-- Name: datavalues; Type: VIEW; Schema: public; Owner: schwingbach-user
--

DROP MATERIALIZED VIEW IF EXISTS datavalues;

CREATE MATERIALIZED VIEW datavalues AS
 SELECT row_number() OVER (ORDER BY r."time") AS valueid,
    d.id as datasetid,
    d.level as offsetvalue,
    (CASE WHEN d.level IS NOT NULL THEN 0 ELSE NULL END)::real as offsettypeid,
    --d.calibration_slope,
    ((r.value * d.calibration_slope) + d.calibration_offset)::real AS datavalue,
    (r."time")::character varying AS localdatetime,
    (CASE WHEN pg_tz.name IS NOT NULL THEN EXTRACT(epoch FROM pg_tz.utc_offset)/3600 ELSE 0 END)::real AS utcoffset,
    (CASE WHEN pg_tz.name IS NOT NULL THEN r."time" AT TIME ZONE pg_tz.name AT TIME ZONE 'UTC' ELSE r."time" END)::character varying AS datetimeutc,
    d.site AS siteid,
    _v.variableid AS variableid,
    'nc'::character varying AS censorcode,
    d.datacollectionmethod AS methodid,
    d.project AS sourceid,
    NULL::integer AS sampleid,
    d.quality AS qualitycontrollevelid
   FROM record r
    JOIN dataset d ON r.dataset = d.id
    JOIN _variables _v ON (_v._sbo_valuetype = d.valuetype
                       AND _v._sbo_dataset_type = d.type)
    LEFT JOIN pg_timezone_names pg_tz ON pg_tz.name = d.timezone
    WHERE r.dataset NOT IN (SELECT id FROM sbo_odm_invalid_datasets)
      AND d.valuetype NOT IN (SELECT id FROM sbo_odm_invalid_valuetypes)
      ORDER BY row_number() OVER (ORDER BY r."time")
  WITH DATA;


ALTER TABLE public.datavalues OWNER TO "schwingbach-user";

--
-- PostgreSQL database dump complete
--

