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
-- Name: installation; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE installation (
    datasource_id integer NOT NULL,
    site_id integer NOT NULL,
    installation_id integer NOT NULL,
    installdate timestamp without time zone,
    removedate timestamp without time zone,
    comment character varying
);


ALTER TABLE public.installation OWNER TO "schwingbach-user";

--
-- Name: TABLE installation; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE installation IS 'The installation of an instrument (datasource) at a site. Has a set up and remove time';


--
-- Name: installation_installation_id_seq; Type: SEQUENCE; Schema: public; Owner: schwingbach-user
--

CREATE SEQUENCE installation_installation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.installation_installation_id_seq OWNER TO "schwingbach-user";

--
-- Name: installation_installation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: schwingbach-user
--

ALTER SEQUENCE installation_installation_id_seq OWNED BY installation.installation_id;


--
-- Name: installation_id; Type: DEFAULT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY installation ALTER COLUMN installation_id SET DEFAULT nextval('installation_installation_id_seq'::regclass);


--
-- Name: installation_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY installation
    ADD CONSTRAINT installation_pkey PRIMARY KEY (datasource_id, site_id, installation_id);


--
-- Name: installation_datasource_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY installation
    ADD CONSTRAINT installation_datasource_id_fkey FOREIGN KEY (datasource_id) REFERENCES datasource(id);


--
-- Name: installation_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY installation
    ADD CONSTRAINT installation_site_id_fkey FOREIGN KEY (site_id) REFERENCES site(id);


--
-- PostgreSQL database dump complete
--

