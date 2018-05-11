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
-- Name: person; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE person (
    username character varying NOT NULL,
    email character varying,
    firstname character varying,
    surname character varying,
    supervisor character varying,
    telephone character varying,
    comment character varying,
    can_supervise boolean,
    mobile character varying,
    car_available integer,
    password character varying,
    active boolean,
    access_level integer,
    street character varying(64),
    city character varying(64),
    postcode character varying(64),
    country character varying(64),
    title character varying(32),
    phone character varying
);


ALTER TABLE public.person OWNER TO "schwingbach-user";

--
-- Name: TABLE person; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE person IS 'The database users';


--
-- Name: COLUMN person.street; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN person.street IS '**CUAHSI WOF Interface**';


--
-- Name: COLUMN person.city; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN person.city IS '**CUAHSI WOF Interface**';


--
-- Name: COLUMN person.postcode; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN person.postcode IS '**CUAHSI WOF Interface**';


--
-- Name: COLUMN person.country; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN person.country IS '**CUAHSI WOF Interface**';


--
-- Name: COLUMN person.title; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN person.title IS '**CUAHSI WOF Interface**';


--
-- Name: COLUMN person.phone; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN person.phone IS '**CUAHSI WOF Interface** Instead of publishing mobile phone number';


--
-- Name: person_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY person
    ADD CONSTRAINT person_pkey PRIMARY KEY (username);


--
-- Name: person_supervisor_fkey; Type: FK CONSTRAINT; Schema: public; Owner: schwingbach-user
--

ALTER TABLE ONLY person
    ADD CONSTRAINT person_supervisor_fkey FOREIGN KEY (supervisor) REFERENCES person(username);


--
-- PostgreSQL database dump complete
--

