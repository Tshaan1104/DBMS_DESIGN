#!/usr/bin/env python3
"""Heterogeneous local schemas — definitions, normalization notes, physical design.

Single source of truth for the site-specific (bottom-up) extensions of each Local
Conceptual Schema. phase6.py, alloc.py and verify.py import from here so the numbers
cannot drift apart.
"""
from math import ceil

B, PTR = 4096, 8
S_, L_ = 8.0, 4.0
BTT = (B + 128) / 104_857_600 * 1000          # 0.0403 ms
ACC = S_ + L_ + BTT                           # 12.04 ms per random block access
TD = 1024 / 12.5e6 * 1000                     # 0.0819 ms per packet
V = 2.7e8
DIST = {("S1", "S2"): 700, ("S1", "S3"): 700, ("S1", "S4"): 2000,
        ("S2", "S3"): 1300, ("S2", "S4"): 1900, ("S3", "S4"): 1650}
SITES = ["S1", "S2", "S3", "S4"]
PORT = {"S1": "New Mangalore", "S2": "JNPT", "S3": "Chennai", "S4": "Kolkata/Haldia"}


def tp(a, b):
    if a == b:
        return 0.0
    return (DIST.get((a, b)) or DIST.get((b, a))) * 1000 / V * 1000


scan = lambda nb: S_ + L_ + nb * BTT          # sequential, one seek
rand = lambda n: ACC * n                      # n scattered accesses
blocks = lambda n, r: ceil(n * r / B)


def multilevel(entries, esz):
    bfri = B // esz
    lv = tot = 0
    e = entries
    while True:
        nb = ceil(e / bfri)
        lv += 1
        tot += nb
        if nb <= 1:
            return lv, tot
        e = nb


def bplus(entries, ksz):
    pl, pi = (B - PTR) // (ksz + PTR), (B + ksz) // (PTR + ksz)
    leaves = ceil(entries / pl)
    tot, nodes, h = leaves, leaves, 1
    while nodes > 1:
        nodes = ceil(nodes / pi)
        tot += nodes
        h += 1
    return h, tot, leaves


# ------------------------------------------------------------------ local relations
# id, site, name, [(attr, bytes, pk?)], tuples, index-kind, index-key-bytes, why
LOCAL = [
    ("R20", "S1", "TANK_FARM",
     [("tank_id", 4, 1), ("hs_code", 8, 0), ("capacity_kl", 8, 0), ("current_kl", 8, 0),
      ("current_density", 8, 0), ("last_gauged_ts", 8, 0)],
     60, "none", 0, "single block"),
    ("R21", "S1", "PIPELINE_TRANSFER",
     [("transfer_id", 4, 1), ("tank_id", 4, 0), ("voyage_id", 4, 0), ("direction", 1, 0),
      ("start_ts", 8, 0), ("end_ts", 8, 0), ("volume_kl", 8, 0), ("density_obs", 8, 0)],
     4_400, "none", 0, "insert-only; no transaction searches it"),
    ("R22", "S2", "RAIL_RAKE",
     [("rake_id", 4, 1), ("train_no", 8, 0), ("dest_icd", 6, 0), ("wagon_count", 4, 0),
      ("departure_ts", 8, 0), ("status", 10, 0)],
     11_000, "primary", 4, "L3 updates status by rake_id; file is in rake_id order"),
    ("R23", "S2", "RAKE_LOADING",
     [("rake_id", 4, 1), ("cont_id", 11, 1), ("wagon_no", 4, 0), ("gross_wt", 4, 0),
      ("loaded_ts", 8, 0)],
     1_000_000, "clustering", 4, "Q9 reads by rake_id; inserts arrive in rake order"),
    ("R24", "S2", "SEZ_UNIT",
     [("unit_id", 4, 1), ("consignee_id", 4, 0), ("sez_name", 30, 0), ("bond_no", 15, 0),
      ("licence_expiry", 4, 0)],
     200, "none", 0, "three blocks; a scan is one seek"),
    ("R25", "S2", "BOND_TRANSFER",
     [("transfer_id", 4, 1), ("cont_id", 11, 0), ("unit_id", 4, 0), ("transfer_ts", 8, 0),
      ("duty_forgone", 8, 0)],
     40_000, "none", 0, "insert-only; no transaction searches it"),
    ("R26", "S3", "RORO_VEHICLE",
     [("vin", 17, 1), ("voyage_id", 4, 0), ("exporter_id", 4, 0), ("make", 15, 0),
      ("model", 20, 0), ("weight_kg", 4, 0), ("deck_no", 4, 0)],
     350_000, "bplus", 17, "L6 looks up by vin; arrival order is not vin order"),
    ("R27", "S3", "VEHICLE_INSPECTION",
     [("vin", 17, 1), ("inspected_ts", 8, 1), ("damage_code", 4, 0), ("surveyor_id", 4, 0),
      ("cleared", 1, 0)],
     420_000, "none", 0, "insert-only; no transaction searches it"),
    ("R28", "S4", "TIDAL_WINDOW",
     [("window_date", 4, 1), ("window_no", 4, 1), ("open_ts", 8, 0), ("close_ts", 8, 0),
      ("max_draft_m", 8, 0)],
     730, "none", 0, "insert-only planning reference; six blocks"),
    ("R29", "S4", "LIGHTERAGE",
     [("op_id", 4, 1), ("voyage_id", 4, 0), ("barge_id", 8, 0), ("cont_count", 4, 0),
      ("cargo_tonnes", 8, 0), ("start_ts", 8, 0), ("end_ts", 8, 0)],
     2_200, "primary", 4, "L7 closes an operation by op_id"),
]

