#!/usr/bin/env python3
"""Phase 4 — physical design: blocking, access methods, disk timings."""
from math import ceil

# ---- frozen assumptions (Phase 0 Section 4.2)
B      = 4096          # block size, bytes
G      = 128           # inter-block gap, bytes
PTR    = 8             # block pointer, bytes
S      = 8.0           # average seek, ms
L      = 4.0           # average rotational latency, ms
XFER   = 104_857_600   # disk transfer rate, bytes/sec
BTT    = (B + G) / XFER * 1000        # block transfer time, ms
PKT    = 1024          # packet, bytes
BW     = 12.5e6        # 100 Mbps, bytes/sec
TD     = PKT / BW * 1000              # transmission delay per packet, ms
V      = 2.7e8         # propagation speed, m/s

DIST = {  # km, Phase 0 Section 2.2
    ("S1","S2"):700, ("S1","S3"):700, ("S1","S4"):2000,
    ("S2","S3"):1300, ("S2","S4"):1900, ("S3","S4"):1650,
}
def tp(a, b):
    d = DIST.get((a,b)) or DIST.get((b,a))
    return d * 1000 / V * 1000        # ms

SHARE = {"S1":0.15, "S2":0.40, "S3":0.30, "S4":0.15}

# id, name, record bytes, total tuples, key attr, key bytes
FRAGS = [
    ("F1","CONTAINER_C",        54,   500_000, "cont_id",  11),
    ("F2","CONTAINER_G",        33,   500_000, "cont_id",  11),
    ("F3","VOYAGE",             50,     3_600, "voyage_id", 4),
    ("F4","YARD_SLOT",          38,    60_000, "slot PK",  19),
    ("F5","YARD_BLOCK",         12,       240, "blk PK",    7),
    ("F6","GATE_MOVE",          46,60_000_000, "move_id",   4),
    ("F7","TARIFF",             18,        40, "tar PK",   10),
    ("F8","CUSTOMS_DECL",       43,   450_000, "cont_id",  11),
    ("F9","BILL_OF_LADING",     36,   180_000, "bl_no",    12),
    ("F10","CONTAINER_REEFER",  23,    40_000, "cont_id",  11),
    ("F11","CONTAINER_TANK",    23,    15_000, "cont_id",  11),
    ("F12","CONTAINER_OPEN_TOP",15,    10_000, "cont_id",  11),
]
GLOBALS = [
    ("G1","PORT",70,4,"port_id",4), ("G2","SHIPPING_LINE",84,120,"line_id",4),
    ("G3","VESSEL",52,800,"vessel_id",4), ("G4","HS_CODE_MASTER",56,5000,"hs_code",8),
    ("G5","SERVICE",39,10,"service_code",6), ("G6","PINCODE",46,20000,"pincode",6),
    ("G7","CONSIGNEE_H",44,40000,"consignee_id",4),
    ("G8","CONSIGNEE_R",85,40000,"consignee_id",4),
    ("G9","CONSIGNEE_PHONE",16,60000,"(cid,phone)",16),
]

blocks   = lambda n, r: ceil(n * r / B)                  # spanned records
scan_ms  = lambda nb: S + L + nb * BTT                   # one seek, sequential
rand_ms  = lambda nb: (S + L + BTT) * nb                 # scattered accesses


def multilevel(entries, entry_sz):
    """Blocks per level for a multilevel index; returns (levels, total_blocks)."""
    bfri = B // entry_sz
    lvls, tot, e = 0, 0, entries
    while True:
        nb = ceil(e / bfri)
        lvls += 1; tot += nb
        if nb <= 1:
            return lvls, tot, bfri
        e = nb


def bplus(entries, key_sz):
    """B+ tree: leaf/internal fanout, height, total blocks."""
    p_leaf = (B - PTR) // (key_sz + PTR)                 # entries + next-leaf pointer
    p_int  = (B + key_sz) // (PTR + key_sz)              # p pointers, p-1 keys
    leaves = ceil(entries / p_leaf)
    h, tot, nodes = 1, leaves, leaves
    while nodes > 1:
        nodes = ceil(nodes / p_int); tot += nodes; h += 1
    return p_leaf, p_int, h, tot


print("=" * 96)
print("DERIVED DISK PARAMETERS")
print("=" * 96)
print(f"  block transfer time  Tr = (B + g)/transfer rate = ({B} + {G})/{XFER:,} "
      f"= {BTT:.4f} ms")
