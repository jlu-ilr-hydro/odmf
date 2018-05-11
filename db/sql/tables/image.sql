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
-- Name: image; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE image (
    id integer NOT NULL,
    name character varying,
    "time" timestamp without time zone,
    mime character varying,
    site integer,
    by character varying,
    image bytea,
    thumbnail bytea
);


ALTER TABLE public.image OWNER TO "schwingbach-user";

--
-- Name: TABLE image; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE image IS 'Contains photos from the study area with date, site and author';


--
-- Name: image_id_seq; Type: SEQUENCE; Schema: public; Owner: schwingbach-user
--

CREATE SEQUENCE image_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.image_id_seq OWNER TO "schwingbach-user";

--
-- Name: image_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: schwingbach-user
--

ALTER SEQUENCE image_id_seq OWNED BY image.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY image ALTER COLUMN id SET DEFAULT nextval('image_id_seq'::regclass);


--
-- Name: image_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY image
    ADD CONSTRAINT image_pkey PRIMARY KEY (id);


--
-- Name: image_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY image
    ADD CONSTRAINT image_by_fkey FOREIGN KEY (by) REFERENCES person(username);


--
-- Name: image_site_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY image
    ADD CONSTRAINT image_site_fkey FOREIGN KEY (site) REFERENCES site(id);


--
-- PostgreSQL database dump complete
--

