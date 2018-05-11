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
-- Name: quality; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE quality (
    id integer NOT NULL,
    name character varying,
    comment character varying
);


ALTER TABLE public.quality OWNER TO "schwingbach-user";

--
-- Name: TABLE quality; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE quality IS 'Quality of data in a dataset';


--
-- Name: quality_id_seq; Type: SEQUENCE; Schema: public; Owner: schwingbach-user
--

CREATE SEQUENCE quality_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.quality_id_seq OWNER TO "schwingbach-user";

--
-- Name: quality_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: schwingbach-user
--

ALTER SEQUENCE quality_id_seq OWNED BY quality.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY quality ALTER COLUMN id SET DEFAULT nextval('quality_id_seq'::regclass);


--
-- Name: quality_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY quality
    ADD CONSTRAINT quality_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

