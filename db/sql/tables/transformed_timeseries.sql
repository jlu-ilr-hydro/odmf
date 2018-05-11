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
-- Name: transformed_timeseries; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE transformed_timeseries (
    id integer NOT NULL,
    expression character varying,
    latex character varying
);


ALTER TABLE public.transformed_timeseries OWNER TO "schwingbach-user";

--
-- Name: TABLE transformed_timeseries; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE transformed_timeseries IS 'A specialization of Dataset. Uses type for polymorphic discremination.';


--
-- Name: COLUMN transformed_timeseries.id; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN transformed_timeseries.id IS 'Primary key and Foreign key to dataset';


--
-- Name: COLUMN transformed_timeseries.expression; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN transformed_timeseries.expression IS 'A valid python/numpy expression. x is an array containing the values from the source datasets';


--
-- Name: COLUMN transformed_timeseries.latex; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN transformed_timeseries.latex IS 'Latex code to print the transformation nicely';


--
-- Name: transformed_timeseries_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY transformed_timeseries
    ADD CONSTRAINT transformed_timeseries_pkey PRIMARY KEY (id);


--
-- Name: PFK_transformed_dataset; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY transformed_timeseries
    ADD CONSTRAINT "PFK_transformed_dataset" FOREIGN KEY (id) REFERENCES dataset(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

