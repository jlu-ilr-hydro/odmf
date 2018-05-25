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

DROP VIEW IF EXISTS seriescatalog;

CREATE VIEW seriescatalog AS
 SELECT d.id AS seriesid,
    d.site AS siteid,
    d.site AS sitecode,
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
    tu.unitsid AS timeunitsid,
    tu.unitsname AS timeunitsname,
    (0.0)::real AS timesupport,
    d.cv_datatype AS datatype,
    _vr.generalcategory AS generalcategory,
    d.datacollectionmethod AS methodid,
    dm.description AS methoddescription,
    d.quality AS qualitycontrollevelid,
    q.name AS qualitycontrollevelcode,
    d.start AS begindatetime,
    d."end" AS enddatetime,
    d.start AS begindatetimeutc,
    d."end" AS enddatetimeutc,
    series.count AS valuecount
   FROM dataset d
     JOIN site s ON d.site = s.id
     JOIN _variables _vr ON _vr._sbo_valuetype = d.valuetype
                         AND _vr._sbo_dataset_type = d.type
     JOIN quality q ON d.quality = q.id
     JOIN datacollectionmethod dm ON d.datacollectionmethod = dm.id
     JOIN units u ON _vr.variableunitsid = u.unitsid
     JOIN project p ON d.project = p.id
     JOIN series ON d.id = series.dataset
  WHERE d.valuetype NOT IN (SELECT id FROM sbo_odm_invalid_valuetypes)
    AND series.count > 0
    AND d.id NOT IN (SELECT id FROM sbo_odm_invalid_datasets)
  ORDER BY d.id;


ALTER TABLE public.seriescatalog OWNER TO "schwingbach-user";

--
-- Name: VIEW seriescatalog; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON VIEW seriescatalog IS 'WHERE clause excludes odm incompatible valuetypes / incompatible rows broadly speaking';


--
-- PostgreSQL database dump complete
--

