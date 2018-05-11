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
-- Name: verticaldatumcv; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE verticaldatumcv (
    term character varying(255) NOT NULL,
    definition character varying
);


ALTER TABLE public.verticaldatumcv OWNER TO "schwingbach-user";

--
-- Name: TABLE verticaldatumcv; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE verticaldatumcv IS '*** Controlled Vocabulary WOF interface required ***';


--
-- Name: COLUMN verticaldatumcv.definition; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN verticaldatumcv.definition IS 'Definition of the VerticalDatum controlled vocabulary term. The definition is 
optional if the term is self explanatory.';


--
-- Name: verticaldatumcv_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY verticaldatumcv
    ADD CONSTRAINT verticaldatumcv_pkey PRIMARY KEY (term);


--
-- PostgreSQL database dump complete
--

