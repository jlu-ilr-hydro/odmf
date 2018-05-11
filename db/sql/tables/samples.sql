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

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: samples; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE samples (
    sampleid integer,
    sampletype integer,
    labsamplecode text,
    labmethodid integer
);


ALTER TABLE public.samples OWNER TO "schwingbach-user";

--
-- PostgreSQL database dump complete
--

