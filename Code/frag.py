#!/usr/bin/env python3
"""Vertical fragmentation: attribute affinity, BEA clustering, split quality.
Assignment 1 Phase 3 — Container Terminal & Port Logistics Network."""

SITES = ["S1", "S2", "S3", "S4"]

# Phase 0 Section 4.1 — accesses per day, per site
FREQ = {
    "Q1": [120, 400, 250, 90], "Q2": [30, 90, 60, 20], "Q3": [40, 150, 100, 35],
    "Q4": [25, 60, 45, 20],    "Q5": [60, 180, 120, 50], "Q6": [15, 50, 30, 10],
    "Q7": [20, 70, 45, 15],    "Q8": [25, 80, 55, 20],
    "Q9": [5, 10, 5, 5],
    "U1": [3000, 11000, 7000, 2200], "U2": [400, 1500, 900, 300],
    "U3": [350, 1300, 850, 280],
}
TOT = {q: sum(f) for q, f in FREQ.items()}

RELATIONS = {
    "CONTAINER": {
        "attrs": ["cont_id", "size_ft", "cont_type", "tare_wt", "gross_wt", "seal_no",
                  "hazmat_class", "line_id", "consignee_id", "invoice_value",
                  "customs_status", "cur_port_id", "voyage_id"],
        "use": {
            "Q1": [1, 2, 3, 5, 6, 12], "Q2": [1, 7, 12], "Q3": [1, 11, 12],
            "Q5": [1, 2, 4, 5, 12],    "Q6": [1, 9, 12], "Q7": [1, 2, 8, 12, 13],
            "Q8": [1, 9, 10, 12],      "Q9": [1, 5, 12],
            "U1": [1, 6, 11], "U2": [1, 2, 7], "U3": [1, 11],
        },
        "sizes": [11, 4, 4, 4, 4, 12, 3, 4, 4, 8, 10, 4, 4],
    },
    "CUSTOMS_DECL": {
        "attrs": ["decl_id", "cont_id", "hs_code", "duty_amt", "filed_on",
                  "cleared_on", "officer_id"],
        "use": {"Q3": [1, 2, 5, 6], "Q6": [1, 2, 4], "U3": [1, 2, 6]},
        "sizes": [4, 11, 8, 8, 4, 4, 4],
    },
    "VOYAGE": {
        "attrs": ["voyage_id", "vessel_id", "port_id", "eta", "ata", "atd",
                  "berth_no", "status"],
        "use": {"Q4": [1, 2, 3, 4, 5, 7, 8], "Q7": [1, 2, 3, 5], "Q9": [1, 6]},
        "sizes": [4, 4, 4, 8, 8, 8, 4, 10],
    },
    "CONSIGNEE": {
        "attrs": ["consignee_id", "name", "street_line", "area", "pincode", "gstin"],
        "use": {"Q6": [1, 2], "Q8": [1, 2]},
        "sizes": [4, 40, 40, 20, 6, 15],
    },
    "GATE_MOVE": {
        "attrs": ["move_id", "cont_id", "port_id", "ts", "direction", "truck_no",
                  "gate_no", "operator_id"],
        "use": {"Q8": [2, 3, 4, 5], "U1": [1, 2, 3, 4, 5, 6, 7, 8]},
        "sizes": [4, 11, 4, 8, 1, 10, 4, 4],
    },
}


def affinity(n, use):
    aff = [[0] * n for _ in range(n)]
    for q, cols in use.items():
        f = TOT[q]
        for i in cols:
            for j in cols:
                aff[i - 1][j - 1] += f
    return aff


def bea(aff):
    """Bond energy clustering. Returns the column order (0-based indices)."""
    n = len(aff)
    bond = lambda x, y: sum(aff[z][x] * aff[z][y] for z in range(n))
    order = [0, 1]                       # first two columns placed as-is
    trace = []
    for k in range(2, n):
        best, bestpos, conts = None, None, []
        for pos in range(len(order) + 1):
            left = order[pos - 1] if pos > 0 else None
            right = order[pos] if pos < len(order) else None
            b_lk = bond(left, k) if left is not None else 0
            b_kr = bond(k, right) if right is not None else 0
            b_lr = bond(left, right) if (left is not None and right is not None) else 0
            cont = 2 * b_lk + 2 * b_kr - 2 * b_lr
            conts.append((pos + 1, cont))
            if best is None or cont > best:
                best, bestpos = cont, pos
        order.insert(bestpos, k)
        trace.append((k + 1, conts, best, bestpos + 1))
    return order, trace


