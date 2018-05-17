-- person TABLE customization
ALTER TABLE person ADD COLUMN street varchar(64);
ALTER TABLE person ADD COLUMN city varchar(64);
ALTER TABLE person ADD COLUMN postcode varchar(64);
ALTER TABLE person ADD COLUMN country varchar(64);

-- create config
CREATE TABLE configuration (
  key varchar(64) NOT NULL,
  value varchar NOT NULL,
  CONSTRAINT pkey_configuration_key PRIMARY KEY (key)
)

-- update config
INSERT INTO configuration VALUES ('institute.street', 'Heinrich Buff Ring 24');
INSERT INTO configuration VALUES ('institute.postcode', '35390');
INSERT INTO configuration VALUES ('institute.city', 'Gießen');
INSERT INTO configuration VALUES ('institute.country', 'Germany');