print(f"  transmission delay   Td = {PKT}/{BW:,.0f} = {TD:.4f} ms per packet")
print(f"  propagation delay    Tp = distance / {V:.1e} m/s")
for (a, b), d in sorted(DIST.items()):
    print(f"      {a}-{b}: {d:>5} km -> Tp = {tp(a,b):.2f} ms,  2Tp = {2*tp(a,b):.2f} ms")

print("\n" + "=" * 96)
print("BLOCKING — spanned, fixed-length records;  blocks = ceil(n x R / B)")
print("=" * 96)
print(f"{'ID':<5}{'Fragment':<21}{'R':>4}{'bfr':>6}   " +
      "".join(f"{s+' blks':>12}" for s in SHARE) + f"{'total blks':>12}")
tot_blocks = {s: 0 for s in SHARE}
FRAGBLK = {}
for fid, name, r, n, _, _ in FRAGS:
    per = {s: blocks(round(n * SHARE[s]), r) for s in SHARE}
    FRAGBLK[fid] = per
    for s in SHARE:
        tot_blocks[s] += per[s]
    print(f"{fid:<5}{name:<21}{r:>4}{B//r:>6}   " +
          "".join(f"{per[s]:>12,}" for s in SHARE) + f"{sum(per.values()):>12,}")
print(f"{'':<5}{'PER-SITE TOTAL':<21}{'':>4}{'':>6}   " +
      "".join(f"{tot_blocks[s]:>12,}" for s in SHARE) +
      f"{sum(tot_blocks.values()):>12,}")

print(f"\n{'ID':<5}{'Unfragmented relation':<21}{'R':>4}{'bfr':>6}{'tuples':>12}{'blocks':>10}")
gtot = 0
for gid, name, r, n, _, _ in GLOBALS:
    nb = blocks(n, r); gtot += nb
    print(f"{gid:<5}{name:<21}{r:>4}{B//r:>6}{n:>12,}{nb:>10,}")
print(f"{'':<5}{'TOTAL (one copy)':<21}{'':>4}{'':>6}{'':>12}{gtot:>10,}")

# ---------------------------------------------------------------- access methods
print("\n" + "=" * 96)
print("ACCESS METHOD COMPARISON — F6 GATE_MOVE at S2 (largest fragment)")
print("=" * 96)
n_s2   = 24_000_000
nb_s2  = FRAGBLK["F6"]["S2"]
distinct_cont = 6_000_000          # annual container transits at S2
print(f"  records = {n_s2:,}   data blocks = {nb_s2:,}   "
      f"file size = {n_s2*46/1e6:.0f} MB   distinct cont_id = {distinct_cont:,}\n")

rows = []
# (a) heap, no index
rows.append(("(a) Heap file, no index", 0, 0, nb_s2, "full scan"))
# (b) primary (sparse) index on move_id — file ordered by move_id
lv, tb, bfri = multilevel(nb_s2, 4 + PTR)
rows.append((f"(b) Primary index on move_id ({lv} levels, bfri={bfri})", tb, lv, lv + 1,
             "useless: no query searches by move_id"))
# (c) clustering index on cont_id — file ordered by cont_id
lv, tb, bfri = multilevel(distinct_cont, 11 + PTR)
rows.append((f"(c) Clustering index on cont_id ({lv} levels, bfri={bfri})", tb, lv, lv + 1,
             "ordered file conflicts with U1 append"))
# (d) dense secondary index on truck_no
lv, tb, bfri = multilevel(n_s2, 10 + PTR)
rows.append((f"(d) Secondary index on truck_no ({lv} levels, bfri={bfri})", tb, lv, lv + 1,
             "no query searches by truck_no"))
# (e) B+ tree on cont_id over a heap file
pl, pi, h, tb = bplus(n_s2, 11)
rows.append((f"(e) B+ tree on cont_id (h={h}, p_leaf={pl}, p={pi})", tb, h, h + 1,
             "heap file stays append-friendly for U1"))

print(f"{'Method':<58}{'idx blks':>10}{'idx MB':>8}{'accesses':>10}")
for label, ib, lv, acc, note in rows:
    print(f"{label:<58}{ib:>10,}{ib*B/1e6:>8.0f}{acc:>10}")
    print(f"{'':<58}{note}")

print(f"\n  full scan time        = S + L + N x Tr = {scan_ms(nb_s2):,.0f} ms "
      f"({scan_ms(nb_s2)/1000:.1f} s)")
