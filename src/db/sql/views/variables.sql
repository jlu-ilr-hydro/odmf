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
-- Name: variables; Type: VIEW; Schema: public; Owner: schwingbach-user
--

CREATE VIEW variables AS
 SELECT DISTINCT concat(v.id, '-', upper((d.cv_datatype)::text)) AS variablecode,
    v.id AS variableid,
    v.cv_variable_name AS variablename,
    v.cv_speciation AS speciation,
    v.cv_unit AS variableunitsid,
    v.cv_sample_medium AS samplemedium,
    d.cv_valuetype AS valuetype,
    false AS isregular,
    0 AS timesupport,
    103 AS timeunitsid,
    d.cv_datatype AS datatype,
    v.cv_general_category AS generalcategory,
    '-9999'::text AS nodatavalue
   FROM dataset d,
    valuetype v
  WHERE ((d.valuetype = v.id) AND (v.id <> 30))
  ORDER BY v.id;


ALTER TABLE public.variables OWNER TO "schwingbach-user";

--
-- Name: VIEW variables; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON VIEW variables IS 'WHERE clause excludes odm incompatible valuetypes';


--
-- PostgreSQL database dump complete
--

