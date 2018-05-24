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
-- Name: project; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE project (
    id integer NOT NULL,
    name character varying NOT NULL,
    person_responsible character varying NOT NULL,
    comment character varying,
    citation character varying,
    organization character varying,
    sourcelink character varying
);


ALTER TABLE public.project OWNER TO "schwingbach-user";

--
-- Name: TABLE project; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE project IS 'Special information for a project';


--
-- Name: project_id_seq; Type: SEQUENCE; Schema: public; Owner: schwingbach-user
--

CREATE SEQUENCE project_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.project_id_seq OWNER TO "schwingbach-user";

--
-- Name: project_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: schwingbach-user
--

ALTER SEQUENCE project_id_seq OWNED BY project.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY project ALTER COLUMN id SET DEFAULT nextval('project_id_seq'::regclass);


--
-- Name: project_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY project
    ADD CONSTRAINT project_pkey PRIMARY KEY (id);


--
-- Name: project_person_responsible_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY project
    ADD CONSTRAINT project_person_responsible_fkey FOREIGN KEY (person_responsible) REFERENCES person(username);


--
-- PostgreSQL database dump complete
--

