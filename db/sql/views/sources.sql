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
-- Name: sources; Type: VIEW; Schema: public; Owner: schwingbach-user
--

CREATE VIEW sources AS
 SELECT p.id AS sourceid,
    (p.organization)::character varying(255) AS organization,
    (p.comment)::character varying(255) AS sourcedescription,
    (p.sourcelink)::character varying(500) AS sourcelink,
    concat(pn.title, pn.firstname, ' ', pn.surname) AS contactname,
    (pn.phone)::character varying(255) AS phone,
    (pn.email)::character varying(255) AS email,
    (pn.street)::character varying(255) AS address,
    (pn.city)::character varying(255) AS city,
    (pn.country)::character varying(255) AS state,
    (pn.postcode)::character varying(255) AS zipcode,
    p.citation,
    NULL::integer AS metadataid
   FROM (project p
     LEFT JOIN person pn ON (((p.person_responsible)::text = (pn.username)::text)));


ALTER TABLE public.sources OWNER TO "schwingbach-user";

--
-- PostgreSQL database dump complete
--

