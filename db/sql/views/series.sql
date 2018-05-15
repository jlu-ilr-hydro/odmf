-- Materialized View: series

-- DROP MATERIALIZED VIEW series;

CREATE MATERIALIZED VIEW series AS
 SELECT 0 AS count,
    d.id AS dataset
   FROM record r
     RIGHT JOIN dataset d ON r.dataset = d.id
  WHERE r.id IS NULL
UNION
 SELECT count(*) AS count,
    d.id AS dataset
   FROM record r
     RIGHT JOIN dataset d ON r.dataset = d.id
  WHERE r.id IS NOT NULL
  GROUP BY d.id
WITH DATA;

ALTER TABLE series
  OWNER TO "schwingbach-user";
