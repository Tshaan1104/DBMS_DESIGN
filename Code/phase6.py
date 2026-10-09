#!/usr/bin/env python3
"""Phase 6 — work area space, system specification, response times."""
from math import ceil
import local_schemas as LS

B, S_, L_ = 4096, 8.0, 4.0
BTT = (B + 128) / 104857600 * 1000
ACC = S_ + L_ + BTT                       # 12.04 ms, one random block access
TD  = 1024 / 12.5e6 * 1000
V   = 2.7e8
DIST = {("S1","S2"):700,("S1","S3"):700,("S1","S4"):2000,
        ("S2","S3"):1300,("S2","S4"):1900,("S3","S4"):1650}
def tp(a,b):
    if a==b: return 0.0
    return (DIST.get((a,b)) or DIST.get((b,a)))*1000/V*1000

SITES=["S1","S2","S3","S4"]
scan = lambda nb: S_ + L_ + nb*BTT        # sequential, one seek
rand = lambda n:  ACC * n                 # n scattered accesses

# block counts per site  (F4/F5 corrected in this phase)
BLK = {
 "F1":{"S1":989,"S2":2637,"S3":1978,"S4":989},      # CONTAINER_C
 "F2":{"S1":605,"S2":1612,"S3":1209,"S4":605},      # CONTAINER_G
 "F3":{"S1":7,"S2":18,"S3":14,"S4":7},              # VOYAGE
 "F4":{"S1":766,"S2":2042,"S3":1531,"S4":766},      # YARD_SLOT  (corrected)
 "F5":{"S1":1,"S2":3,"S3":2,"S4":1},                # YARD_BLOCK (corrected)
 "F6":{"S1":101075,"S2":269532,"S3":202149,"S4":101075},
 "F7":{"S1":1,"S2":1,"S3":1,"S4":1},                # TARIFF
 "F8":{"S1":709,"S2":1890,"S3":1418,"S4":709},      # CUSTOMS_DECL
 "F9":{"S1":238,"S2":633,"S3":475,"S4":238},
 "G2":3, "G3":11, "G5":1, "G7":430,
}
CONT = {"S1":75_000,"S2":200_000,"S3":150_000,"S4":75_000}

print("="*94)
print("PART A — WHEN DOES AN INDEX BEAT A SCAN?")
print("="*94)
print("  index lookup = 3 random accesses = %.2f ms      sequential block = %.4f ms" % (rand(3), BTT))
print(f"\n  {'Fragment':<16}{'blocks @S2':>12}{'scan ms':>10}{'break-even N':>14}")
for f,label in [("F1","CONTAINER_C"),("F8","CUSTOMS_DECL"),("F6","GATE_MOVE")]:
    nb = BLK[f]["S2"]; sc = scan(nb)
    per = rand(3) if f!="F6" else rand(2)      # F6 non-leaf buffered
    print(f"  {label:<16}{nb:>12,}{sc:>10,.1f}{sc/per:>14.1f}")
print("\n  => the primary indexes on F1/F8 pay only for single-record access (U1, U3).")
print("     Any query needing more than ~4 records should scan. The optimiser must")
print("     choose per query — the same fragment is probed by U1 and scanned by Q1.")

# ---------------------------------------------------------------- work areas
print("\n" + "="*94)
print("PART B — WORK AREA SPACE per query (at S2, the busiest site)")
print("="*94)
WA = []
def add(q, desc, kb):  WA.append((q, desc, kb))

add("Q1","hash table on one yard block's slots (250) joined to container rows",
    250*(38+54+33)/1024)
add("Q2","build side: hazmat containers (5% of 200,000) x 54 B",
    0.05*CONT["S2"]*54/1024)
add("Q3","build side: open declarations (10% of 180,000) x 43 B",
    0.10*180_000*43/1024)
add("Q4","today's voyages (~10) joined to VESSEL", 10*(50+52)/1024)
add("Q5","build side: YARD_SLOT_2 (220,000 x 38 B) for the hash join",
    220_000*38/1024)
