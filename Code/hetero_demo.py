#!/usr/bin/env python3
"""Executable demonstration of the heterogeneous distributed design.

Builds four SQLite databases — one per port — each with its OWN local conceptual schema:
the shared core fragments (identical everywhere) plus that port's local extensions
(different everywhere). Each site publishes an EXPORT VIEW over its own tables, defined
differently at each site. A mediator ATTACHes all four and answers Q9 through the global
GAV view CARGO_IN_CUSTODY.

Then it checks, with assertions, the properties the design claims:
  1. the local schemas are pairwise different
  2. the shared core is identical at every site
  3. Q9 through the global view equals the value computed independently
  4. custody is conserved across each port's own boundary events, i.e. no double counting
"""
import os
import random
import sqlite3

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hetero_demo")
os.makedirs(OUT, exist_ok=True)
random.seed(7)

SITES = {1: ("s1", "New Mangalore"), 2: ("s2", "JNPT"), 3: ("s3", "Chennai"),
         4: ("s4", "Kolkata/Haldia")}

# ------------------------------------------------------------------ shared core (identical DDL)
CORE = """
CREATE TABLE container_c (cont_id TEXT PRIMARY KEY, size_ft INT, cont_type TEXT, tare_wt INT,
    gross_wt INT, hazmat_class TEXT, line_id INT, consignee_id INT, invoice_value REAL,
    cur_port_id INT NOT NULL, voyage_id INT);
CREATE TABLE container_g (cont_id TEXT PRIMARY KEY REFERENCES container_c, seal_no TEXT,
    customs_status TEXT);
CREATE TABLE voyage (voyage_id INT PRIMARY KEY, vessel_id INT, port_id INT, eta TEXT, ata TEXT,
    atd TEXT, berth_no TEXT, status TEXT);
CREATE TABLE yard_block (port_id INT, block TEXT, has_power INT, max_tier INT,
    PRIMARY KEY (port_id, block));
CREATE TABLE yard_slot (port_id INT, block TEXT, bay INT, row INT, tier INT,
    cont_id TEXT UNIQUE, occupied_since TEXT, PRIMARY KEY (port_id, block, bay, row, tier));
CREATE TABLE gate_move (move_id INT PRIMARY KEY, cont_id TEXT, port_id INT, ts TEXT,
    direction TEXT, truck_no TEXT, gate_no INT, operator_id INT);
CREATE TABLE tariff (port_id INT, service_code TEXT, rate REAL, PRIMARY KEY (port_id, service_code));
CREATE TABLE customs_decl (decl_id INT PRIMARY KEY, cont_id TEXT UNIQUE, hs_code TEXT,
    duty_amt REAL, filed_on TEXT, cleared_on TEXT, officer_id INT);
CREATE TABLE bill_of_lading (bl_no TEXT PRIMARY KEY, voyage_id INT, consignee_id INT,
    cont_count INT, freight_amt REAL, issue_date TEXT);
CREATE TABLE container_reefer (cont_id TEXT PRIMARY KEY, set_point_temp INT, plug_id TEXT);
CREATE TABLE container_tank (cont_id TEXT PRIMARY KEY, un_number TEXT, last_cleaned_on TEXT);
CREATE TABLE container_open_top (cont_id TEXT PRIMARY KEY, over_height_cm INT);
CREATE TABLE port (port_id INT PRIMARY KEY, port_name TEXT, city TEXT, country TEXT, timezone TEXT);
CREATE TABLE shipping_line (line_id INT PRIMARY KEY, name TEXT, country TEXT, agent_name TEXT);
CREATE TABLE vessel (vessel_id INT PRIMARY KEY, name TEXT, imo_no TEXT, flag TEXT,
    capacity_teu INT, line_id INT);
CREATE TABLE service (service_code TEXT PRIMARY KEY, service_name TEXT, currency TEXT);
"""
# single-copy / partially replicated global relations (Section 11 allocation)
CONSIGNEE_H = "CREATE TABLE consignee_h (consignee_id INT PRIMARY KEY, name TEXT);"
S2_ONLY_GLOBAL = """
CREATE TABLE hs_code_master (hs_code TEXT PRIMARY KEY, hs_description TEXT, duty_rate REAL);
CREATE TABLE pincode (pincode TEXT PRIMARY KEY, city TEXT, state TEXT);
CREATE TABLE consignee_r (consignee_id INT PRIMARY KEY, street_line TEXT, area TEXT,
    pincode TEXT, gstin TEXT);
CREATE TABLE consignee_phone (consignee_id INT, phone TEXT, PRIMARY KEY (consignee_id, phone));
"""

