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
-- Name: datasource; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE datasource (
    id integer NOT NULL,
    name character varying NOT NULL,
    sourcetype character varying NOT NULL,
    comment character varying,
    manuallink text
);


ALTER TABLE public.datasource OWNER TO "schwingbach-user";

--
-- Name: TABLE datasource; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE datasource IS 'Describes the instrument or other datasources of a dataset';


--
-- Name: COLUMN datasource.manuallink; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN datasource.manuallink IS 'Contains the link to the manual';


--
-- Name: datasource_id_seq; Type: SEQUENCE; Schema: public; Owner: schwingbach-user
--

CREATE SEQUENCE datasource_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.datasource_id_seq OWNER TO "schwingbach-user";

--
-- Name: datasource_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: schwingbach-user
--

ALTER SEQUENCE datasource_id_seq OWNED BY datasource.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY datasource ALTER COLUMN id SET DEFAULT nextval('datasource_id_seq'::regclass);


--
-- Name: datasource_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY datasource
    ADD CONSTRAINT datasource_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

