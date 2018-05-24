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

CREATE VIEW datavalues AS
 SELECT r.id AS valueid,
    d.calibration_offset,
    d.calibration_slope,
    d.id AS datasetid,
    ((r.value * d.calibration_slope) + d.calibration_offset) AS datavalue,
    (r."time")::character varying AS localdatetime,
    2 AS utcoffset,
    (r."time" + ('01:00:00'::time without time zone)::interval) AS datetimeutc,
    d.site AS siteid,
    d.valuetype AS variableid,
    'nc'::character varying AS censorcode,
    d.datacollectionmethod AS methodid,
    d.project AS sourceid,
    NULL::integer AS sampleid,
    d.quality AS qualitycontrollevelid
   FROM record r,
    dataset d
  WHERE (r.dataset = d.id);


ALTER TABLE public.datavalues OWNER TO "schwingbach-user";

--
-- PostgreSQL database dump complete
--

