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

DROP VIEW IF EXISTS sites;

CREATE VIEW sites AS
 SELECT s.id AS siteid,
    s.id::character varying AS sitecode,
    s.name AS sitename,
    s.lat AS latitude,
    s.lon AS longitude,
    NULL::real AS localx, -- can be null after spec
    NULL::real AS localy, -- can be null after spec
    s.height AS elevation_m,
    'Unknown'::character varying AS verticaldatum,
    'Hessen'::character varying AS state,
    'Giessen'::character varying AS county,
    -- removes newlines and carriage returns
    regexp_replace(s.comment, E'[\\n\\r]+', ' ', 'g' )::text AS comments,
    NULL::real AS posaccuracy_m, -- can be null after spec
    3 AS latlongdatumid,
    3 AS localprojectionid
   FROM site s
  JOIN dataset d ON (s.id = d.site
                 AND d.id NOT IN (SELECT id FROM sbo_odm_invalid_datasets)
                 AND d.valuetype NOT IN (SELECT id FROM sbo_odm_invalid_valuetypes))
  JOIN series ss ON (d.id = ss.dataset
                 AND ss.count > 0)
  GROUP BY s.id
  ORDER BY s.id;

ALTER VIEW sites OWNER TO "schwingbach-user";

--
-- PostgreSQL database dump complete
--

