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
-- Name: sites; Type: VIEW; Schema: public; Owner: schwingbach-user
--

CREATE VIEW sites AS
 SELECT s.id AS siteid,
    s.id AS sitecode,
    s.name AS sitename,
    s.lat AS latitude,
    s.lon AS longitude,
    NULL::real AS localx,
    NULL::real AS localy,
    s.height AS elevation_m,
    'Unknown'::character varying AS verticaldatum,
    'Hessen'::character varying AS state,
    'Giessen'::character varying AS county,
    (s.comment)::text AS comments,
    NULL::real AS posaccuracy_m,
    3 AS latlongdatumid,
    3 AS localprojectionid
   FROM site s
  ORDER BY s.id;


ALTER TABLE public.sites OWNER TO "schwingbach-user";

--
-- PostgreSQL database dump complete
--