REC = {r[2]: sum(a[1] for a in r[3]) for r in LOCAL}
TUP = {r[2]: r[4] for r in LOCAL}
SITE_OF = {r[2]: r[1] for r in LOCAL}


def physical():
    """Blocks, index blocks, index levels and a note, per local relation."""
    out = {}
    for rid, site, name, attrs, n, kind, ksz, why in LOCAL:
        nb = blocks(n, REC[name])
        if kind == "none":
            ib, lv = 0, 0
        elif kind == "primary":
            lv, ib = multilevel(nb, ksz + PTR)
        elif kind == "clustering":
            distinct = 11_000                      # rakes: one index entry per rake
            lv, ib = multilevel(distinct, ksz + PTR)
        else:                                      # bplus
            lv, ib, _ = bplus(n, ksz)
        out[name] = dict(id=rid, site=site, rec=REC[name], tuples=n, blocks=nb,
                         idx_kind=kind, idx_blocks=ib, idx_levels=lv, why=why)
    return out


PHYS = physical()
LOCAL_DATA = {s: sum(p["blocks"] for p in PHYS.values() if p["site"] == s) for s in SITES}
LOCAL_IDX = {s: sum(p["idx_blocks"] for p in PHYS.values() if p["site"] == s) for s in SITES}

# ------------------------------------------------------------------ local transactions
# Run under local (execution) autonomy: invisible to the global transaction manager.
LOCAL_TX = [
    ("L1", "S1", "Record tank gauging", "UPDATE TANK_FARM", 240, rand(1) * 2),
    ("L2", "S1", "Record pipeline transfer", "INSERT PIPELINE_TRANSFER", 12, rand(2)),
    ("L3", "S2", "Load container onto rake", "INSERT RAKE_LOADING; close CONTAINER_C_2 row",
     2_740, rand(2) + rand(3)),
    ("L4", "S2", "Transfer container to SEZ unit", "read SEZ_UNIT; INSERT BOND_TRANSFER",
     110, scan(3) + rand(2)),
    ("L5", "S3", "Register RoRo vehicle for export", "FK check CONSIGNEE_H; INSERT RORO_VEHICLE",
     960, rand(3) + rand(2) + rand(4)),
    ("L6", "S3", "Record vehicle inspection", "probe RORO_VEHICLE by vin; INSERT VEHICLE_INSPECTION",
     1_150, rand(3) + rand(2)),
    ("L7", "S4", "Open / close lighterage operation", "INSERT or UPDATE LIGHTERAGE",
     6, rand(2) * 2),
    ("L8", "S4", "Publish tidal window", "INSERT TIDAL_WINDOW", 2, rand(2)),
]
LOCAL_TX_TOTAL = sum(t[4] for t in LOCAL_TX)

