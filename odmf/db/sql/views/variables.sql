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

DROP VIEW IF EXISTS variables;

CREATE OR REPLACE VIEW variables AS
  SELECT
    variablecode,
    variableid,
    variablename,
    speciation,
    variableunitsid,
    samplemedium,
    valuetype,
    isregular,
    timesupport,
    timeunitsid,
    datatype,
    generalcategory,
    nodatavalue
    FROM _variables;

ALTER TABLE public.variables OWNER TO "schwingbach-user";

--
-- Name: VIEW variables; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON VIEW variables IS 'WHERE clause excludes odm incompatible valuetypes';

--
-- PostgreSQL database dump complete
--

