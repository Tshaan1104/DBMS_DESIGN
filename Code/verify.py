#!/usr/bin/env python3
"""Phase 7 — consistency pass. Recomputes every derived figure from the Phase 0
assumptions and compares it against what Phases 1-6 claimed. Reports PASS/FAIL."""
from math import ceil

B, G, PTR = 4096, 128, 8
S_, L_, XFER = 8.0, 4.0, 104_857_600
BTT = (B + G) / XFER * 1000
V, PKT, BW = 2.7e8, 1024, 12.5e6
SITES = ["S1", "S2", "S3", "S4"]
SHARE = {"S1": .15, "S2": .40, "S3": .30, "S4": .15}

checks = []
def check(name, got, want, tol=0.0):
    ok = abs(got - want) <= tol if isinstance(want, (int, float)) else got == want
    checks.append((ok, name, got, want))
    return ok

def section(t):
    print(f"\n{'='*92}\n{t}\n{'='*92}")

# ------------------------------------------------------- 1. record sizes
section("1. RECORD SIZES recomputed from the Phase 2 attribute lists")
ATTRS = {
 "PORT":            [("port_id",4),("port_name",20),("city",20),("country",20),("timezone",6)],
 "SHIPPING_LINE":   [("line_id",4),("name",30),("country",20),("agent_name",30)],
 "VESSEL":          [("vessel_id",4),("name",30),("imo_no",7),("flag",3),("capacity_teu",4),("line_id",4)],
 "VOYAGE":          [("voyage_id",4),("vessel_id",4),("port_id",4),("eta",8),("ata",8),("atd",8),("berth_no",4),("status",10)],
 "CONSIGNEE":       [("consignee_id",4),("name",40),("street_line",40),("area",20),("pincode",6),("gstin",15)],
 "PINCODE":         [("pincode",6),("city",20),("state",20)],
 "CONSIGNEE_PHONE": [("consignee_id",4),("phone",12)],
 "CONTAINER":       [("cont_id",11),("size_ft",4),("cont_type",4),("tare_wt",4),("gross_wt",4),
                     ("seal_no",12),("hazmat_class",3),("invoice_value",8),("customs_status",10),
                     ("line_id",4),("consignee_id",4),("cur_port_id",4),("voyage_id",4)],
 "YARD_BLOCK":      [("port_id",4),("block",3),("has_power",1),("max_tier",4)],
 "YARD_SLOT":       [("port_id",4),("block",3),("bay",4),("row",4),("tier",4),("cont_id",11),("occupied_since",8)],
 "GATE_MOVE":       [("move_id",4),("cont_id",11),("port_id",4),("ts",8),("direction",1),
                     ("truck_no",10),("gate_no",4),("operator_id",4)],
 "CUSTOMS_DECL":    [("decl_id",4),("cont_id",11),("hs_code",8),("duty_amt",8),("filed_on",4),("cleared_on",4),("officer_id",4)],
 "HS_CODE_MASTER":  [("hs_code",8),("hs_description",40),("duty_rate",8)],
 "BILL_OF_LADING":  [("bl_no",12),("voyage_id",4),("consignee_id",4),("cont_count",4),("freight_amt",8),("issue_date",4)],
 "SERVICE":         [("service_code",6),("service_name",30),("currency",3)],
 "TARIFF":          [("port_id",4),("service_code",6),("rate",8)],
 "CONTAINER_REEFER":[("cont_id",11),("set_point_temp",4),("plug_id",8)],
 "CONTAINER_TANK":  [("cont_id",11),("un_number",8),("last_cleaned_on",4)],
 "CONTAINER_OPEN_TOP":[("cont_id",11),("over_height_cm",4)],
}
CLAIMED = {"PORT":70,"SHIPPING_LINE":84,"VESSEL":52,"VOYAGE":50,"CONSIGNEE":125,"PINCODE":46,
 "CONSIGNEE_PHONE":16,"CONTAINER":76,"YARD_BLOCK":12,"YARD_SLOT":38,"GATE_MOVE":46,
 "CUSTOMS_DECL":43,"HS_CODE_MASTER":56,"BILL_OF_LADING":36,"SERVICE":39,"TARIFF":18,
 "CONTAINER_REEFER":23,"CONTAINER_TANK":23,"CONTAINER_OPEN_TOP":15}
