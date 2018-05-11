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
-- Name: configuration; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE configuration (
    key character varying(64) NOT NULL,
    value character varying NOT NULL
);


ALTER TABLE public.configuration OWNER TO "schwingbach-user";

--
-- Name: pkey_configuration_key; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY configuration
    ADD CONSTRAINT pkey_configuration_key PRIMARY KEY (key);


--
-- PostgreSQL database dump complete
--

