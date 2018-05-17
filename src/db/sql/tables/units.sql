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
-- Name: units; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE units (
    unitsid integer NOT NULL,
    unitsname character varying(255),
    unitstype character varying(255),
    unitsabbreviation character varying(255)
);


ALTER TABLE public.units OWNER TO "schwingbach-user";

--
-- Name: TABLE units; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE units IS '*** Controlled Vocabulary WOF interface required ***';


--
-- Name: units_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY units
    ADD CONSTRAINT units_pkey PRIMARY KEY (unitsid);


--
-- PostgreSQL database dump complete
--

