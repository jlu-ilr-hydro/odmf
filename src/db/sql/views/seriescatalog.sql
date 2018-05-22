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

--DROP VIEW seriescatalog;
  CREATE VIEW seriescatalog AS
 SELECT d.id AS seriesid,
    d.site AS siteid,
    d.site AS sitecode,
    s.name AS sitename,
    _vr.variableid AS variableid,
    _vr.variablecode AS variablecode,
    v.name AS variablename,
    (u.unitsname)::text AS variableunitsname,
    _vr.valuetype AS valuetype,
    v.cv_speciation AS speciation,
    v.cv_unit AS variableunitsid,
    v.cv_sample_medium AS samplemedium,
    d.project AS sourceid,
    p.name AS sourcedescription,
    p.organization AS organization,
    p.citation AS citation,
    tu.unitsid AS timeunitsid,
    tu.unitsname AS timeunitsname,
    (0.0)::real AS timesupport,
    d.cv_datatype AS datatype,
    (v.cv_general_category)::text AS generalcategory,
    d.datacollectionmethod AS methodid,
    dm.description AS methoddescription,
    d.quality AS qualitycontrollevelid,
    q.name AS qualitycontrollevelcode,
    d.start AS begindatetime,
    d."end" AS enddatetime,
    d.start AS begindatetimeutc,
    d."end" AS enddatetimeutc,
    series.count AS valuecount
   FROM (((((((((dataset d
     LEFT JOIN site s ON ((d.site = s.id)))
     LEFT JOIN valuetype v ON (d.valuetype = v.id))
     INNER JOIN _variables _vr ON (_vr._sbo_valuetype = v.id AND _vr._sbo_dataset_type = d.type))
     LEFT JOIN quality q ON ((d.quality = q.id)))
     LEFT JOIN datacollectionmethod dm ON ((d.datacollectionmethod = dm.id)))
     LEFT JOIN units u ON ((v.cv_unit = u.unitsid)))
     LEFT JOIN project p ON ((d.project = p.id)))
     LEFT JOIN units tu ON ((tu.unitsid = 100)))
     LEFT JOIN series ON ((d.id = series.dataset)))
  WHERE ((((d.access = 0) AND (v.id <> 30)) AND (series.count > 0)) AND (d.id NOT IN (SELECT id FROM sbo_odm_invalid_datasets)))
  ORDER BY d.id;


ALTER TABLE public.seriescatalog OWNER TO "schwingbach-user";

--
-- Name: VIEW seriescatalog; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON VIEW seriescatalog IS 'WHERE clause excludes odm incompatible valuetypes / incompatible rows broadly speaking';


--
-- PostgreSQL database dump complete
--