for r, a in ATTRS.items():
    got = sum(s for _, s in a)
    ok = check(f"record size {r}", got, CLAIMED[r])
    print(f"  {'PASS' if ok else 'FAIL':<5} {r:<22} computed {got:>4} B   claimed {CLAIMED[r]:>4} B")

# ------------------------------------------------------- 2. vertical split
section("2. VERTICAL FRAGMENTATION of CONTAINER — do the pieces reconstruct?")
d = dict(ATTRS["CONTAINER"])
G_at = ["cont_id", "seal_no", "customs_status"]
C_at = [k for k, _ in ATTRS["CONTAINER"] if k not in G_at[1:]]
sg, sc = sum(d[k] for k in G_at), sum(d[k] for k in C_at)
print(f"  CONTAINER_G = {G_at}  -> {sg} B")
print(f"  CONTAINER_C = {len(C_at)} attrs                      -> {sc} B")
check("CONTAINER_G size", sg, 33); check("CONTAINER_C size", sc, 54)
union = set(G_at) | set(C_at); inter = set(G_at) & set(C_at)
print(f"  {'PASS' if union == set(d) else 'FAIL'}  completeness: union covers all 13 attributes")
print(f"  {'PASS' if inter == {'cont_id'} else 'FAIL'}  disjointness: overlap is exactly the key {inter}")
print(f"  {'PASS' if sg+sc == CLAIMED['CONTAINER']+d['cont_id'] else 'FAIL'}  "
      f"overhead: {sg}+{sc} = {sg+sc} = 76 + {d['cont_id']} (key replicated once)")
check("vertical union", union == set(d), True)
check("vertical disjoint", inter == {"cont_id"}, True)

# ------------------------------------------------------- 3. tuple counts
section("3. TUPLE COUNTS — do per-site figures sum to the relation totals?")
TUPLES = {"CONTAINER":500_000,"GATE_MOVE":60_000_000,"CUSTOMS_DECL":450_000,
          "BILL_OF_LADING":180_000,"YARD_SLOT":550_000,"YARD_BLOCK":2_200,
          "VOYAGE":3_600,"CONTAINER_REEFER":40_000,"CONTAINER_TANK":15_000,
          "CONTAINER_OPEN_TOP":10_000}
for r, n in TUPLES.items():
    per = [round(n*SHARE[s]) for s in SITES]
    ok = check(f"tuples {r}", sum(per), n)
    print(f"  {'PASS' if ok else 'FAIL':<5} {r:<20} " +
          " + ".join(f"{p:,}" for p in per) + f" = {sum(per):,}  (want {n:,})")
sub = sum(TUPLES[k] for k in ["CONTAINER_REEFER","CONTAINER_TANK","CONTAINER_OPEN_TOP"])
print(f"\n  subtypes: {sub:,} of {TUPLES['CONTAINER']:,} = {100*sub/TUPLES['CONTAINER']:.0f}% "
      f"non-dry, DRY = {TUPLES['CONTAINER']-sub:,} ({100-100*sub/TUPLES['CONTAINER']:.0f}%)")
check("subtype total <= CONTAINER", sub <= TUPLES["CONTAINER"], True)

