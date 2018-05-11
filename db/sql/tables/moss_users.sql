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
-- Name: moss_users; Type: TABLE; Schema: public; Owner: gh1961; Tablespace: 
--

CREATE TABLE moss_users (
    firstname character varying(50) NOT NULL,
    lastname character varying(50) NOT NULL,
    username character varying(25) NOT NULL,
    password character varying(100) NOT NULL,
    authority moss_roles NOT NULL
);


ALTER TABLE public.moss_users OWNER TO gh1961;

--
-- PostgreSQL database dump complete
--

