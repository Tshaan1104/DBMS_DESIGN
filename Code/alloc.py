#!/usr/bin/env python3
"""Phase 5 — All Beneficial Sites allocation with benefit AND cost computation."""
from math import ceil

SITES = ["S1", "S2", "S3", "S4"]
DIST = {("S1","S2"):700, ("S1","S3"):700, ("S1","S4"):2000,
        ("S2","S3"):1300, ("S2","S4"):1900, ("S3","S4"):1650}
V, PKT, BW = 2.7e8, 1024, 12.5e6
TD = PKT / BW * 1000                      # 0.0819 ms per packet
S_, L_, BTT = 8.0, 4.0, (4096+128)/104857600*1000
ACC = S_ + L_ + BTT                       # 12.04 ms per random block access

def tp(a, b):
    if a == b: return 0.0
    d = DIST.get((a,b)) or DIST.get((b,a))
    return d*1000/V*1000

# read frequencies per site (Phase 0 Section 4.1)
F = {"Q1":[120,400,250,90], "Q2":[30,90,60,20], "Q3":[40,150,100,35], "Q4":[25,60,45,20],
     "Q5":[60,180,120,50],  "Q6":[15,50,30,10], "Q7":[20,70,45,15],   "Q8":[25,80,55,20],
     "Q9":[5,10,5,5],
     "U1":[3000,11000,7000,2200], "U2":[400,1500,900,300], "U3":[350,1300,850,280]}
f = lambda q, s: F[q][SITES.index(s)]

print("="*100)
print("PART A — LOCALITY OF THE FRAGMENTED ALLOCATION")
print("="*100)
local_tx  = sum(sum(F[q]) for q in ["Q1","Q2","Q3","Q4","Q5","Q7","U1","U2","U3"])
cross_tx  = sum(sum(F[q]) for q in ["Q6","Q8","Q9"])
remote_acc = cross_tx * 3                 # each cross-site query touches 3 remote sites
print(f"  transactions served entirely locally : {local_tx:>8,}/day")
print(f"  cross-site transactions (Q6, Q8, Q9) : {cross_tx:>8,}/day")
print(f"  remote fragment accesses they cause  : {remote_acc:>8,}/day")
print(f"  locality = 1 - {remote_acc:,}/{local_tx+cross_tx*4:,} = "
      f"{100*(1-remote_acc/(local_tx+cross_tx*4)):.2f}% of global accesses are local")
import local_schemas as LS
print(f"  + local transactions L1-L8 (local autonomy, always local): {LS.LOCAL_TX_TOTAL:,}/day")
tot_all = local_tx + LS.LOCAL_TX_TOTAL + cross_tx*4
print(f"  locality including local transactions = {100*(1-remote_acc/tot_all):.2f}%")

print("\n" + "="*100)
print("PART B — THE REPLICATION BREAK-EVEN")
print("="*100)
print("  A local replica saves, per read:        Td + 2Tp  = %.2f .. %.2f ms" %
      (TD+2*tp("S1","S2"), TD+2*tp("S1","S4")))
print("  A replica costs, per update:  local_update + 2Tp  = %.2f .. %.2f ms" %
      (2*ACC*3+2*tp("S1","S2"), 2*ACC*3+2*tp("S1","S4")))
lo = (2*ACC*3+2*tp("S1","S2")) / (TD+2*tp("S1","S2"))
hi = (2*ACC*3+2*tp("S1","S4")) / (TD+2*tp("S1","S4"))
print(f"\n  => a fragment must be read {hi:.0f}x to {lo:.0f}x more often than it is updated,")
print(f"     AT THAT SITE, before a replica breaks even.")

# ------------------------------------------------------------------ fragments
print("\n" + "="*100)
print("PART C — ALL BENEFICIAL SITES: FRAGMENTED RELATIONS")
print("="*100)
UPD = 72.24        # local single-record update (2 index + 1 data, read-modify-write)

# reads of a remote fragment: only Q6 and Q8 leave their site
CROSS = {"F1": ["Q6","Q8","Q9"], "F8": ["Q6"], "F6": ["Q8"]}
# writes landing on each fragment at its HOME site, per day network-wide
WRITES = {
    "F1": ("container lifecycle: 41,000 inserts + 41,000 deletes + 6,160 migrations", 88_160),
    "F2": ("U3 clearance + lifecycle", 2_780 + 82_000),
    "F6": ("U1 gate moves", 23_200),
    "F8": ("U3 clearance + declaration filing", 2_780 + 41_000),
}
SHARE = {"S1":0.15, "S2":0.40, "S3":0.30, "S4":0.15}

