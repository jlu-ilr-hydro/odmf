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
-- Name: valuetype; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE valuetype (
    id integer NOT NULL,
    name character varying,
    unit character varying,
    comment character varying,
    minvalue double precision,
    maxvalue double precision,
    cv_variable_name character varying(32) DEFAULT NULL::character varying,
    cv_speciation character varying(32) DEFAULT 'Not Applicable'::character varying,
    cv_sample_medium character varying(32) DEFAULT 'Not Relevant'::character varying,
    cv_general_category character varying(32) DEFAULT 'Hydrology'::character varying,
    cv_unit integer
);


ALTER TABLE public.valuetype OWNER TO "schwingbach-user";

--
-- Name: TABLE valuetype; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE valuetype IS 'Describes the meaning of a  value and holds the unit. Eg. Temperature (°C)';


--
-- Name: COLUMN valuetype.minvalue; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN valuetype.minvalue IS 'The lowest value of this value type. For sanity checks on records';


--
-- Name: COLUMN valuetype.maxvalue; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN valuetype.maxvalue IS 'The highest value of this value type. For sanity checks on records';


--
-- Name: valuetype_id_seq; Type: SEQUENCE; Schema: public; Owner: schwingbach-user
--

CREATE SEQUENCE valuetype_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.valuetype_id_seq OWNER TO "schwingbach-user";

--
-- Name: valuetype_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: schwingbach-user
--

ALTER SEQUENCE valuetype_id_seq OWNED BY valuetype.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY valuetype ALTER COLUMN id SET DEFAULT nextval('valuetype_id_seq'::regclass);


--
-- Name: valuetype_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY valuetype
    ADD CONSTRAINT valuetype_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

