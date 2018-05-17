-- script to extend the schwingbach database tables to
-- serve the same information as the odm schema

ALTER TABLE valuetype
    ADD COLUMN cv_variable_name varchar(32) default NULL,
    ADD COLUMN cv_speciation varchar(32) default 'Not Applicable',
    ADD COLUMN cv_sample_medium varchar(32) default 'Not Relevant',
    ADD COLUMN cv_general_category varchar(32) default 'Hydrology',
    ADD COLUMN cv_unit varchar(32) default NULL;

ALTER TABLE dataset
    ADD COLUMN cv_valuetype varchar(32) default 'Unknown',
    ADD COLUMN cv_datatype varchar(32) default 'Sporadic';

-- Creating views to grant applications access, that implement the odm schema

CREATE VIEW variable AS
    SELECT distinct CONCAT(v.id, '-', UPPER(d.cv_datatype)) as variable_id, v.*, d.cv_valuetype, d.cv_datatype 
      FROM dataset d, valuetype v 
      WHERE d.valuetype = v.id 
      ORDER BY id;


CREATE VIEW Variables AS
  SELECT
    distinct CONCAT(v.id, '-', UPPER(d.cv_datatype)) as VariableID,  -- PK
    NULL as VariableCode,
    v.cv_variable_name as VariableName,
    v.cv_speciation as Speciation,
    v.cv_unit as VariableUnitsID, -- FK
    v.cv_sample_medium as SampleMedium,
    d.cv_valuetype as ValueType,
    False as IsRegular,
    NULL as TimeSupport,
    NULL as TimeUnitsID,
    d.cv_datatype as DataType,
    v.cv_general_category as GeneralCategory,
    NULL as NoDataValue
  FROM dataset d, valuetype v
  WHERE d.valuetype = v.id;

CREATE VIEW DataValues AS
  SELECT
    r.id as ValueID, -- PK
    r.value as DataValue,
    r.time as LocalDateTime,
    1 as UTCOffset, -- utc offset with dst is 2
    r.time + time '01:00' as DateTimeUTC, --
    d.site as SiteID, -- FK
    CONCAT(d.valuetype, '-', UPPER(d.cv_datatype)) as VariableID,
    'nc' as CensorCode,
    d.datacollectionmethod as MethodID,
    d.project as SourceID,
    d.quality as QualityControlLevelID
  FROM record r, dataset d
  WHERE r.dataset = d.id;

CREATE VIEW Methods AS
  SELECT
    d.id as MethodID,
    d.description as MethodDescription,
    d.link as MethodLink
 FROM datacollectionmethod d;

-- CREATE VIEW OffsetTypes AS
-- correlates with datavalues


CREATE OR REPLACE VIEW "`sites`" AS
  SELECT
    s.id as "SiteID", -- PK
    s.id as siteid, -- PK
    CONCAT('Schwingbach-', s.id) as "SiteCode", -- See Documentation TODO: MAKE CONSTANT, write to documentation
    s.name as "SiteName",
    s.lat as "Latitude",
    s.lon AS "Longitude",
    s.lat AS "LocalX",
    s.lon AS "LocalY",
    s.height AS "Elevation_m",
    NULL AS "VerticalDatum",
    NULL AS "State",
    NULL AS "County",
    NULL AS "Comments",
    NULL AS "PosAccuracy_m",
    3 AS "LatLongDatumID", -- See Documentation TODO: write to documentation
    3 AS "LocalProjectionID"
  FROM site s;

CREATE VIEW Sources AS
  SELECT
    p.id AS "SourceID", -- PK
    'JLU FB09 ILR' AS "Organization",
    p.comment AS "SourceDescription",
    'Dr. Philipp Kraft' AS "ContactName",
    '+49641-9937554' AS "Phone",
    'philipp.kraft@umwelt.uni-giessen.de' AS "Email",
    'Heinrich-Buff-Ring 26' AS Adress,
    'Gießen' AS City,
    'Rhineland-Palatinate' AS State,
    '35392' AS ZipCode,
    NULL AS Citation,
    NULL AS MetaDataID -- FK
  FROM project p;

CREATE VIEW QualityControlLevels AS
  SELECT
    id as QualityControlLevelID, -- PK
    NULL as QualityControlLevelCode,
    name as Definition,
    comment as Explanation
  FROM quality;

-- CREATE VIEW Samples AS
--   SELECT
--     NULL as SampleID, -- PK
--     'Unknown' as SampleType,
--     r.sample as LabSampleCode,
--     0 as LabMethodID -- FK
--   FROM record r
--   WHERE r.sample is not NULL;

-- CREATE VIEW LabMethods AS
--SELECT
--  d.id as LabMethodID, -- PK
--FROM datacollectionmethod d;

--
-- Refers to view SeriesCatalog in ODM 1.1
--

CREATE VIEW seriescatalog AS  SELECT
    d.id as seriesid,
    d.site as "SiteId",
    s.id as sitecode,
    s.name as sitename,
    d.valuetype as variableid,
    v.name as variablename,
    v.cv_speciation as speciation,
    v.cv_unit AS variableunitsid,
    --d.variableunitsname,
    v.cv_sample_medium as samplemedium,
    -- timesupport,
    -- timeunitsid,
    -- timeunitsname,
    -- datatype
    -- generalcategory
    d.datacollectionmethod AS methodid,
    dm.description AS methoddescription,
    --d.sourceid AS sourceid,
    --sc.organization as organization,
    --sc.description AS sourcedescription,
    --sc.citation as citation,
    d.quality as qualitycontrollevelid,
    q.name as qualitycontrollevelcode
    -- begin date time
    -- end date time
    -- begin date time utc
    -- end date time utc
    -- value count
FROM dataset d
  LEFT JOIN site s ON d.site = s.id
  LEFT JOIN valuetype v ON d.valuetype = v.id
  LEFT JOIN quality q ON d.quality = q.id
  LEFT JOIN datacollectionmethod dm ON d.datacollectionmethod = dm.id;
  --LEFT JOIN source sc ON d.sourceid = sc.id

-- Controlled Vocabularies

-- ALTER TABLE site

CREATE OR REPLACE VIEW "`spatialreferences`" AS
    SELECT int '3' AS "SpatialReferenceID",
	   int '4326' AS "SRSID",
           varchar 'WGS84' AS "SRSName";


CREATE OR REPLACE VIEW "`speciationcv`" AS
    SELECT DISTINCT cv_speciation as "Term" FROM valuetype;

  CREATE OR REPLACE VIEW "`samplemediumcv`" AS
    SELECT DISTINCT cv_sample_medium as "Term" FROM valuetype;