# ------------------------------------------------------------------ local extensions (different)
LOCAL = {
    1: """
CREATE TABLE tank_farm (tank_id INT PRIMARY KEY, hs_code TEXT, capacity_kl REAL,
    current_kl REAL, current_density REAL, last_gauged_ts TEXT);
CREATE TABLE pipeline_transfer (transfer_id INT PRIMARY KEY, tank_id INT REFERENCES tank_farm,
    voyage_id INT REFERENCES voyage, direction TEXT, start_ts TEXT, end_ts TEXT,
    volume_kl REAL, density_obs REAL);
""",
    2: """
CREATE TABLE rail_rake (rake_id INT PRIMARY KEY, train_no TEXT, dest_icd TEXT, wagon_count INT,
    departure_ts TEXT, status TEXT);
CREATE TABLE rake_loading (rake_id INT REFERENCES rail_rake, cont_id TEXT, wagon_no INT,
    gross_wt INT, loaded_ts TEXT, PRIMARY KEY (rake_id, cont_id));
CREATE TABLE sez_unit (unit_id INT PRIMARY KEY, consignee_id INT UNIQUE, sez_name TEXT,
    bond_no TEXT UNIQUE, licence_expiry TEXT);
CREATE TABLE bond_transfer (transfer_id INT PRIMARY KEY, cont_id TEXT,
    unit_id INT REFERENCES sez_unit, transfer_ts TEXT, duty_forgone REAL);
""",
    3: """
CREATE TABLE roro_vehicle (vin TEXT PRIMARY KEY, voyage_id INT REFERENCES voyage,
    exporter_id INT REFERENCES consignee_h, make TEXT, model TEXT, weight_kg INT, deck_no INT);
CREATE TABLE vehicle_inspection (vin TEXT REFERENCES roro_vehicle, inspected_ts TEXT,
    damage_code TEXT, surveyor_id INT, cleared TEXT, PRIMARY KEY (vin, inspected_ts));
""",
    4: """
CREATE TABLE tidal_window (window_date TEXT, window_no INT, open_ts TEXT UNIQUE, close_ts TEXT,
    max_draft_m REAL, PRIMARY KEY (window_date, window_no));
CREATE TABLE lighterage (op_id INT PRIMARY KEY, voyage_id INT REFERENCES voyage, barge_id TEXT,
    cont_count INT, cargo_tonnes REAL, start_ts TEXT, end_ts TEXT);
""",
}

# ------------------------------------------------------------------ export schemas (GAV sources)
# Each site defines what "cargo in custody" means at THAT port, in tonnes.
EXPORT = {
    1: """CREATE VIEW export_custody AS
  SELECT 1 AS port_id, 'CONTAINER' AS cargo_class,
         COALESCE(SUM(gross_wt), 0) / 1000.0 AS tonnes FROM container_c
  UNION ALL
  SELECT 1, 'LIQUID_BULK',                        -- kilolitres x density (t/m3) = tonnes
         COALESCE(SUM(current_kl * current_density), 0) FROM tank_farm;""",
    2: """CREATE VIEW export_custody AS
  SELECT 2 AS port_id, 'CONTAINER' AS cargo_class,
         COALESCE(SUM(gross_wt), 0) / 1000.0 AS tonnes FROM container_c
  UNION ALL
  SELECT 2, 'CONTAINER_ON_RAIL',                  -- rail weighment, until the rake departs
         COALESCE(SUM(rl.gross_wt), 0) / 1000.0
    FROM rake_loading rl JOIN rail_rake r ON r.rake_id = rl.rake_id
   WHERE r.departure_ts IS NULL;""",
    3: """CREATE VIEW export_custody AS
  SELECT 3 AS port_id, 'CONTAINER' AS cargo_class,
         COALESCE(SUM(gross_wt), 0) / 1000.0 AS tonnes FROM container_c
  UNION ALL
  SELECT 3, 'RORO',                               -- manifest weight, until the voyage sails
         COALESCE(SUM(v.weight_kg), 0) / 1000.0
    FROM roro_vehicle v JOIN voyage y ON y.voyage_id = v.voyage_id
   WHERE y.atd IS NULL;""",
    4: """CREATE VIEW export_custody AS
  SELECT 4 AS port_id, 'CONTAINER' AS cargo_class,
         COALESCE(SUM(gross_wt), 0) / 1000.0 AS tonnes FROM container_c
  UNION ALL
  SELECT 4, 'CONTAINER_AFLOAT',                   -- barge manifest, until the barge lands
         COALESCE(SUM(cargo_tonnes), 0) FROM lighterage WHERE end_ts IS NULL;""",
}