# ------------------------------------------------------- 4. blocks
section("4. BLOCK COUNTS — recomputed, with Amendment B1 (YARD_SLOT) applied")
FRAG = [("F1","CONTAINER_C",54,500_000),("F2","CONTAINER_G",33,500_000),
        ("F3","VOYAGE",50,3_600),("F4","YARD_SLOT",38,550_000),
        ("F5","YARD_BLOCK",12,2_200),("F6","GATE_MOVE",46,60_000_000),
        ("F7","TARIFF",18,40),("F8","CUSTOMS_DECL",43,450_000),
        ("F9","BILL_OF_LADING",36,180_000),("F10","CONTAINER_REEFER",23,40_000),
        ("F11","CONTAINER_TANK",23,15_000),("F12","CONTAINER_OPEN_TOP",15,10_000)]
blocks = lambda n, r: ceil(n*r/B)
DATA = {s: 0 for s in SITES}; FB = {}
print(f"  {'ID':<5}{'Fragment':<21}" + "".join(f"{s:>10}" for s in SITES) + f"{'total':>10}")
for fid, nm, r, n in FRAG:
    per = {s: blocks(10 if fid == "F7" else round(n*SHARE[s]), r) for s in SITES}
    FB[fid] = per
    for s in SITES: DATA[s] += per[s]
    print(f"  {fid:<5}{nm:<21}" + "".join(f"{per[s]:>10,}" for s in SITES)
          + f"{sum(per.values()):>10,}")
print(f"  {'':<5}{'DATA TOTAL':<21}" + "".join(f"{DATA[s]:>10,}" for s in SITES)
      + f"{sum(DATA.values()):>10,}")

unfrag_blocks = blocks(60_000_000, 46)
frag_blocks   = sum(FB["F6"].values())
print(f"\n  fragmentation rounding: GATE_MOVE as one relation = {unfrag_blocks:,} blocks;")
print(f"    as four fragments = {frag_blocks:,} blocks  -> +{frag_blocks-unfrag_blocks} blocks "
      f"({(frag_blocks-unfrag_blocks)*B/1024:.0f} KB) lost to per-fragment rounding")

# ------------------------------------------------------- 5. indexes
section("5. INDEX BLOCKS — recomputed")
def multilevel(entries, esz):
    bfri = B // esz; lv = tot = 0; e = entries
    while True:
        nb = ceil(e/bfri); lv += 1; tot += nb
        if nb <= 1: return lv, tot
        e = nb
def bplus(entries, ksz):
    pl, pi = (B-PTR)//(ksz+PTR), (B+ksz)//(PTR+ksz)
    leaves = ceil(entries/pl); tot, nodes, h = leaves, leaves, 1
    while nodes > 1:
        nodes = ceil(nodes/pi); tot += nodes; h += 1
    return h, tot
KEY = {"F1":11,"F2":11,"F3":4,"F4":19,"F5":0,"F6":11,"F7":0,"F8":11,"F9":12,
       "F10":11,"F11":11,"F12":11}
IDX = {s: 0 for s in SITES}
print(f"  {'ID':<5}{'index':<28}" + "".join(f"{s:>10}" for s in SITES))
for fid, nm, r, n in FRAG:
    if KEY[fid] == 0:
        print(f"  {fid:<5}{'none (single block)':<28}" + "".join(f"{0:>10}" for s in SITES)); continue
    per = {}
    for s in SITES:
        if fid == "F6": _, tb = bplus(round(n*SHARE[s]), KEY[fid])
        else:           _, tb = multilevel(FB[fid][s], KEY[fid]+PTR)
        per[s] = tb; IDX[s] += tb
    kind = "B+ tree on cont_id" if fid == "F6" else f"primary, key {KEY[fid]} B"
    print(f"  {fid:<5}{kind:<28}" + "".join(f"{per[s]:>10,}" for s in SITES))
print(f"  {'':<5}{'INDEX TOTAL':<28}" + "".join(f"{IDX[s]:>10,}" for s in SITES))

