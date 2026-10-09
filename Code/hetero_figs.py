#!/usr/bin/env python3
"""Figure 5 (three-level schema architecture) and Figure 6 (site-specific local ER extensions)."""
import cairosvg

# reuse the drawing primitives of figs.py (class C) and eer.py (class Canvas) without
# re-running their figure code
for src, marker in [("figs.py", "# ============================================================ FIGURE 1"),
                    ("eer.py", "# ===================================================== FIGURE 1")]:
    exec(open(src).read().split(marker)[0])

GREYFILL = "#E6E6E6"

# ============================================================ FIGURE 5 — architecture
c = C(1600, 960)


def band(y, label):
    c.txt(24, y, label, 18, bold=True, color=MUTED, anchor="start")


def box(cx, cy, w, h, title, subs, dashed=False):
    d = ' stroke-dasharray="8,5"' if dashed else ''
    c.o.append(f'<rect x="{cx-w/2}" y="{cy-h/2}" width="{w}" height="{h}" rx="6" fill="{BG}" '
               f'stroke="{FG}" stroke-width="2.5"{d}/>')
    top = cy - (len(subs) * 25) / 2 - 4
    c.txt(cx, top + 8, title, 24, bold=True)
    for i, ln in enumerate(subs):
        c.txt(cx, top + 34 + i * 25, ln, 19, color=MUTED)


band(28, "EXTERNAL LEVEL")
box(330, 92, 420, 76, "Terminal operations view", ["Q1–Q8, U1–U3"])
box(800, 92, 420, 76, "Port-authority view", ["Q9 over CARGO_IN_CUSTODY"])
box(1330, 92, 380, 76, "Site applications", ["L1–L8, never global"], dashed=True)

band(172, "CONCEPTUAL LEVEL — GLOBAL")
box(650, 262, 1180, 104, "GLOBAL CONCEPTUAL SCHEMA",
    ["19 core relations (Sections 7–8), designed top-down, identical everywhere",
     "+ CARGO_IN_CUSTODY(port_id, cargo_class, tonnes): GAV view over EXP_1 … EXP_4"])
c.arrow(330, 130, 330, 208)
c.arrow(800, 130, 800, 208)

band(348, "MAPPINGS")
box(380, 410, 560, 76, "Fragmentation & allocation schema", ["F1–F12 and replicas (Sections 9, 11)"])
box(960, 410, 560, 76, "Export schemas EXP_1 … EXP_4", ["each site's custody rule, in tonnes (Section 12)"])
c.arrow(380, 314, 380, 370)
c.arrow(960, 314, 960, 370)

band(527, "CONCEPTUAL LEVEL — LOCAL")
LCS = [("LCS_1  New Mangalore", ["core fragments  …_1", "replicas: PORT, SHIPPING_LINE,", "  VESSEL, SERVICE",
                                 "+ TANK_FARM", "+ PIPELINE_TRANSFER"]),
       ("LCS_2  JNPT", ["core fragments  …_2", "replicas + HS_CODE_MASTER,", "  PINCODE, CONSIGNEE_*",
                        "+ RAIL_RAKE, RAKE_LOADING", "+ SEZ_UNIT, BOND_TRANSFER"]),
       ("LCS_3  Chennai", ["core fragments  …_3", "replicas + CONSIGNEE_H", "",
                           "+ RORO_VEHICLE", "+ VEHICLE_INSPECTION"]),
       ("LCS_4  Kolkata / Haldia", ["core fragments  …_4", "replicas: PORT, SHIPPING_LINE,",
                                    "  VESSEL, SERVICE", "+ TIDAL_WINDOW", "+ LIGHTERAGE"])]
