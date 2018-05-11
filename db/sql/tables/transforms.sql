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
-- Name: transforms; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE transforms (
    target integer NOT NULL,
    source integer NOT NULL,
    automatic_added boolean DEFAULT false
);


ALTER TABLE public.transforms OWNER TO "schwingbach-user";

--
-- Name: TABLE transforms; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE transforms IS 'n:n connection between timeseries and transformed_timeseries. Denotes the sources for the transformation';


--
-- Name: COLUMN transforms.target; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN transforms.target IS 'The target of the transformation';


--
-- Name: transforms_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY transforms
    ADD CONSTRAINT transforms_pkey PRIMARY KEY (target, source);


--
-- Name: transforms_source_idx; Type: INDEX; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE INDEX transforms_source_idx ON transforms USING btree (source);


--
-- Name: transforms_source_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY transforms
    ADD CONSTRAINT transforms_source_fkey FOREIGN KEY (source) REFERENCES dataset(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: transforms_target_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY transforms
    ADD CONSTRAINT transforms_target_fkey FOREIGN KEY (target) REFERENCES transformed_timeseries(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