# ------------------------------------------------------- 6. storage reconciliation
section("6. STORAGE RECONCILIATION — restated with Amendment B1")
REPL = {"S1":16,"S2":1806,"S3":16,"S4":16}   # before Amendment C2 (CONSIGNEE_H -> S3)
PREV = {"S1":145857,"S2":390686,"S3":291682,"S4":145857}     # Phase 5 table
print(f"  {'Site':<6}{'data':>10}{'index':>10}{'repl':>8}{'TOTAL':>11}{'MB':>9}"
      f"{'Phase 5 said':>14}{'delta':>9}")
grand = 0
for s in SITES:
    tot = DATA[s]+IDX[s]+REPL[s]; grand += tot
    print(f"  {s:<6}{DATA[s]:>10,}{IDX[s]:>10,}{REPL[s]:>8,}{tot:>11,}"
          f"{tot*B/1e6:>9.0f}{PREV[s]:>14,}{tot-PREV[s]:>+9,}")
print(f"  {'ALL':<6}{sum(DATA.values()):>10,}{sum(IDX.values()):>10,}"
      f"{sum(REPL.values()):>8,}{grand:>11,}{grand*B/1e6:>9.0f}"
      f"{sum(PREV.values()):>14,}{grand-sum(PREV.values()):>+9,}")

# ------------------------------------------------------- 7. derived constants
section("7. DERIVED CONSTANTS")
for nm, got, want, unit in [
    ("Tr block transfer", (B+G)/XFER*1000, 0.0403, "ms"),
    ("Td per packet",     PKT/BW*1000,     0.0819, "ms"),
    ("Tp S1-S2 (700 km)", 700_000/V*1000,  2.59,   "ms"),
    ("Tp S1-S4 (2000 km)",2_000_000/V*1000,7.41,   "ms"),
    ("random block access", S_+L_+(B+G)/XFER*1000, 12.04, "ms"),
]:
    ok = check(nm, round(got,4), want, 0.005)
    print(f"  {'PASS' if ok else 'FAIL':<5} {nm:<22} {got:>9.4f} {unit}  (report says {want})")

# ------------------------------------------------------- 8. internal coherence
section("8. INTERNAL COHERENCE of the workload assumptions")
transits = 60_000_000/4
dwell = 500_000/(transits/365)
print(f"  gate moves/yr 60,000,000 at 4 per transit -> {transits:,.0f} transits/yr")
print(f"  {transits/365:,.0f} transits/day; 500,000 resident -> dwell = {dwell:.1f} days")
ok = check("dwell > 5-day free period", dwell > 5, True)
print(f"  {'PASS' if ok else 'FAIL'}  dwell {dwell:.1f} d exceeds the 5-day free period, so Q8 "
      f"(demurrage) has a population to measure")
jnpt = 6_000_000/365*dwell
ok = check("JNPT yard population", abs(jnpt-200_000) < 5_000, True)
print(f"  {'PASS' if ok else 'FAIL'}  JNPT 6M TEU/yr x {dwell:.1f} d dwell = {jnpt:,.0f} in yard "
      f"vs 200,000 at S2 ({100*abs(jnpt-200_000)/200_000:.1f}% apart)")
ok = check("slots >= containers", 550_000 >= 500_000, True)
print(f"  {'PASS' if ok else 'FAIL'}  550,000 yard slots >= 500,000 resident containers "
      f"({100*500_000/550_000:.0f}% occupancy)")
gm = FB["F6"]; tot_b = sum(DATA.values())
print(f"\n  GATE_MOVE = {sum(gm.values()):,} of {tot_b:,} data blocks = "
      f"{100*sum(gm.values())/tot_b:.1f}%  (I/O-bound claim)")
check("GATE_MOVE dominates", sum(gm.values())/tot_b > 0.9, True)