XS = [212, 604, 996, 1388]
TOP, HGT, BWD = 545, 232, 376
for x, (t, lines) in zip(XS, LCS):
    c.o.append(f'<rect x="{x-BWD/2}" y="{TOP+HGT-80}" width="{BWD}" height="80" fill="{GREYFILL}" '
               f'stroke="none"/>')
    c.o.append(f'<rect x="{x-BWD/2}" y="{TOP}" width="{BWD}" height="{HGT}" rx="6" fill="none" '
               f'stroke="{FG}" stroke-width="2.5"/>')
    c.txt(x, TOP + 32, t, 22, bold=True)
    for i, ln in enumerate(lines):
        bold = ln.startswith("+")
        c.txt(x - BWD / 2 + 16, TOP + 64 + i * 30 + (10 if i >= 3 else 0), ln, 19, bold=bold,
              color=FG if bold else MUTED, anchor="start")
    c.elbow(380, 448, x + 120, TOP, my=470)
    c.elbow(960, 448, x + 172, TOP, my=486)
c.o.append(f'<path d="M 1330 130 L 1330 150 L 1588 150 L 1588 {TOP+HGT-40} L 1582 {TOP+HGT-40}" '
           f'fill="none" stroke="{FG}" stroke-width="2.5" stroke-dasharray="8,5"/>')
c.arrow(1588, TOP + HGT - 40, 1578, TOP + HGT - 40)
c.txt(1578, 176, "local autonomy: bypasses the global layer", 18, italic=True, color=ACCENT,
      anchor="end")

band(810, "INTERNAL LEVEL")
LIS = [("LIS_1", "146,595 blocks · 600 MB"), ("LIS_2", "400,576 blocks · 1,641 MB"),
       ("LIS_3", "304,947 blocks · 1,249 MB"), ("LIS_4", "146,576 blocks · 600 MB")]
for x, (t, s_) in zip(XS, LIS):
    box(x, 866, 340, 72, t, [s_])
    c.arrow(x, TOP + HGT, x, 828)

c.o.append(f'<rect x="24" y="918" width="34" height="24" fill="{BG}" stroke="{FG}" stroke-width="1.5"/>')
c.txt(68, 937, "shared core, designed top-down (same structure at every site)", 19, anchor="start")
c.o.append(f'<rect x="820" y="918" width="34" height="24" fill="{GREYFILL}" stroke="{FG}" stroke-width="1.5"/>')
c.txt(864, 937, "site-only relations, designed bottom-up by that port", 19, anchor="start")

open("fig_architecture.svg", "w").write(c.svg())
cairosvg.svg2png(bytestring=c.svg().encode(), write_to="fig_architecture.png", output_width=2400)


# ============================================================ FIGURE 6 — local ER
AT_RX, AT_RY = 74, 23                 # larger attribute ovals than Figure 2, for print size


class K(Canvas):
    def attribute(self, cx, cy, label, kind=""):
        dash = ' stroke-dasharray="7,5"' if kind == "derived" else ""
        self.o.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{AT_RX}" ry="{AT_RY}" fill="{BG}" '
                      f'stroke="{FG}" stroke-width="2"{dash}/>')
        fs = 18 if len(label) <= 12 else 16
        self.text(cx, cy + 6, label, fs, under=(kind == "key"))
        if kind == "partial":
            w = len(label) * fs * 0.5
            self.line(cx - w / 2, cy + 10, cx + w / 2, cy + 10, 1.4, "4,3")

    def entity(self, cx, cy, name, weak=False):
        x, y = cx - EB_W / 2, cy - EB_H / 2
        self.o.append(f'<rect x="{x}" y="{y}" width="{EB_W}" height="{EB_H}" fill="{BG}" '
                      f'stroke="{FG}" stroke-width="2.5"/>')
        if weak:
            self.o.append(f'<rect x="{x+7}" y="{y+7}" width="{EB_W-14}" height="{EB_H-14}" '
                          f'fill="none" stroke="{FG}" stroke-width="2"/>')
        self.text(cx, cy + 6, name, 21 if len(name) <= 12 else (17 if len(name) <= 17 else 15), bold=True)
        return ("box", cx, cy)

    def core(self, cx, cy, name):
        x, y = cx - EB_W / 2, cy - EB_H / 2
        self.o.append(f'<rect x="{x}" y="{y}" width="{EB_W}" height="{EB_H}" fill="{GREYFILL}" '
                      f'stroke="{FG}" stroke-width="2.5"/>')
        self.text(cx, cy + 6, name, 21, bold=True)
        return ("box", cx, cy)

    def panel(self, ox, oy, w, h, title, sub):
        self.o.append(f'<rect x="{ox+10}" y="{oy+10}" width="{w-20}" height="{h-20}" fill="none" '
                      f'stroke="#8a8a8a" stroke-width="2" stroke-dasharray="10,6"/>')
        self.text(ox + 40, oy + 58, title, 30, anchor="start", bold=True)
        self.text(ox + 40, oy + 92, sub, 19, anchor="start", italic=True)


