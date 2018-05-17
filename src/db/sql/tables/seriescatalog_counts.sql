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
-- Name: seriescatalog_counts; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE seriescatalog_counts (
    siteid integer NOT NULL,
    variableid integer NOT NULL,
    methodid integer NOT NULL,
    sourceid integer NOT NULL,
    qualitycontrollevelid integer NOT NULL,
    count integer NOT NULL,
    last_update timestamp without time zone,
    update_length interval
);


ALTER TABLE public.seriescatalog_counts OWNER TO "schwingbach-user";

--
-- Name: seriescatalog_counts_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY seriescatalog_counts
    ADD CONSTRAINT seriescatalog_counts_pkey PRIMARY KEY (siteid, variableid, methodid, sourceid, qualitycontrollevelid);


--
-- PostgreSQL database dump complete
--

