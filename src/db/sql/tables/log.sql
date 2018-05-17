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
-- Name: log; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE log (
    id integer NOT NULL,
    "time" timestamp without time zone,
    "user" character varying,
    message character varying,
    site integer,
    type character varying(30)
);


ALTER TABLE public.log OWNER TO "schwingbach-user";

--
-- Name: TABLE log; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE log IS 'A log book for actions and observations at sites';


--
-- Name: COLUMN log.type; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN log.type IS 'Type of the log entry';


--
-- Name: log_id_seq; Type: SEQUENCE; Schema: public; Owner: schwingbach-user
--

CREATE SEQUENCE log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.log_id_seq OWNER TO "schwingbach-user";

--
-- Name: log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: schwingbach-user
--

ALTER SEQUENCE log_id_seq OWNED BY log.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY log ALTER COLUMN id SET DEFAULT nextval('log_id_seq'::regclass);


--
-- Name: log_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY log
    ADD CONSTRAINT log_pkey PRIMARY KEY (id);


--
-- Name: log_time_index; Type: INDEX; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE INDEX log_time_index ON log USING btree ("time" DESC);


--
-- Name: log_site_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY log
    ADD CONSTRAINT log_site_fkey FOREIGN KEY (site) REFERENCES site(id) ON UPDATE SET NULL ON DELETE SET NULL;


--
-- Name: log_user_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY log
    ADD CONSTRAINT log_user_fkey FOREIGN KEY ("user") REFERENCES person(username);


--
-- PostgreSQL database dump complete
--