# ------------------------------------------------------- 9. heterogeneous local schemas
section("9. HETEROGENEOUS LOCAL SCHEMAS (Amendment C1) — recomputed independently")
import os, sqlite3
import local_schemas as LS
CLAIMED_L = {"TANK_FARM":44, "PIPELINE_TRANSFER":45, "RAIL_RAKE":40, "RAKE_LOADING":31,
             "SEZ_UNIT":57, "BOND_TRANSFER":35, "RORO_VEHICLE":68, "VEHICLE_INSPECTION":34,
             "TIDAL_WINDOW":32, "LIGHTERAGE":44}
CLAIMED_LB = {"TANK_FARM":1, "PIPELINE_TRANSFER":49, "RAIL_RAKE":108, "RAKE_LOADING":7_569,
              "SEZ_UNIT":3, "BOND_TRANSFER":342, "RORO_VEHICLE":5_811,
              "VEHICLE_INSPECTION":3_487, "TIDAL_WINDOW":6, "LIGHTERAGE":24}
CLAIMED_LI = {"RAIL_RAKE":1, "RAKE_LOADING":34, "RORO_VEHICLE":2_163, "LIGHTERAGE":1}
for rid, site, name, attrs, n, kind, ksz, why in LS.LOCAL:
    rec = sum(a[1] for a in attrs)
    nb = ceil(n * rec / B)
    ok1 = check(f"record size {name}", rec, CLAIMED_L[name])
    ok2 = check(f"blocks {name}", nb, CLAIMED_LB[name])
    ok3 = check(f"index blocks {name}", LS.PHYS[name]["idx_blocks"], CLAIMED_LI.get(name, 0))
    print(f"  {'PASS' if ok1 and ok2 and ok3 else 'FAIL':<5} {rid} {site} {name:<20} "
          f"{rec:>3} B x {n:>9,} = {nb:>6,} blocks, index {LS.PHYS[name]['idx_blocks']:>5,}")
    if name in ATTRS:
        check(f"local name {name} collides with core", False, True)

# B+ tree on vin, recomputed by hand: 17-byte key, 8-byte pointer
pl = (B - PTR) // (17 + PTR); leaves = ceil(350_000 / pl)
pi = (B + 17) // (PTR + 17); inner = ceil(leaves / pi); root = ceil(inner / pi)
ok = check("RORO B+ tree", (leaves, leaves + inner + root), (2_148, 2_163))
print(f"  {'PASS' if ok else 'FAIL':<5} RORO_VEHICLE B+ tree: {pl} keys/leaf -> {leaves:,} leaves "
      f"+ {inner} + {root} = {leaves+inner+root:,} blocks, height 3")

# the four Local Conceptual Schemas must be pairwise different
LCS = {s: {r[2] for r in LS.LOCAL if r[1] == s} for s in SITES}
for i, a in enumerate(SITES):
    for b in SITES[i+1:]:
        ok = check(f"LCS {a} != {b}", LCS[a] != LCS[b] and not (LCS[a] & LCS[b]), True)
        print(f"  {'PASS' if ok else 'FAIL':<5} LCS_{a[1]} and LCS_{b[1]} share no local relation "
              f"({len(LCS[a])} vs {len(LCS[b])})")

