-- offsettypes from odm 1.1

DROP TABLE IF EXISTS wof_offsettypes;

CREATE TABLE wof_offsettypes (
  offsettypeid integer,
  offsetunitsid integer,
  offsetdescription varchar
);

DROP VIEW IF EXISTS offsettypes;

CREATE VIEW offsettypes AS
    SELECT 
     offsettypeid,
     offsetunitsid,
     offsetdescription
    FROM
     wof_offsettypes;

-- TODO: Not NULL

INSERT INTO wof_offsettypes (offsettypeid, offsetunitsid, offsetdescription) VALUES
  (0, 52, 'Vertical displacement in meters. Positive means up');
