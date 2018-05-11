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
-- Name: qualitycontrollevels; Type: VIEW; Schema: public; Owner: schwingbach-user
--

CREATE VIEW qualitycontrollevels AS
 SELECT quality.id AS qualitycontrollevelid,
    (quality.id)::character varying(50) AS qualitycontrollevelcode,
    quality.name AS definition,
    quality.comment AS explanation
   FROM quality;


ALTER TABLE public.qualitycontrollevels OWNER TO "schwingbach-user";

--
-- PostgreSQL database dump complete
--