# executable prototype: read the four SQLite databases produced by hetero_demo.py
DBS = {"S1":"s1_new_mangalore.db", "S2":"s2_jnpt.db", "S3":"s3_chennai.db", "S4":"s4_kolkata.db"}
if all(os.path.exists(f"hetero_demo/{f}") for f in DBS.values()):
    tabs, cols, views = {}, {}, {}
    for s, f in DBS.items():
        cx = sqlite3.connect(f"hetero_demo/{f}")
        tabs[s] = {r[0] for r in cx.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        cols[s] = {t: [c[1] for c in cx.execute(f"PRAGMA table_info({t})")] for t in tabs[s]}
        views[s] = [c[1] for c in cx.execute("PRAGMA table_info(export_custody)")]
        cx.close()
    common = set.intersection(*tabs.values())
    same = all(cols[s][t] == cols["S1"][t] for t in common for s in SITES)
    ok = check("prototype: common relations identical", same, True)
    print(f"  {'PASS' if ok else 'FAIL':<5} prototype: {len(common)} relations common to all four "
          f"databases have identical columns")
    distinct = len({frozenset(v) for v in tabs.values()}) == 4
    ok = check("prototype: four different schemas", distinct, True)
    print(f"  {'PASS' if ok else 'FAIL':<5} prototype: the four databases have four different "
          f"sets of relations ({', '.join(str(len(tabs[s])) for s in SITES)})")
    ok = check("prototype: export schema uniform", all(v == ["port_id", "cargo_class", "tonnes"]
                                                       for v in views.values()), True)
    print(f"  {'PASS' if ok else 'FAIL':<5} prototype: every site exports "
          f"export_custody(port_id, cargo_class, tonnes) in the same unit")
else:
    print("  (hetero_demo/ not found - run hetero_demo.py for the prototype checks)")

# storage restated with the local relations and Amendment C2
REPL2 = {"S1":16, "S2":1806, "S3":446, "S4":16}
print(f"\n  {'Site':<6}{'core':>10}{'local':>8}{'repl':>8}{'TOTAL':>11}{'MB':>8}")
g2 = 0
for s in SITES:
    loc = LS.LOCAL_DATA[s] + LS.LOCAL_IDX[s]
    tot = DATA[s] + IDX[s] + loc + REPL2[s]; g2 += tot
    print(f"  {s:<6}{DATA[s]+IDX[s]:>10,}{loc:>8,}{REPL2[s]:>8,}{tot:>11,}{tot*B/1e6:>8.0f}")
ok = check("grand total with local schemas", g2, 998_694)
print(f"  {'PASS' if ok else 'FAIL':<5} all sites {g2:,} blocks = {g2*B/1e6:,.0f} MB "
      f"(report: 998,694 blocks, 4,091 MB)")
all_data = sum(DATA.values()) + sum(LS.LOCAL_DATA.values())
ok = check("GATE_MOVE still dominates", sum(FB["F6"].values()) / all_data > 0.9, True)
print(f"  {'PASS' if ok else 'FAIL':<5} GATE_MOVE = {100*sum(FB['F6'].values())/all_data:.1f}% of all "
      f"data blocks including local relations (still I/O-bound)")

# locality with Q9 and the local transactions (Section 3 frequency table)
FQ = {"Q1":860, "Q2":200, "Q3":325, "Q4":150, "Q5":410, "Q6":105, "Q7":150, "Q8":180,
      "Q9":25, "U1":23_200, "U2":3_100, "U3":2_780}
cross = FQ["Q6"] + FQ["Q8"] + FQ["Q9"]
local = sum(FQ.values()) - cross
tot_acc = local + 4 * cross
loc_g = 1 - 3 * cross / tot_acc
loc_all = 1 - 3 * cross / (tot_acc + LS.LOCAL_TX_TOTAL)
ok1 = check("locality global", round(100 * loc_g, 2), 97.13)
ok2 = check("locality incl. local tx", round(100 * loc_all, 2), 97.53)
print(f"  {'PASS' if ok1 and ok2 else 'FAIL':<5} locality: 1 - {3*cross}/{tot_acc:,} = {100*loc_g:.2f}% "
      f"of global accesses; {100*loc_all:.2f}% with L1-L8 ({LS.LOCAL_TX_TOTAL:,}/day)")

# ------------------------------------------------------- summary
section("SUMMARY")
bad = [c for c in checks if not c[0]]
print(f"  {len(checks)-len(bad)} of {len(checks)} automated checks PASS")
if bad:
    for _, n, got, want in bad:
        print(f"    FAIL  {n}: got {got}, expected {want}")
else:
    print("  No discrepancies. Section 6 restates Phase 5 (Amendment B1); section 9 restates it "
          "again with the local relations and Amendment C2.")