add("Q6","pipelined scan + per-consignee result (~20 rows)", 64)
add("Q7","build side: VOYAGE_2 (1,440 x 50 B) + 360 aggregate groups",
    (1440*50+360*24)/1024)
add("Q8","4 partial results merged at the originating site (~20 containers)", 64)
for q, d, kb in sorted(WA, key=lambda t:-t[2]):
    print(f"  {q}  {kb:>10,.0f} KB   {d}")
WAS = max(kb for _,_,kb in WA)
print(f"\n  WAS = {WAS:,.0f} KB = {WAS/1024:.2f} MB   (driven by Q5)")

print("\n  Q5 — the work area is a CHOICE, not a requirement:")
hj = scan(BLK['F4']['S2']) + scan(BLK['F1']['S2'])
inl = rand(3) * 220_000
print(f"    hash join      : {WAS/1024:6.2f} MB work area, {hj:10,.0f} ms")
print(f"    index nested loop: {250*125/1024/1024:6.2f} MB work area, {inl:10,.0f} ms "
      f"({inl/60000:.0f} min)")
print(f"    => {WAS/1024:.1f} MB of buffer buys a {inl/hj:,.0f}x speed-up.")

# ---------------------------------------------------------------- memory
print("\n" + "="*94)
print("PART C — MEMORY PER SITE")
print("="*94)
p_leaf, p_int = (B-8)//19, (B+11)//19
def nonleaf(n):
    leaves = ceil(n/p_leaf); tot, nodes = 0, leaves
    while nodes > 1:
        nodes = ceil(nodes/p_int); tot += nodes
    return tot
GM = {"S1":9_000_000,"S2":24_000_000,"S3":18_000_000,"S4":9_000_000}
SMALL_IDX = {"S1":23,"S2":45,"S3":37,"S4":23}      # all non-F6 core index blocks
_h, _tot, _leaves = LS.bplus(LS.TUP["RORO_VEHICLE"], 17)
LOCAL_PIN = {"S1": 0, "S2": LS.LOCAL_IDX["S2"], "S3": _tot - _leaves, "S4": LS.LOCAL_IDX["S4"]}
SMALL_IDX = {k: SMALL_IDX[k] + LOCAL_PIN[k] for k in SMALL_IDX}   # + pinned local index blocks
CONC = 4
print(f"  {'Site':<6}{'WAS x4':>10}{'B+ non-leaf':>13}{'small idx':>11}"
      f"{'repl. reln':>12}{'scan bufs':>11}{'DBMS':>8}{'TOTAL':>10}")
MEM = {}
for s in SITES:
    was = WAS/1024 * CONC * (CONT[s]/CONT["S2"])           # work area scales with data
    nl  = nonleaf(GM[s]) * B / 1e6
    si  = SMALL_IDX[s] * B / 1e6
    rep = 16 * B / 1e6
    buf = 8 * 64 * B / 1e6
    dbms = 64
    tot = was + nl + si + rep + buf + dbms
    MEM[s] = tot
    print(f"  {s:<6}{was:>10.1f}{nl:>13.2f}{si:>11.2f}{rep:>12.2f}"
          f"{buf:>11.2f}{dbms:>8}{tot:>10.1f}")
print("   (MB)")

# ---------------------------------------------------------------- response times
print("\n" + "="*94)
print("PART D — RESPONSE TIME PER QUERY (ms)")
print("="*94)
def q_local(s):
    b = BLK
    return {
      "Q1": scan(3) + rand(2) + scan(b["F1"][s]) + scan(b["F2"][s]),
      "Q2": scan(b["F1"][s]) + scan(b["F4"][s]) + scan(b["F5"][s]),
      "Q3": scan(b["F8"][s]) + scan(b["F2"][s]),
      "Q4": scan(b["F3"][s]) + scan(11),
      "Q5": scan(b["F4"][s]) + scan(b["F1"][s]),
      "Q7": scan(b["F1"][s]) + scan(b["F3"][s]) + scan(11) + scan(3),
    }
