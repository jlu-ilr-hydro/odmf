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
-- Name: datacollectionmethod; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE datacollectionmethod (
    id integer NOT NULL,
    description character varying,
    link character varying
);


ALTER TABLE public.datacollectionmethod OWNER TO "schwingbach-user";

--
-- Name: TABLE datacollectionmethod; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE datacollectionmethod IS 'Template for the ODM Methods Table';


--
-- Name: COLUMN datacollectionmethod.description; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN datacollectionmethod.description IS 'Describes the method of datacollection';


--
-- Name: COLUMN datacollectionmethod.link; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN datacollectionmethod.link IS 'A URL to a document describing the method';


--
-- Name: datacollectionmethod_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY datacollectionmethod
    ADD CONSTRAINT datacollectionmethod_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