# ------------------------------------------------------------------ Q9 (global, integrated)
Q9_FREQ = [5, 10, 5, 5]       # per originating site
Q9_TOTAL = sum(Q9_FREQ)

CORE_BLK_F1 = {"S1": 989, "S2": 2637, "S3": 1978, "S4": 989}    # CONTAINER_C_k
VOYAGE_BLK = {"S1": 7, "S2": 18, "S3": 14, "S4": 7}


def q9_part(site):
    """Local sub-query cost at one site. Each site's plan is DIFFERENT."""
    core = scan(CORE_BLK_F1[site])                       # sum(gross_wt) over CONTAINER_C_k
    if site == "S1":                                     # + tank farm, kl x density
        return core + scan(PHYS["TANK_FARM"]["blocks"]), "CONTAINER_C_1 + TANK_FARM"
    if site == "S2":                                     # + rakes not yet departed
        rake_scan = scan(PHYS["RAIL_RAKE"]["blocks"])
        tail = 2 * ACC + scan(8)                         # clustering idx to first open rake, read ~8 blocks
        return core + rake_scan + tail, "CONTAINER_C_2 + RAIL_RAKE |><| RAKE_LOADING"
    if site == "S3":                                     # + RoRo awaiting shipment
        return core + scan(VOYAGE_BLK["S3"]) + scan(PHYS["RORO_VEHICLE"]["blocks"]), \
            "CONTAINER_C_3 + VOYAGE_3 |><| RORO_VEHICLE"
    return core + scan(PHYS["LIGHTERAGE"]["blocks"]), "CONTAINER_C_4 + LIGHTERAGE"


def q9_response(origin):
    parts = [q9_part(s)[0] + (TD + 2 * tp(origin, s) if s != origin else 0) for s in SITES]
    return max(parts) + 5, sum(parts)


# ------------------------------------------------------------------ report
if __name__ == "__main__":
    line = "=" * 96
    print(line + "\nLOCAL RELATIONS — definitions and physical design\n" + line)
    print(f"{'ID':<5}{'Site':<5}{'Relation':<20}{'R':>4}{'tuples':>11}{'blocks':>8}"
          f"{'index':>12}{'idx blks':>9}  why")
    for name, p in PHYS.items():
        print(f"{p['id']:<5}{p['site']:<5}{name:<20}{p['rec']:>4}{p['tuples']:>11,}"
              f"{p['blocks']:>8,}{p['idx_kind']:>12}{p['idx_blocks']:>9,}  {p['why']}")
    print(f"\n{'Site':<6}{'local data':>12}{'local index':>13}{'relations':>11}")
    for s in SITES:
        n = sum(1 for p in PHYS.values() if p["site"] == s)
        print(f"{s:<6}{LOCAL_DATA[s]:>12,}{LOCAL_IDX[s]:>13,}{n:>11}   {PORT[s]}")

    print("\n" + line + "\nLOCAL TRANSACTIONS (local autonomy — invisible to the global layer)\n" + line)
    for tid, s, nm, ops, f, ms in LOCAL_TX:
        print(f"  {tid} {s}  {nm:<34}{f:>6,}/day  {ms:>7.1f} ms   {ops}")
    print(f"  total {LOCAL_TX_TOTAL:,}/day")

    print("\n" + line + "\nQ9 — CARGO IN CUSTODY: a different sub-query at every site\n" + line)
    for s in SITES:
        ms, plan = q9_part(s)
        print(f"  {s} {PORT[s]:<16}{ms:>8.1f} ms   {plan}")
    print()
    for s in SITES:
        par, ser = q9_response(s)
        print(f"  originating at {s}: parallel {par:6.0f} ms   serial {ser:6.0f} ms")
