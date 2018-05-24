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
-- Name: sampletypecv; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE sampletypecv (
    term character varying(255) NOT NULL,
    definition character varying
);


ALTER TABLE public.sampletypecv OWNER TO "schwingbach-user";

--
-- Name: TABLE sampletypecv; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE sampletypecv IS '*** Controlled Vocabulary WOF interface required ***';


--
-- Name: COLUMN sampletypecv.definition; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN sampletypecv.definition IS 'Definition of the SampleType controlled vocabulary term. The definition is 
optional if the term is self explanatory.';


--
-- Name: sampletypecv_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY sampletypecv
    ADD CONSTRAINT sampletypecv_pkey PRIMARY KEY (term);


--
-- PostgreSQL database dump complete
--

