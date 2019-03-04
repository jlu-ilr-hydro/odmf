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
-- Name: seriescatalog; Type: VIEW; Schema: public; Owner: schwingbach-user
--
-- TODO: better join cuahsi views for non-redundant code (such as variablecode)

DROP MATERIALIZED VIEW IF EXISTS seriescatalog;

CREATE MATERIALIZED VIEW seriescatalog AS
 SELECT MIN(d.id) as seriesid, -- changes are unusual
    d.site AS siteid,
    d.site::character varying AS sitecode,
    s.name AS sitename,
    _vr.variableid AS variableid,
    _vr.variablecode AS variablecode,
    _vr.variablename AS variablename,
    (u.unitsname)::text AS variableunitsname,
    _vr.valuetype AS valuetype,
    _vr.speciation AS speciation,
    _vr.variableunitsid AS variableunitsid,
    _vr.samplemedium AS samplemedium,
    d.project AS sourceid,
    p.name AS sourcedescription,
    p.organization AS organization,
    p.citation AS citation,
    u.unitsid AS timeunitsid,
    u.unitsname AS timeunitsname,
    (0.0)::real AS timesupport,
    d.cv_datatype AS datatype,
    _vr.generalcategory AS generalcategory,
    d.datacollectionmethod AS methodid,
    dm.description AS methoddescription,
    d.quality AS qualitycontrollevelid,
    q.name AS qualitycontrollevelcode,
    MIN(d.start) AS begindatetime,
    MAX(d."end") AS enddatetime,
    -- adds utcdatetime
    MIN(CASE WHEN pg_tz.utc_offset IS NOT NULL THEN
         d.start AT TIME ZONE pg_tz.name AT TIME ZONE 'UTC'
         ELSE d.start END) as begindatetimeutc,
    MAX(CASE WHEN pg_tz.utc_offset IS NOT NULL THEN
         d."end" AT TIME ZONE pg_tz.name AT TIME ZONE 'UTC'
         ELSE d."end" END) as enddatetimeutc,
    --MIN(d.timezone) as timezone,
    SUM(series.count) AS valuecount
   FROM dataset d
     JOIN site s ON d.site = s.id
     JOIN _variables _vr ON _vr._sbo_valuetype = d.valuetype
                         AND _vr._sbo_dataset_type = d.type
     JOIN quality q ON d.quality = q.id
     JOIN datacollectionmethod dm ON d.datacollectionmethod = dm.id
     JOIN units u ON _vr.variableunitsid = u.unitsid
     JOIN project p ON d.project = p.id
     JOIN series ON d.id = series.dataset
     LEFT JOIN pg_timezone_names pg_tz ON pg_tz.name = d.timezone
  WHERE d.valuetype NOT IN (SELECT id FROM sbo_odm_invalid_valuetypes)
    AND series.count > 0
    AND d.id NOT IN (SELECT id FROM sbo_odm_invalid_datasets)
  GROUP BY siteid, sitename, variableid, variablecode, variablename, variableunitsname, u.unitsid, _vr.valuetype, speciation,
    variableunitsid, samplemedium, sourceid, sourcedescription, organization,
    citation, timeunitsid, timeunitsname, timesupport, d.cv_datatype, generalcategory, methodid, methoddescription,
    qualitycontrollevelid, qualitycontrollevelcode, methodid
  ORDER BY seriesid
WITH DATA;


ALTER TABLE public.seriescatalog OWNER TO "schwingbach-user";

--
-- Name: VIEW seriescatalog; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON MATERIALIZED VIEW seriescatalog IS 'WHERE clause excludes odm incompatible valuetypes / incompatible rows broadly speaking';


--
-- PostgreSQL database dump complete
--

