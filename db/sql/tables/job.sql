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
-- Name: job; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE job (
    id integer NOT NULL,
    name character varying,
    description character varying,
    due timestamp without time zone,
    author character varying,
    responsible character varying,
    done boolean,
    nextreminder timestamp without time zone,
    repeat integer,
    link character varying,
    type character varying(25),
    donedate timestamp without time zone
);


ALTER TABLE public.job OWNER TO "schwingbach-user";

--
-- Name: TABLE job; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE job IS 'Things to be done by users';


--
-- Name: COLUMN job.repeat; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN job.repeat IS 'Number of days until this job is repeated';


--
-- Name: COLUMN job.link; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN job.link IS 'A link to help the execution of the tasks';


--
-- Name: COLUMN job.type; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN job.type IS 'Type of the job';


--
-- Name: job_id_seq; Type: SEQUENCE; Schema: public; Owner: schwingbach-user
--

CREATE SEQUENCE job_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.job_id_seq OWNER TO "schwingbach-user";

--
-- Name: job_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: schwingbach-user
--

ALTER SEQUENCE job_id_seq OWNED BY job.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY job ALTER COLUMN id SET DEFAULT nextval('job_id_seq'::regclass);


--
-- Name: job_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY job
    ADD CONSTRAINT job_pkey PRIMARY KEY (id);


--
-- Name: job_author_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY job
    ADD CONSTRAINT job_author_fkey FOREIGN KEY (author) REFERENCES person(username);


--
-- Name: job_responsible_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY job
    ADD CONSTRAINT job_responsible_fkey FOREIGN KEY (responsible) REFERENCES person(username);


--
-- PostgreSQL database dump complete
--

