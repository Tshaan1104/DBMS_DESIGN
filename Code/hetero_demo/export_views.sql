-- Export schemas: one per site, each defined over that site's OWN tables.
-- The mediator unions them into the global relation CARGO_IN_CUSTODY (GAV).

-- s1: New Mangalore
CREATE VIEW export_custody AS
  SELECT 1 AS port_id, 'CONTAINER' AS cargo_class,
         COALESCE(SUM(gross_wt), 0) / 1000.0 AS tonnes FROM container_c
  UNION ALL
  SELECT 1, 'LIQUID_BULK',                        -- kilolitres x density (t/m3) = tonnes
         COALESCE(SUM(current_kl * current_density), 0) FROM tank_farm;

-- s2: JNPT
CREATE VIEW export_custody AS
  SELECT 2 AS port_id, 'CONTAINER' AS cargo_class,
         COALESCE(SUM(gross_wt), 0) / 1000.0 AS tonnes FROM container_c
  UNION ALL
  SELECT 2, 'CONTAINER_ON_RAIL',                  -- rail weighment, until the rake departs
         COALESCE(SUM(rl.gross_wt), 0) / 1000.0
    FROM rake_loading rl JOIN rail_rake r ON r.rake_id = rl.rake_id
   WHERE r.departure_ts IS NULL;

-- s3: Chennai
CREATE VIEW export_custody AS
  SELECT 3 AS port_id, 'CONTAINER' AS cargo_class,
         COALESCE(SUM(gross_wt), 0) / 1000.0 AS tonnes FROM container_c
  UNION ALL
  SELECT 3, 'RORO',                               -- manifest weight, until the voyage sails
         COALESCE(SUM(v.weight_kg), 0) / 1000.0
    FROM roro_vehicle v JOIN voyage y ON y.voyage_id = v.voyage_id
   WHERE y.atd IS NULL;

-- s4: Kolkata/Haldia
CREATE VIEW export_custody AS
  SELECT 4 AS port_id, 'CONTAINER' AS cargo_class,
         COALESCE(SUM(gross_wt), 0) / 1000.0 AS tonnes FROM container_c
  UNION ALL
  SELECT 4, 'CONTAINER_AFLOAT',                   -- barge manifest, until the barge lands
         COALESCE(SUM(cargo_tonnes), 0) FROM lighterage WHERE end_ts IS NULL;

-- Mediator (global layer)
CREATE VIEW cargo_in_custody AS
  SELECT * FROM s1.export_custody UNION ALL SELECT * FROM s2.export_custody
  UNION ALL SELECT * FROM s3.export_custody UNION ALL SELECT * FROM s4.export_custody;

-- Q9
SELECT port_id, cargo_class, SUM(tonnes)
  FROM cargo_in_custody
 GROUP BY port_id, cargo_class;
