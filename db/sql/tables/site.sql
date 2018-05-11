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
-- Name: site; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE site (
    id integer NOT NULL,
    lat double precision,
    lon double precision,
    height double precision,
    name character varying,
    comment character varying,
    icon character varying(30)
);


ALTER TABLE public.site OWNER TO "schwingbach-user";

--
-- Name: TABLE site; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE site IS 'Sites in the study area. The sites are intended for reuse. Single measurement plots, should be saved as a geometry';


--
-- Name: site_id_seq; Type: SEQUENCE; Schema: public; Owner: schwingbach-user
--

CREATE SEQUENCE site_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.site_id_seq OWNER TO "schwingbach-user";

--
-- Name: site_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: schwingbach-user
--

ALTER SEQUENCE site_id_seq OWNED BY site.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY site ALTER COLUMN id SET DEFAULT nextval('site_id_seq'::regclass);


--
-- Name: site_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY site
    ADD CONSTRAINT site_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

