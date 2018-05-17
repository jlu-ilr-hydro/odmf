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
-- Name: methods; Type: VIEW; Schema: public; Owner: schwingbach-user
--

CREATE VIEW methods AS
 SELECT d.id AS methodid,
    d.description AS methoddescription,
    d.link AS methodlink
   FROM datacollectionmethod d;


ALTER TABLE public.methods OWNER TO "schwingbach-user";

--
-- PostgreSQL database dump complete
--

