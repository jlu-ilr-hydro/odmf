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
-- Name: topiccategorycv; Type: TABLE; Schema: public; Owner: schwingbach-user; Tablespace: 
--

CREATE TABLE topiccategorycv (
    term character varying(255) NOT NULL,
    definition character varying
);


ALTER TABLE public.topiccategorycv OWNER TO "schwingbach-user";

--
-- Name: TABLE topiccategorycv; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON TABLE topiccategorycv IS '*** Controlled Vocabulary WOF interface required ***';


--
-- Name: COLUMN topiccategorycv.definition; Type: COMMENT; Schema: public; Owner: schwingbach-user
--

COMMENT ON COLUMN topiccategorycv.definition IS 'Definition of the TopicCategory controlled vocabulary term. The definition is 
optional if the term is self explanatory.';


--
-- Name: topiccategorycv_pkey; Type: CONSTRAINT; Schema: public; Owner: schwingbach-user; Tablespace: 
--

ALTER TABLE ONLY topiccategorycv
    ADD CONSTRAINT topiccategorycv_pkey PRIMARY KEY (term);


--
-- PostgreSQL database dump complete
--

