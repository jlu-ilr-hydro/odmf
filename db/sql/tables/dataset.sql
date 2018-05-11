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
-- Name: dataset; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE dataset (
    id integer NOT NULL,
    name character varying NOT NULL,
    filename character varying,
    start timestamp without time zone,
    "end" timestamp without time zone,
    source integer,
    site integer,
    valuetype integer,
    measured_by character varying,
    quality integer DEFAULT 0,
    comment character varying,
    calibration_offset double precision DEFAULT 0.0 NOT NULL,
    calibration_slope double precision DEFAULT 1.0 NOT NULL,
    type character varying(50),
    uses_dst boolean DEFAULT false NOT NULL,
    level double precision,
    access integer DEFAULT 1 NOT NULL,
    project integer,
    timezone character varying,
    cv_valuetype character varying(32) DEFAULT 'Unknown'::character varying,
    cv_datatype character varying(32) DEFAULT 'Sporadic'::character varying,
    datacollectionmethod integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.dataset OWNER TO "schwingbach-user";

--
-- Name: TABLE dataset; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE dataset IS 'Holds the meta data for a set of records. Can be of type "timeseries" "transformation" or "geodataset"';


--
-- Name: COLUMN dataset.type; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN dataset.type IS 'Describes the type of the dataset. Can be one of ''timeseries'',''derived_timeseries'' or ''geodataset''';


--
-- Name: COLUMN dataset.uses_dst; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN dataset.uses_dst IS 'Indicates, if the records of the dataset uses day light saving time (dst).
If false, the time is considered to be in timezone Berlin, winter time';


--
-- Name: COLUMN dataset.level; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN dataset.level IS 'Level of measurement in m. Below ground is negative, above ground positive';


--
-- Name: COLUMN dataset.access; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN dataset.access IS 'Indicates the user level, this dataset can be accessed: 0 (public/guest), 1 (logger), 2 (editor), 3 (supervisor), 4 (admin)';


--
-- Name: COLUMN dataset.project; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN dataset.project IS 'Foreign Key to project table';


--
-- Name: dataset_id_seq; Type: SEQUENCE; Schema: public; Owner: schwingbach-user
--

CREATE SEQUENCE dataset_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dataset_id_seq OWNER TO "schwingbach-user";

--
-- Name: dataset_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: schwingbach-user
--

ALTER SEQUENCE dataset_id_seq OWNED BY dataset.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY dataset ALTER COLUMN id SET DEFAULT nextval('dataset_id_seq'::regclass);


--
-- Name: dataset_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY dataset
    ADD CONSTRAINT dataset_pkey PRIMARY KEY (id);


--
-- Name: fki_dataset_project_fkey; Type: INDEX; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE INDEX fki_dataset_project_fkey ON dataset USING btree (project);


--
-- Name: dataset_datacollectionmethod_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY dataset
    ADD CONSTRAINT dataset_datacollectionmethod_fkey FOREIGN KEY (datacollectionmethod) REFERENCES datacollectionmethod(id) ON UPDATE CASCADE ON DELETE SET DEFAULT;


--
-- Name: dataset_measured_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY dataset
    ADD CONSTRAINT dataset_measured_by_fkey FOREIGN KEY (measured_by) REFERENCES person(username);


--
-- Name: dataset_project_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY dataset
    ADD CONSTRAINT dataset_project_fkey FOREIGN KEY (project) REFERENCES project(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: dataset_quality_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY dataset
    ADD CONSTRAINT dataset_quality_fkey FOREIGN KEY (quality) REFERENCES quality(id);


--
-- Name: dataset_site_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY dataset
    ADD CONSTRAINT dataset_site_fkey FOREIGN KEY (site) REFERENCES site(id);


--
-- Name: dataset_source_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY dataset
    ADD CONSTRAINT dataset_source_fkey FOREIGN KEY (source) REFERENCES datasource(id);


--
-- Name: dataset_valuetype_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY dataset
    ADD CONSTRAINT dataset_valuetype_fkey FOREIGN KEY (valuetype) REFERENCES valuetype(id);


--
-- PostgreSQL database dump complete
--

