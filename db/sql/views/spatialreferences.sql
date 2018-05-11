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
-- Name: spatialreferences; Type: VIEW; Schema: public; Owner: schwingbach-user
--

CREATE VIEW spatialreferences AS
 SELECT 3 AS spatialreferenceid,
    4326 AS srsid,
    'WGS84'::character varying AS srsname;


ALTER TABLE public.spatialreferences OWNER TO "schwingbach-user";

--
-- PostgreSQL database dump complete
--