pl, pi, h, tb = bplus(n_s2, 11)
print(f"  B+ tree lookup (one container's ~4 moves) = {h} index + 1 data block "
      f"= {rand_ms(h+1):.2f} ms")
print(f"  speed-up = {scan_ms(nb_s2)/rand_ms(h+1):,.0f}x")
print(f"  index overhead = {tb*B/1e6:.0f} MB on a {n_s2*46/1e6:.0f} MB fragment "
      f"({100*tb*B/(n_s2*46):.0f}%)")

# ---------------------------------------------------------------- chosen methods
print("\n" + "=" * 96)
print("CHOSEN ACCESS METHOD PER FRAGMENT (index blocks at each site)")
print("=" * 96)
CHOICE = {
    "F1": ("primary index on cont_id", "primary", 11),
    "F2": ("primary index on cont_id", "primary", 11),
    "F3": ("primary index on voyage_id", "primary", 4),
    "F4": ("primary index on (block,bay,row,tier)", "primary", 19),
    "F5": ("none - single block", "none", 0),
    "F6": ("B+ tree on cont_id over heap", "bplus", 11),
    "F7": ("none - single block", "none", 0),
    "F8": ("primary index on cont_id", "primary", 11),
    "F9": ("primary index on bl_no", "primary", 12),
    "F10": ("primary index on cont_id", "primary", 11),
    "F11": ("primary index on cont_id", "primary", 11),
    "F12": ("primary index on cont_id", "primary", 11),
}
print(f"{'ID':<5}{'Access method':<40}" + "".join(f"{s:>11}" for s in SHARE) + f"{'accesses':>10}")
idx_tot = {s: 0 for s in SHARE}
for fid, name, r, n, _, _ in FRAGS:
    label, kind, ks = CHOICE[fid]
    per, acc = {}, 1
    for s in SHARE:
        nb = FRAGBLK[fid][s]
        if kind == "none":
            per[s] = 0; acc = 1
        elif kind == "primary":
            lv, tb, _ = multilevel(nb, ks + PTR); per[s] = tb; acc = lv + 1
        else:
            _, _, h, tb = bplus(round(n * SHARE[s]), ks); per[s] = tb; acc = h + 1
        idx_tot[s] += per[s]
    print(f"{fid:<5}{label:<40}" + "".join(f"{per[s]:>11,}" for s in SHARE) + f"{acc:>10}")
print(f"{'':<5}{'INDEX BLOCKS TOTAL':<40}" + "".join(f"{idx_tot[s]:>11,}" for s in SHARE))

# ---------------------------------------------------------------- timings
print("\n" + "=" * 96)
print("FRAGMENT ACCESS TIMES (ms) — full-fragment scan at its home site")
print("=" * 96)
print(f"  local retrieval  = S + L + N x Tr")
print(f"  local update     = 2 x (S + L + Tr) x N_touched")
print(f"  remote retrieval = local + Td_total + 2Tp")
print(f"  remote update    = local + 2Tp\n")
print(f"{'ID':<5}{'Fragment':<21}" + "".join(f"{s+' scan':>13}" for s in SHARE))
for fid, name, r, n, _, _ in FRAGS:
    print(f"{fid:<5}{name:<21}" +
          "".join(f"{scan_ms(FRAGBLK[fid][s]):>13,.1f}" for s in SHARE))

print("\n  Single-record access with the chosen index (any site):")
for fid in ["F1", "F2", "F8"]:
    lv, tb, _ = multilevel(FRAGBLK[fid]["S2"], CHOICE[fid][2] + PTR)
    print(f"    {fid}: {lv} index + 1 data = {rand_ms(lv+1):.2f} ms local; "
          f"update = {2*rand_ms(lv+1):.2f} ms")
_, _, h, _ = bplus(24_000_000, 11)
print(f"    F6: {h} index + 1 data = {rand_ms(h+1):.2f} ms local; "
      f"insert (U1) = append 1 block + {h} index = {rand_ms(h+1)*2:.2f} ms")

print("\n  Remote single-record retrieval of F2 (gate fragment, 33 B result = 1 packet):")
base = rand_ms(multilevel(FRAGBLK['F2']['S2'], 19)[0] + 1)
for a, b in [("S1","S2"), ("S2","S3"), ("S1","S4"), ("S2","S4")]:
    print(f"    {a} -> {b}: {base:.2f} + {TD:.3f} + {2*tp(a,b):.2f} = "
          f"{base + TD + 2*tp(a,b):.2f} ms   "
          f"({(base + TD + 2*tp(a,b))/base:.1f}x the local cost)")