log = []
def say(s=""):
    print(s)
    log.append(s)


def build():
    paths = {}
    for k, (tag, name) in SITES.items():
        p = os.path.join(OUT, f"{tag}_{name.split('/')[0].lower().replace(' ', '_')}.db")
        if os.path.exists(p):
            os.remove(p)
        db = sqlite3.connect(p)
        db.executescript(CORE)
        if k in (2, 3):
            db.executescript(CONSIGNEE_H)
        if k == 2:
            db.executescript(S2_ONLY_GLOBAL)
        db.executescript(LOCAL[k])
        db.executescript(EXPORT[k])
        db.commit()
        db.close()
        paths[k] = p
    return paths


def populate(paths):
    """Deterministic synthetic data; returns the expected custody tonnes per (port, class)."""
    exp = {}
    for k, p in paths.items():
        db = sqlite3.connect(p)
        n = {1: 30, 2: 80, 3: 60, 4: 30}[k]               # proportional to site share
        wts = [random.randint(8_000, 30_000) for _ in range(n)]
        db.executemany("INSERT INTO container_c (cont_id, gross_wt, cur_port_id) VALUES (?,?,?)",
                       [(f"S{k}U{i:07d}", w, k) for i, w in enumerate(wts)])
        exp[(k, "CONTAINER")] = sum(wts) / 1000
        db.execute("INSERT INTO voyage (voyage_id, port_id, ata, atd) VALUES (?,?,?,NULL)",
                   (k * 100 + 1, k, "2026-09-25"))
        db.execute("INSERT INTO voyage (voyage_id, port_id, ata, atd) VALUES (?,?,?,?)",
                   (k * 100 + 2, k, "2026-09-20", "2026-09-22"))
        if k == 1:
            tanks = [(t, "27090000", 20_000.0, round(random.uniform(2_000, 18_000), 1),
                      round(random.uniform(0.82, 0.96), 3), "2026-09-26T06:00")
                     for t in range(1, 7)]
            db.executemany("INSERT INTO tank_farm VALUES (?,?,?,?,?,?)", tanks)
            exp[(1, "LIQUID_BULK")] = sum(t[3] * t[4] for t in tanks)
        if k == 2:
            db.execute("INSERT INTO rail_rake VALUES (1,'CONR101','ICDTKD',45,NULL,'LOADING')")
            db.execute("INSERT INTO rail_rake VALUES (2,'CONR102','ICDDER',45,'2026-09-25T20:00','DEPARTED')")
            open_w = [random.randint(10_000, 28_000) for _ in range(12)]
            gone_w = [random.randint(10_000, 28_000) for _ in range(20)]
            db.executemany("INSERT INTO rake_loading VALUES (1,?,?,?,'2026-09-26')",
                           [(f"R1C{i:04d}", i // 2, w) for i, w in enumerate(open_w)])
            db.executemany("INSERT INTO rake_loading VALUES (2,?,?,?,'2026-09-25')",
                           [(f"R2C{i:04d}", i // 2, w) for i, w in enumerate(gone_w)])
            exp[(2, "CONTAINER_ON_RAIL")] = sum(open_w) / 1000
        if k == 3:
            db.execute("INSERT INTO consignee_h VALUES (501, 'Car Exporter Pvt Ltd')")
            waiting = [random.randint(1_050, 1_900) for _ in range(40)]
            sailed = [random.randint(1_050, 1_900) for _ in range(25)]
            db.executemany("INSERT INTO roro_vehicle VALUES (?,301,501,'MakeA','ModelX',?,1)",
                           [(f"MALW{i:013d}", w) for i, w in enumerate(waiting)])
            db.executemany("INSERT INTO roro_vehicle VALUES (?,302,501,'MakeA','ModelX',?,2)",
                           [(f"MALS{i:013d}", w) for i, w in enumerate(sailed)])
            exp[(3, "RORO")] = sum(waiting) / 1000
        if k == 4:
            db.execute("INSERT INTO lighterage VALUES (1,401,'BARGE07',24,412.5,'2026-09-26T02:00',NULL)")
            db.execute("INSERT INTO lighterage VALUES (2,401,'BARGE03',20,338.0,'2026-09-25T02:00','2026-09-25T14:00')")
            exp[(4, "CONTAINER_AFLOAT")] = 412.5
        db.commit()
        db.close()
    for k in SITES:                                     # classes a site does not have report 0
        for c in ("CONTAINER", "LIQUID_BULK", "CONTAINER_ON_RAIL", "RORO", "CONTAINER_AFLOAT"):
            pass
    return exp


def mediator(paths):
    m = sqlite3.connect(":memory:")
    for k, p in paths.items():
        m.execute(f"ATTACH DATABASE '{p}' AS {SITES[k][0]}")
    m.execute("""CREATE TEMP VIEW cargo_in_custody AS
        SELECT * FROM s1.export_custody UNION ALL SELECT * FROM s2.export_custody
        UNION ALL SELECT * FROM s3.export_custody UNION ALL SELECT * FROM s4.export_custody""")
    return m


def q9(m):
    return {(r[0], r[1]): r[2] for r in
            m.execute("SELECT port_id, cargo_class, SUM(tonnes) FROM cargo_in_custody "
                      "GROUP BY port_id, cargo_class ORDER BY port_id, cargo_class")}


def site_total(m, k):
    return m.execute("SELECT SUM(tonnes) FROM cargo_in_custody WHERE port_id=?", (k,)).fetchone()[0]


def main():
    paths = build()
    exp = populate(paths)
    m = mediator(paths)
    ok = True

    say("=" * 88)
    say("1. LOCAL CONCEPTUAL SCHEMAS — relations present at each site")
    say("=" * 88)
    rel = {}
    for k, (tag, name) in SITES.items():
        rel[k] = {r[0] for r in m.execute(
            f"SELECT name FROM {tag}.sqlite_master WHERE type='table'")}
    core = set.intersection(*rel.values())
    for k, (tag, name) in SITES.items():
        local = sorted(rel[k] - core)
        say(f"  {tag} {name:<16} {len(rel[k]):>2} relations   = {len(core)} common core"
            f" + {len(local)} site-specific: {', '.join(local)}")
    say("")
    pairs = [(a, b) for a in SITES for b in SITES if a < b]
    for a, b in pairs:
        d = rel[a] ^ rel[b]
        flag = "PASS" if d else "FAIL"
        ok &= bool(d)
        say(f"  {flag}  LCS_{a} != LCS_{b}   ({len(d)} relations differ)")

    say("\n" + "=" * 88)
    say("2. SHARED CORE — identical structure at every site")
    say("=" * 88)
    sig = {}
    for k, (tag, _) in SITES.items():
        sig[k] = {t: tuple(c[1] for c in m.execute(f"PRAGMA {tag}.table_info({t})"))
                  for t in core}
    same = all(sig[k] == sig[1] for k in SITES)
    ok &= same
    say(f"  {'PASS' if same else 'FAIL'}  {len(core)} core relations have identical columns "
        f"at all four sites")

    say("\n" + "=" * 88)
    say("3. Q9 THROUGH THE GLOBAL GAV VIEW  vs  value computed independently")
    say("=" * 88)
    got = q9(m)
    say(f"  {'port':<5}{'cargo class':<20}{'global view (t)':>17}{'expected (t)':>15}")
    for key in sorted(got):
        e = exp.get(key, 0.0)
        g = got[key] or 0.0
        good = abs(g - e) < 1e-6
        ok &= good
        say(f"  {key[0]:<5}{key[1]:<20}{g:>17,.3f}{e:>15,.3f}  {'PASS' if good else 'FAIL'}")
    for k, (tag, name) in SITES.items():
        classes = [r[0] for r in m.execute(
            f"SELECT cargo_class FROM {tag}.export_custody")]
        say(f"  {tag} exports classes: {', '.join(classes)}")

    say("\n" + "=" * 88)
    say("4. CUSTODY CONSERVATION — each port's own boundary events, no double counting")
    say("=" * 88)
    # S2: yard -> rake. The container leaves CONTAINER_C_2 and enters RAKE_LOADING.
    db2 = sqlite3.connect(paths[2])
    before = site_total(m, 2)
    move = db2.execute("SELECT cont_id, gross_wt FROM container_c LIMIT 5").fetchall()
    db2.executemany("INSERT INTO rake_loading VALUES (1,?,23,?,'2026-09-26T10:00')", move)
    db2.executemany("DELETE FROM container_c WHERE cont_id=?", [(c,) for c, _ in move])
    db2.commit()
    after = site_total(m, 2)
    t1 = abs(before - after) < 1e-6
    say(f"  {'PASS' if t1 else 'FAIL'}  JNPT  load 5 containers onto open rake: "
        f"{before:,.3f} t -> {after:,.3f} t (conserved)")
    rake_t = db2.execute("SELECT SUM(gross_wt)/1000.0 FROM rake_loading WHERE rake_id=1").fetchone()[0]
    db2.execute("UPDATE rail_rake SET departure_ts='2026-09-26T18:00', status='DEPARTED' WHERE rake_id=1")
    db2.commit()
    dep = site_total(m, 2)
    t2 = abs((after - dep) - rake_t) < 1e-6
    say(f"  {'PASS' if t2 else 'FAIL'}  JNPT  rake departs: custody falls by exactly the rake's "
        f"{rake_t:,.3f} t")
    db2.close()

    # S4: barge lands. Afloat tonnage becomes yard containers.
    db4 = sqlite3.connect(paths[4])
    before = site_total(m, 4)
    n, t = db4.execute("SELECT cont_count, cargo_tonnes FROM lighterage WHERE op_id=1").fetchone()
    each = [int(t * 1000 // n)] * n
    each[-1] += int(round(t * 1000)) - sum(each)
    db4.executemany("INSERT INTO container_c (cont_id, gross_wt, cur_port_id) VALUES (?,?,4)",
                    [(f"S4L{i:07d}", w) for i, w in enumerate(each)])
    db4.execute("UPDATE lighterage SET end_ts='2026-09-26T15:00' WHERE op_id=1")
    db4.commit()
    after = site_total(m, 4)
    t3 = abs(before - after) < 1e-6
    say(f"  {'PASS' if t3 else 'FAIL'}  HALDIA barge lands, {n} containers enter the yard: "
        f"{before:,.3f} t -> {after:,.3f} t (conserved)")
    db4.close()

    # S3: the RoRo voyage sails.
    db3 = sqlite3.connect(paths[3])
    before = site_total(m, 3)
    roro = got[(3, "RORO")]
    db3.execute("UPDATE voyage SET atd='2026-09-26T21:00' WHERE voyage_id=301")
    db3.commit()
    after = site_total(m, 3)
    t4 = abs((before - after) - roro) < 1e-6
    say(f"  {'PASS' if t4 else 'FAIL'}  CHENNAI RoRo voyage sails: custody falls by exactly the "
        f"{roro:,.3f} t of vehicles aboard")
    db3.close()

    # S1: a gauging changes the level; tonnes follow kl x density.
    db1 = sqlite3.connect(paths[1])
    kl, dens = db1.execute("SELECT current_kl, current_density FROM tank_farm WHERE tank_id=1").fetchone()
    before = site_total(m, 1)
    db1.execute("UPDATE tank_farm SET current_kl = current_kl - 500 WHERE tank_id=1")
    db1.commit()
    after = site_total(m, 1)
    t5 = abs((before - after) - 500 * dens) < 1e-6
    say(f"  {'PASS' if t5 else 'FAIL'}  NEW MANGALORE 500 kl pumped out at density {dens}: "
        f"custody falls by {500*dens:,.3f} t")
    db1.close()
    ok &= all([t1, t2, t3, t4, t5])

    say("\n" + "=" * 88)
    say(f"RESULT: {'ALL CHECKS PASS' if ok else 'FAILURES PRESENT'}")
    say("=" * 88)
    with open(os.path.join(OUT, "hetero_demo_output.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    with open(os.path.join(OUT, "export_views.sql"), "w") as f:
        f.write("-- Export schemas: one per site, each defined over that site's OWN tables.\n")
        f.write("-- The mediator unions them into the global relation CARGO_IN_CUSTODY (GAV).\n\n")
        for k, (tag, name) in SITES.items():
            f.write(f"-- {tag}: {name}\n{EXPORT[k]}\n\n")
        f.write("-- Mediator (global layer)\nCREATE VIEW cargo_in_custody AS\n"
                "  SELECT * FROM s1.export_custody UNION ALL SELECT * FROM s2.export_custody\n"
                "  UNION ALL SELECT * FROM s3.export_custody UNION ALL SELECT * FROM s4.export_custody;\n\n"
                "-- Q9\nSELECT port_id, cargo_class, SUM(tonnes)\n  FROM cargo_in_custody\n"
                " GROUP BY port_id, cargo_class;\n")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