def q6_part(s):  return scan(BLK["F1"][s]) + scan(BLK["F8"][s])
def q8_part(s):
    n = round(40 * CONT[s]/500_000)                   # 40 containers network-wide, by site share
    return scan(BLK["F1"][s]) + rand(2)*n + scan(BLK["F4"][s]) + scan(BLK["F7"][s])

print(f"  {'Query':<7}" + "".join(f"{s:>12}" for s in SITES) + "   notes")
for q in ["Q1","Q2","Q3","Q4","Q5","Q7"]:
    print(f"  {q:<7}" + "".join(f"{q_local(s)[q]:>12,.0f}" for s in SITES) + "   local only")
for q, fn in [("Q6", q6_part), ("Q8", q8_part)]:
    row = []
    for s in SITES:
        parts = [fn(x) + (TD + 2*tp(s,x) if x!=s else 0) for x in SITES]
        extra = scan(BLK["G7"]) + 2*tp(s,"S2") if s!="S2" else scan(BLK["G7"])
        row.append(max(parts) + extra*0.0 + 5)         # parallel fan-out + merge
    print(f"  {q:<7}" + "".join(f"{v:>12,.0f}" for v in row) + "   4 sites in parallel")
    row_ser = []
    for s in SITES:
        row_ser.append(sum(fn(x) + (TD + 2*tp(s,x) if x!=s else 0) for x in SITES))
    print(f"  {'':<7}" + "".join(f"{v:>12,.0f}" for v in row_ser) + "   if executed serially")

print(f"  {'Q9':<7}" + "".join(f"{LS.q9_response(s)[0]:>12,.0f}" for s in SITES)
      + "   4 sites in parallel, a different sub-query at each")
print(f"  {'':<7}" + "".join(f"{LS.q9_response(s)[1]:>12,.0f}" for s in SITES)
      + "   if executed serially")
print("\n  Q9 local sub-queries:")
for x in SITES:
    ms, plan = LS.q9_part(x)
    print(f"    {x}: {ms:7.1f} ms   {plan}")

print(f"\n  {'Update':<7}" + "".join(f"{s:>12}" for s in SITES))
print(f"  {'U1':<7}" + "".join(f"{rand(3)+rand(3):>12,.0f}" for s in SITES)
      + "   F2 probe + F6 insert")
print(f"  {'U2':<7}" + "".join(f"{rand(3)+2*rand(3):>12,.0f}" for s in SITES)
      + "   F1 probe + F4 update")
print(f"  {'U3':<7}" + "".join(f"{2*rand(3)+2*rand(3):>12,.0f}" for s in SITES)
      + "   F2 update + F8 update")

# ---------------------------------------------------------------- utilisation
print("\n" + "="*94)
print("PART E — DISK UTILISATION")
print("="*94)
FREQ = {"Q1":[120,400,250,90],"Q2":[30,90,60,20],"Q3":[40,150,100,35],"Q4":[25,60,45,20],
        "Q5":[60,180,120,50],"Q6":[15,50,30,10],"Q7":[20,70,45,15],"Q8":[25,80,55,20],
        "U1":[3000,11000,7000,2200],"U2":[400,1500,900,300],"U3":[350,1300,850,280]}
print(f"  {'Site':<6}{'busy ms/day':>14}{'busy min/day':>15}{'utilisation':>14}")
for i, s in enumerate(SITES):
    t = sum(FREQ[q][i]*q_local(s)[q] for q in ["Q1","Q2","Q3","Q4","Q5","Q7"])
    t += FREQ["Q6"][i]*q6_part(s) + FREQ["Q8"][i]*q8_part(s)
    t += FREQ["U1"][i]*rand(6) + FREQ["U2"][i]*rand(9) + FREQ["U3"][i]*rand(12)
    g = t
    t += LS.Q9_FREQ[i] * LS.q9_part(s)[0]
    loc = sum(f * ms for tid, site, nm, ops, f, ms in LS.LOCAL_TX if site == s)
    t += loc
    print(f"  {s:<6}{t:>14,.0f}{t/60000:>15.1f}{100*t/86_400_000:>13.2f}%"
          f"   (of which local transactions {loc/60000:.1f} min)")