PW, PH = 1300, 1000
kA, kB = K(PW, 2 * PH + 80), K(PW, 2 * PH + 80)

# ---------------- S1 New Mangalore
k = kA
ox, oy = 0, 0
k.panel(ox, oy, PW, PH, "S1  New Mangalore — liquid bulk",
        "tanks are gauged in kilolitres; custody = kl × density")
TANK = k.entity(ox + 370, oy + 520, "TANK_FARM")
PIPE = k.entity(ox + 900, oy + 520, "PIPELINE_TRANSFER")
VOY1 = k.core(ox + 900, oy + 900, "VOYAGE")
d1 = k.diamond(ox + 640, oy + 520, "THROUGH")
d2 = k.diamond(ox + 900, oy + 725, "FOR")
k.connect(TANK, d1, "1"); k.connect(PIPE, d1, "N", total=True)
k.connect(VOY1, d2, "1"); k.connect(PIPE, d2, "N", total=True)
k.attrs(TANK, [("tank_id", "key"), ("hs_code", ""), ("capacity_kl", ""), ("current_kl", ""),
               ("current_density", ""), ("last_gauged_ts", "")], 95, 265, 215, 295)
k.attrs(PIPE, [("transfer_id", "key"), ("direction", ""), ("start_ts", ""), ("end_ts", ""),
               ("volume_kl", ""), ("density_obs", "")], 8, 168, 205, 290)

# ---------------- S2 JNPT
ox, oy = 0, PH
k.panel(ox, oy, PW, PH, "S2  JNPT — rail and SEZ",
        "a container on an open rake is still in custody; a bonded transfer is not")
CON2 = k.core(ox + 230, oy + 330, "CONTAINER")
RAKE = k.entity(ox + 960, oy + 330, "RAIL_RAKE")
LOAD = k.diamond(ox + 590, oy + 330, "LOADED_ON")
k.connect(CON2, LOAD, "M"); k.connect(RAKE, LOAD, "N")
k.attrs(LOAD, [("wagon_no", ""), ("gross_wt", ""), ("loaded_ts", "")], 145, 35, 135, 135)
k.attrs(RAKE, [("rake_id", "key"), ("train_no", ""), ("dest_icd", ""), ("wagon_count", ""),
               ("departure_ts", ""), ("status", "")], 108, -60, 180, 232)
BOND = k.entity(ox + 590, oy + 580, "BOND_TRANSFER")
CNS2 = k.core(ox + 230, oy + 840, "CONSIGNEE")
SEZ = k.entity(ox + 960, oy + 840, "SEZ_UNIT")
OF = k.diamond(ox + 400, oy + 460, "OF")
INTO = k.diamond(ox + 775, oy + 710, "INTO")
OPS = k.diamond(ox + 590, oy + 840, "OPERATES")
k.connect(CON2, OF, "1"); k.connect(BOND, OF, "N", total=True)
k.connect(SEZ, INTO, "1"); k.connect(BOND, INTO, "N", total=True)
k.connect(CNS2, OPS, "1"); k.connect(SEZ, OPS, "1", total=True)
k.attrs(BOND, [("transfer_id", "key"), ("transfer_ts", ""), ("duty_forgone", "")],
        180, 280, 175, 185)