def split_quality(order, use, n):
    """Evaluate every binary split point of the clustered order."""
    rows = []
    for cut in range(1, n):
        TA = set(order[:cut]);  TB = set(order[cut:])
        TQ = BQ = OQ = []
        TQ = [q for q, c in use.items() if {i - 1 for i in c} <= TA]
        BQ = [q for q, c in use.items() if {i - 1 for i in c} <= TB]
        OQ = [q for q, c in use.items()
              if not ({i - 1 for i in c} <= TA or {i - 1 for i in c} <= TB)]
        CTQ, CBQ, COQ = (sum(TOT[q] for q in g) for g in (TQ, BQ, OQ))
        rows.append(dict(cut=cut, TA=sorted(i + 1 for i in TA), TB=sorted(i + 1 for i in TB),
                         TQ=sorted(TQ), BQ=sorted(BQ), OQ=sorted(OQ),
                         CTQ=CTQ, CBQ=CBQ, COQ=COQ, Z=CTQ * CBQ - COQ * COQ))
    return rows


def show(name, drop_key=True):
    R = RELATIONS[name]
    attrs_all = R["attrs"]
    if drop_key:
        # The primary key is replicated into EVERY vertical fragment by construction,
        # so it cannot constrain the split and is excluded from the partitioning analysis.
        keep = list(range(2, len(attrs_all) + 1))          # 1-based, drop A1
        remap = {old: new for new, old in enumerate(keep, start=1)}
        use = {q: sorted(remap[a] for a in c if a in remap) for q, c in R["use"].items()}
        use = {q: c for q, c in use.items() if c}
        attrs = [attrs_all[i - 1] for i in keep]
        label = {new: f"A{old}" for old, new in remap.items()}
    else:
        use, attrs = R["use"], attrs_all
        label = {i: f"A{i}" for i in range(1, len(attrs) + 1)}
    n = len(attrs)
    aff = affinity(n, use)
    L = lambda i: label[i + 1]
    print(f"\n{'='*78}\nRELATION: {name}   ({n} attributes after key exclusion)\n{'='*78}")

    print("\nATTRIBUTE USAGE MATRIX (rows = transactions)")
    print("      " + "".join(f"{L(i):>6}" for i in range(n)) + "    freq")
    for q in sorted(use):
        row = ["1" if (i + 1) in use[q] else "0" for i in range(n)]
        print(f"  {q}  " + "".join(f"{v:>6}" for v in row) + f"  {TOT[q]:>7}")

    print("\nATTRIBUTE AFFINITY MATRIX")
    print("      " + "".join(f"{L(i):>8}" for i in range(n)))
    for i in range(n):
        print(f"  {L(i):<4}" + "".join(f"{aff[i][j]:>8}" for j in range(n)))

    order, trace = bea(aff)
    print("\nBEA ORDERING")
    for col, conts, best, pos in trace:
        print(f"  place {L(col-1)}: max contribution {best:,} at position {pos}")
    print("  clustered order: " + " ".join(L(i) for i in order))

    print("\nCLUSTERED AFFINITY MATRIX")
    print("      " + "".join(f"{L(i):>8}" for i in order))
    for i in order:
        print(f"  {L(i):<4}" + "".join(f"{aff[i][j]:>8}" for j in order))

    print("\nSPLIT QUALITY  Z = (CTQ x CBQ) - COQ^2")
    rows = split_quality(order, use, n)
    for r in rows:
        ta = ",".join(L(j) for j in order[:r['cut']])
        tb = ",".join(L(j) for j in order[r['cut']:])
        print(f"  cut {r['cut']:>2}: TA={{{ta}}}  TB={{{tb}}}")
        print(f"          TQ={r['TQ']} BQ={r['BQ']} OQ={r['OQ']}")
        print(f"          CTQ={r['CTQ']:,}  CBQ={r['CBQ']:,}  COQ={r['COQ']:,}   Z={r['Z']:,}")
    best = max(rows, key=lambda r: r["Z"])
    print(f"\n  BEST SPLIT: Z = {best['Z']:,} at cut {best['cut']}")
    ta = [order[j] for j in range(best['cut'])]
    tb = [order[j] for j in range(best['cut'], n)]
    key = R["attrs"][0]; ksz = R["sizes"][0]
    idx = lambda i: int(L(i)[1:])
    print(f"    F_a: {key} (key) + " + ", ".join(f"{L(i)}={attrs[i]}" for i in sorted(ta, key=idx)))
    print(f"    F_b: {key} (key) + " + ", ".join(f"{L(i)}={attrs[i]}" for i in sorted(tb, key=idx)))
    sa = ksz + sum(R["sizes"][idx(i)-1] for i in ta)
    sb = ksz + sum(R["sizes"][idx(i)-1] for i in tb)
    print(f"    record sizes: F_a={sa}B  F_b={sb}B   (original {sum(R['sizes'])}B, "
          f"overhead +{sa+sb-sum(R['sizes'])}B from key replication)")
    cold = [i for i in range(n) if not any((i + 1) in c for c in use.values())]
    if cold:
        print("    COLD (no transaction touches): " + ", ".join(f"{L(i)}={attrs[i]}" for i in cold))



