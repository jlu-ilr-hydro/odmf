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
-- Name: record; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE record (
    id integer NOT NULL,
    dataset integer NOT NULL,
    "time" timestamp without time zone,
    value double precision,
    sample character varying,
    comment character varying,
    is_error boolean DEFAULT false NOT NULL
);


ALTER TABLE public.record OWNER TO "schwingbach-user";

--
-- Name: TABLE record; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE record IS 'A single measurement of a dataset (timeseries)';


--
-- Name: COLUMN record.is_error; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN record.is_error IS 'Make true, if this record is a fault measurement.';


--
-- Name: record_id_seq; Type: SEQUENCE; Schema: public; Owner: schwingbach-user
--

CREATE SEQUENCE record_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.record_id_seq OWNER TO "schwingbach-user";

--
-- Name: record_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: schwingbach-user
--

ALTER SEQUENCE record_id_seq OWNED BY record.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY record ALTER COLUMN id SET DEFAULT nextval('record_id_seq'::regclass);


--
-- Name: record_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY record
    ADD CONSTRAINT record_pkey PRIMARY KEY (id, dataset);


--
-- Name: record-dataset-time-index; Type: INDEX; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE INDEX "record-dataset-time-index" ON record USING btree (dataset, "time" DESC);


--
-- Name: record_dataset_index; Type: INDEX; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE INDEX record_dataset_index ON record USING btree (dataset);


--
-- Name: record_dataset_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY record
    ADD CONSTRAINT record_dataset_fkey FOREIGN KEY (dataset) REFERENCES dataset(id);


--
-- PostgreSQL database dump complete
--