for fid in ["F1", "F6", "F8"]:
    desc, w_total = WRITES[fid]
    print(f"\n  {fid}  (writes: {desc} = {w_total:,}/day network-wide)")
    print(f"   {'home':<6}{'replica at':<12}{'benefit ms/day':>16}{'cost ms/day':>16}"
          f"{'B - C':>18}  decision")
    for home in ["S2"]:                                   # worst case: the busiest home
        w_home = w_total * SHARE[home]
        for s in SITES:
            if s == home: continue
            ben = sum(f(q, s) * (TD + 2*tp(s, home)) for q in CROSS.get(fid, []))
            cost = w_home * (UPD + 2*tp(home, s))
            print(f"   {home:<6}{s:<12}{ben:>16,.0f}{cost:>16,.0f}{ben-cost:>18,.0f}"
                  f"  {'REPLICATE' if ben>cost else 'no'}")

# ------------------------------------------------------------------ globals
print("\n" + "="*100)
print("PART D — ALL BENEFICIAL SITES: UNFRAGMENTED RELATIONS")
print("="*100)
# (id, name, blocks, reading queries, assumed updates/day, update cost ms)
GLOB = [
    ("G1","PORT",            1, ["Q1","Q2","Q3","Q4","Q5","Q7","Q9"], 0.01, 24.08),
    ("G2","SHIPPING_LINE",   3, ["Q7"],                          0.10, 24.08),
    ("G3","VESSEL",         11, ["Q4","Q7"],                     1.00, 72.24),
    ("G4","HS_CODE_MASTER", 69, [],                              0.20, 72.24),
    ("G5","SERVICE",         1, ["Q8"],                          0.01, 24.08),
    ("G6","PINCODE",       225, [],                              0.10, 72.24),
    ("G7","CONSIGNEE_H",   430, ["Q6","Q8"],                    20.00, 72.24),
    ("G8","CONSIGNEE_R",   831, [],                             20.00, 72.24),
    ("G9","CONSIGNEE_PHONE",235,[],                             15.00, 72.24),
]
HOME = "S2"
alloc = {}
for gid, name, blk, reads, upd, ucost in GLOB:
    print(f"\n  {gid} {name}  ({blk} blocks, reads: {reads or 'NONE in the workload'}, "
          f"{upd}/day updates)")
    if not reads:
        alloc[gid] = [HOME]
        print(f"     no read demand anywhere -> benefit = 0 at every site. "
              f"SINGLE COPY at {HOME}.")
        continue
    print(f"   {'replica at':<12}{'reads/day':>11}{'benefit ms/day':>16}"
          f"{'cost ms/day':>14}{'B - C':>14}  decision")
    sites = [HOME]
    for s in SITES:
        if s == HOME: continue
        r = sum(f(q, s) for q in reads)
        if name == "CONSIGNEE_H" and s == "S3":
            r += 960                                   # L5: exporter FK check, local transaction
        ben = r * (TD + 2*tp(s, HOME))
        cost = upd * (ucost + 2*tp(HOME, s))
        ok = ben > cost
        if ok: sites.append(s)
        print(f"   {s:<12}{r:>11,}{ben:>16,.1f}{cost:>14,.1f}{ben-cost:>14,.1f}"
              f"  {'REPLICATE' if ok else 'no'}")
    alloc[gid] = sites

print("\n" + "="*100)
print("PART E — FINAL ALLOCATION")
print("="*100)
print(f"  {'Relation':<22}{'copies':>7}  sites")
for gid, name, blk, *_ in GLOB:
    print(f"  {name:<22}{len(alloc[gid]):>7}  {', '.join(sorted(alloc[gid]))}")

print("\n  Fragments F1-F12: exactly one copy each, at the site named by its port predicate.")

# storage totals
DATA = {"S1":104444, "S2":278507, "S3":208882, "S4":104444}
IDX  = {"S1":42085,  "S2":112206, "S3":84158,  "S4":42085}
GBLK = {g[0]: g[2] for g in GLOB}
print(f"\n  {'Site':<6}{'core data':>11}{'core idx':>10}{'local data':>12}{'local idx':>11}"
      f"{'global rel':>12}{'total':>10}{'MB':>8}")
grand = 0
for s in SITES:
    rep = sum(GBLK[g] for g in alloc if s in alloc[g])
    tot = DATA[s] + IDX[s] + LS.LOCAL_DATA[s] + LS.LOCAL_IDX[s] + rep
    grand += tot
    print(f"  {s:<6}{DATA[s]:>11,}{IDX[s]:>10,}{LS.LOCAL_DATA[s]:>12,}{LS.LOCAL_IDX[s]:>11,}"
          f"{rep:>12,}{tot:>10,}{tot*4096/1e6:>8.0f}")
print(f"  {'ALL':<6}{sum(DATA.values()):>11,}{sum(IDX.values()):>10,}"
      f"{sum(LS.LOCAL_DATA.values()):>12,}{sum(LS.LOCAL_IDX.values()):>11,}"
      f"{sum(sum(GBLK[g] for g in alloc if s in alloc[g]) for s in SITES):>12,}"
      f"{grand:>10,}{grand*4096/1e6:>8.0f}")