def exhaustive(name):
    """Evaluate every binary partition of the non-key attributes (BEA checks only contiguous cuts)."""
    from itertools import combinations
    R = RELATIONS[name]
    attrs = list(range(2, len(R["attrs"]) + 1))
    use = {q: [a for a in c if a != 1] for q, c in R["use"].items()}
    use = {q: c for q, c in use.items() if c}
    def Z(TA):
        TA, TB = set(TA), set(attrs) - set(TA)
        T = sum(TOT[q] for q, c in use.items() if set(c) <= TA)
        Bq = sum(TOT[q] for q, c in use.items() if set(c) <= TB)
        O = sum(TOT[q] for q, c in use.items() if not (set(c) <= TA or set(c) <= TB))
        return T * Bq - O * O, T, Bq, O
    res = sorted(((Z(t), t) for k in range(1, len(attrs)) for t in combinations(attrs, k)),
                 key=lambda x: -x[0][0])
    n = 2 ** len(attrs) - 2
    (z, T, Bq, O), ta = res[0]
    ties = [r for r in res if r[0][0] == z]
    smallest = min(ties, key=lambda r: min(sum(R["sizes"][a-1] for a in r[1]),
                                           sum(R["sizes"][a-1] for a in set(attrs)-set(r[1]))))
    ta = smallest[1]
    hot = ta if sum(R["sizes"][a-1] for a in ta) <= sum(R["sizes"][a-1] for a in set(attrs)-set(ta)) \
        else tuple(sorted(set(attrs) - set(ta)))
    print(f"\n  EXHAUSTIVE over all {n:,} binary partitions: optimum Z = {z:,}"
          f"  ({len(ties)} tied partitions)")
    print(f"    smallest hot fragment: {R['attrs'][0]} + " +
          ", ".join(f"A{a}={R['attrs'][a-1]}" for a in sorted(hot)))
    print(f"    CTQ={T:,}  CBQ={Bq:,}  COQ={O:,}")
    return z, res

for rel in ["CONTAINER", "CUSTOMS_DECL", "VOYAGE", "CONSIGNEE", "GATE_MOVE"]:
    show(rel)

zc, res = exhaustive("CONTAINER")
bea_z = 102_657_375
rank = 1 + sum(1 for r in res if r[0][0] > bea_z)
print(f"    BEA's contiguous answer (Z = {bea_z:,}) ranks {rank} of {len(res):,}; "
      f"gap {100*(zc-bea_z)/zc:.1f}%")

# Whole-tuple operations: what happens if the container lifecycle enters the matrix
import copy
R2 = copy.deepcopy(RELATIONS["CONTAINER"])
RELATIONS["CONTAINER_WITH_LIFECYCLE"] = R2
R2["use"]["M1"] = list(range(1, 14))
TOT["M1"] = 82_000
zl, _ = exhaustive("CONTAINER_WITH_LIFECYCLE")
print(f"  => with 82,000 whole-tuple ops/day admitted, best Z = {zl:,}")