k.attrs(SEZ, [("unit_id", "key"), ("sez_name", ""), ("bond_no", ""), ("licence_expiry", "")],
        75, -35, 170, 210)

# ---------------- S3 Chennai
k = kB
ox, oy = 0, 0
k.panel(ox, oy, PW, PH, "S3  Chennai — RoRo vehicles",
        "cars are counted by VIN and weighed in kg; custody ends when the voyage sails")
VOY3 = k.core(ox + 230, oy + 300, "VOYAGE")
CNS3 = k.core(ox + 230, oy + 780, "CONSIGNEE")
RORO = k.entity(ox + 720, oy + 540, "RORO_VEHICLE")
INSP = k.entity(ox + 1030, oy + 780, "VEHICLE_INSPECTION", weak=True)
CB = k.diamond(ox + 470, oy + 420, "CARRIED_BY")
EB = k.diamond(ox + 470, oy + 660, "EXPORTED_BY")
IN = k.diamond(ox + 880, oy + 660, "INSPECTED", ident=True)
k.connect(VOY3, CB, "1"); k.connect(RORO, CB, "N", total=True)
k.connect(CNS3, EB, "1"); k.connect(RORO, EB, "N", total=True)
k.connect(RORO, IN, "1"); k.connect(INSP, IN, "N", total=True)
k.attrs(RORO, [("vin", "key"), ("make", ""), ("model", ""), ("weight_kg", ""), ("deck_no", "")],
        5, 125, 190, 260)
k.attrs(INSP, [("inspected_ts", "partial"), ("damage_code", ""), ("surveyor_id", ""),
               ("cleared", "")], 70, -60, 150, 185)

# ---------------- S4 Kolkata / Haldia
ox, oy = 0, PH
k.panel(ox, oy, PW, PH, "S4  Kolkata / Haldia — riverine port",
        "large ships anchor offshore; boxes on a barge mid-river are still in custody")
VOY4 = k.core(ox + 230, oy + 360, "VOYAGE")
LIGHT = k.entity(ox + 900, oy + 360, "LIGHTERAGE")
LT = k.diamond(ox + 565, oy + 360, "LIGHTENS")
k.connect(VOY4, LT, "1"); k.connect(LIGHT, LT, "N", total=True)
k.attrs(LIGHT, [("op_id", "key"), ("barge_id", ""), ("cont_count", ""), ("cargo_tonnes", ""),
                ("start_ts", ""), ("end_ts", "")], 110, -70, 170, 220)
TIDE = k.entity(ox + 430, oy + 750, "TIDAL_WINDOW")
k.attrs(TIDE, [("window_date", "key"), ("window_no", "key"), ("open_ts", ""), ("close_ts", ""),
               ("max_draft_m", "")], 160, -20, 175, 225)
k.text(ox + 960, oy + 860, "Reference data published by the port; it constrains",
       18, italic=True)
k.text(ox + 960, oy + 886, "when VOYAGE may berth, but no stored reference links them.",
       18, italic=True)

# legend + output
for kk, name in [(kA, "fig_local_er_a"), (kB, "fig_local_er_b")]:
    ly = 2 * PH + 40
    kk.o.append(f'<rect x="40" y="{ly-22}" width="150" height="42" fill="{GREYFILL}" stroke="{FG}" '
                f'stroke-width="2.5"/>')
    kk.text(115, ly + 7, "CORE", 20, bold=True)
    kk.text(205, ly + 7, "shared by every site (Figure 2)", 21, anchor="start")
    kk.o.append(f'<rect x="690" y="{ly-22}" width="150" height="42" fill="{BG}" stroke="{FG}" '
                f'stroke-width="2.5"/>')
    kk.text(765, ly + 7, "LOCAL", 20, bold=True)
    kk.text(855, ly + 7, "exists only at that site", 21, anchor="start")
    open(name + ".svg", "w").write(kk.svg())
    cairosvg.svg2png(bytestring=kk.svg().encode(), write_to=name + ".png", output_width=1800)
print("wrote fig_architecture and fig_local_er_a / _b")
