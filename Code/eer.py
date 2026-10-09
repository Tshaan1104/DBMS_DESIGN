#!/usr/bin/env python3
"""Chen-notation EER diagrams for the Container Terminal Network (Assignment 1, Phase 1)."""
import math

EB_W, EB_H = 190, 56
AT_RX, AT_RY = 62, 20
RD_W, RD_H = 172, 80
FG, BG = "#1a1a1a", "#ffffff"


class Canvas:
    def __init__(self, w, h):
        self.w, self.h, self.o = w, h, [f'<rect width="{w}" height="{h}" fill="{BG}"/>']

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}">' + "".join(self.o) + "</svg>")

    # ---------- primitives
    def line(self, x1, y1, x2, y2, w=2, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                      f'stroke="{FG}" stroke-width="{w}"{d}/>')

    def text(self, x, y, s, size=13, anchor="middle", bold=False, italic=False, under=False):
        w = ' font-weight="bold"' if bold else ""
        i = ' font-style="italic"' if italic else ""
        u = ""                     # cairosvg ignores text-decoration: draw the underline
        if under:
            wd = len(s) * size * 0.52
            self.o.append(f'<line x1="{x-wd/2:.1f}" y1="{y+3:.1f}" x2="{x+wd/2:.1f}" '
                          f'y2="{y+3:.1f}" stroke="{FG}" stroke-width="1.4"/>')
        self.o.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
                      f'font-family="Helvetica,Arial" font-size="{size}" fill="{FG}"{w}{i}{u}>'
                      f'{s.replace("&","&amp;").replace("<","&lt;")}</text>')

    def entity(self, cx, cy, name, weak=False):
        x, y = cx - EB_W / 2, cy - EB_H / 2
        self.o.append(f'<rect x="{x}" y="{y}" width="{EB_W}" height="{EB_H}" fill="{BG}" '
                      f'stroke="{FG}" stroke-width="2.5"/>')
        if weak:
            self.o.append(f'<rect x="{x+7}" y="{y+7}" width="{EB_W-14}" height="{EB_H-14}" '
                          f'fill="none" stroke="{FG}" stroke-width="2"/>')
        self.text(cx, cy + 6, name, 21, bold=True)
        return ("box", cx, cy)

    def diamond(self, cx, cy, label, ident=False):
        p = lambda w, h: f"{cx},{cy-h/2} {cx+w/2},{cy} {cx},{cy+h/2} {cx-w/2},{cy}"
        self.o.append(f'<polygon points="{p(RD_W,RD_H)}" fill="{BG}" stroke="{FG}" stroke-width="2.5"/>')
        if ident:
            self.o.append(f'<polygon points="{p(RD_W-18,RD_H-18)}" fill="none" stroke="{FG}" stroke-width="2"/>')
        fs = 17 if len(label) <= 12 else 14
        self.text(cx, cy + 5, label, fs)
        return ("dia", cx, cy)

    def attribute(self, cx, cy, label, kind=""):
        dash = ' stroke-dasharray="7,5"' if kind == "derived" else ""
        self.o.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{AT_RX}" ry="{AT_RY}" fill="{BG}" '
                      f'stroke="{FG}" stroke-width="2"{dash}/>')
        if kind == "mv":
            self.o.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{AT_RX-6}" ry="{AT_RY-5}" '
                          f'fill="none" stroke="{FG}" stroke-width="1.6"/>')
        fs = 16 if len(label) <= 12 else 13
        self.text(cx, cy + 4, label, fs, under=(kind == "key"))
        if kind == "partial":
            w = len(label) * fs * 0.48
            self.line(cx - w / 2, cy + 7, cx + w / 2, cy + 7, 1.3, "3,3")

    # ---------- geometry
    @staticmethod
    def _clip(node, tx, ty):
        kind, cx, cy = node
        dx, dy = tx - cx, ty - cy
        if dx == 0 and dy == 0:
            return cx, cy
        if kind == "box":
            s = min(EB_W / 2 / abs(dx) if dx else 1e9, EB_H / 2 / abs(dy) if dy else 1e9)
        else:
            s = 1.0 / (abs(dx) / (RD_W / 2) + abs(dy) / (RD_H / 2))
        return cx + dx * s, cy + dy * s

    def connect(self, ent, dia, card, total=False):
        p1 = self._clip(ent, dia[1], dia[2])
        p2 = self._clip(dia, ent[1], ent[2])
        self.line(*p1, *p2)
        if total:
            ux, uy = p2[0] - p1[0], p2[1] - p1[1]
            L = math.hypot(ux, uy) or 1
            nx, ny = -uy / L * 5, ux / L * 5
            self.line(p1[0] + nx, p1[1] + ny, p2[0] + nx, p2[1] + ny, 1.7)
        # cardinality label, placed just outside the entity end of the edge
        t = 0.26
        mx, my = p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t
        a = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        self.text(mx - math.sin(a) * 19, my + math.cos(a) * 19 + 5, card, 21, bold=True)

    def attrs(self, ent, items, a0, a1, r1, r2):
        _, ex, ey = ent
        n = len(items)
        for i, (label, kind) in enumerate(items):
            t = a0 if n == 1 else a0 + (a1 - a0) * i / (n - 1)
            r = r1 if i % 2 == 0 else r2
            a = math.radians(t)
            ax, ay = ex + r * math.cos(a), ey - r * math.sin(a)
            p = self._clip(ent, ax, ay)
            vx, vy = ax - p[0], ay - p[1]
            L = math.hypot(vx, vy) or 1
            ang = math.atan2(vy, vx)
            er = (AT_RX * AT_RY) / math.hypot(AT_RY * math.cos(ang), AT_RX * math.sin(ang))
            self.line(p[0], p[1], ax - vx / L * er, ay - vy / L * er, 1.8)
            self.attribute(ax, ay, label, kind)


# ===================================================== FIGURE 1 — main EER
c = Canvas(3850, 3330)

CONT  = c.entity( 670, 1550, "CONTAINER")
CONS  = c.entity(1820,  400, "CONSIGNEE")
BOL   = c.entity(2720,  300, "BILL_OF_LADING")
VOY   = c.entity(2270,  900, "VOYAGE")
VESL  = c.entity(3400,  400, "VESSEL")
SLINE = c.entity(3450, 1000, "SHIPPING_LINE")
YSLOT = c.entity(2070, 1500, "YARD_SLOT", weak=True)
PORT  = c.entity(2800, 2350, "PORT")
GATE  = c.entity(1900, 2900, "GATE_MOVE")
CUST  = c.entity(1320, 2650, "CUSTOMS_DECL")
TARF  = c.entity(2800, 3000, "TARIFF", weak=True)

c.attrs(CONT, [("cont_id", "key"), ("size_ft", ""), ("cont_type", ""), ("tare_wt", ""),
               ("gross_wt", ""), ("seal_no", ""), ("hazmat_class", ""), ("invoice_value", ""),
               ("customs_status", ""), ("dwell_time", "derived")], 115, 245, 370, 480)
c.attrs(CONS, [("consignee_id", "key"), ("name", ""), ("address", ""), ("city", ""),
               ("country", ""), ("gstin", ""), ("phone", "mv")], 152, 28, 195, 252)
c.attrs(BOL, [("bl_no", "key"), ("cont_count", ""), ("freight_amt", ""), ("issue_date", "")],
        150, 30, 170, 212)
c.attrs(VOY, [("voyage_id", "key"), ("eta", ""), ("ata", ""), ("atd", ""), ("berth_no", ""),
              ("status", "")], 72, 172, 196, 252)
c.attrs(VESL, [("vessel_id", "key"), ("name", ""), ("imo_no", ""), ("flag", ""),
               ("capacity_teu", "")], -55, 65, 172, 215)
c.attrs(SLINE, [("line_id", "key"), ("name", ""), ("country", ""), ("agent_name", "")],
        -78, 14, 172, 215)
c.attrs(YSLOT, [("block", "partial"), ("bay", "partial"), ("row", "partial"),
                ("tier", "partial"), ("occupied_since", "")], 142, 38, 175, 220)
c.attrs(PORT, [("port_id", "key"), ("port_name", ""), ("city", ""), ("country", ""),
               ("timezone", "")], -58, 58, 200, 268)
c.attrs(GATE, [("move_id", "key"), ("ts", ""), ("direction", ""), ("truck_no", ""),
               ("gate_no", ""), ("operator_id", "")], 196, 344, 180, 226)
c.attrs(CUST, [("decl_id", "key"), ("hs_code", ""), ("duty_amt", ""), ("filed_on", ""),
               ("cleared_on", ""), ("officer_id", "")], 194, 330, 180, 226)
c.attrs(TARF, [("service_code", "partial"), ("rate", ""), ("currency", "")], 208, 332, 180, 224)

pairs = [
    (SLINE, c.diamond(3428,  700, "operates"), "1", VESL, "N", False, False),
    (VESL,  c.diamond(2850,  560, "makes"),    "1", VOY,  "N", False, False),
    (VOY,   c.diamond(1470, 1225, "discharges"), "1", CONT, "N", False, False),
    (CONT,  c.diamond(1245,  975, "consigned to"), "N", CONS, "1", False, False),
    (CONT,  c.diamond(1900, 1200, "carried by"), "N", SLINE, "1", False, False),
    (CONT,  c.diamond(1370, 1525, "occupies"), "1", YSLOT, "1", False, False),
    (YSLOT, c.diamond(2430, 1930, "located in", True), "N", PORT, "1", True, False),
    (CONT,  c.diamond(1370, 2210, "logs"), "1", GATE, "N", False, False),
    (CONT,  c.diamond( 980, 2090, "declared in"), "1", CUST, "1", False, False),
    (CONT,  c.diamond(1760, 1990, "currently at"), "N", PORT, "1", False, False),
    (GATE,  c.diamond(2350, 2720, "recorded at"), "N", PORT, "1", False, False),
    (TARF,  c.diamond(2800, 2680, "applies at", True), "N", PORT, "1", True, False),
    (BOL,   c.diamond(2495,  600, "issued for"), "N", VOY, "1", False, False),
    (BOL,   c.diamond(2270,  350, "billed to"), "N", CONS, "1", False, False),
    (VOY,   c.diamond(3010, 1560, "calls at"), "N", PORT, "1", False, False),
]
for e1, d, c1, e2, c2, tot2, tot1 in pairs:
    c.connect(e1, d, c1, tot1)
    c.connect(e2, d, c2, tot2)

# specialization pointer
sx, sy = 670, 2010
c.line(670, 1578, sx, sy - 36)
c.o.append(f'<circle cx="{sx}" cy="{sy}" r="36" fill="{BG}" stroke="{FG}" stroke-width="2.5"/>')
c.text(sx, sy + 8, "d", 22, bold=True)
c.line(sx, sy + 36, sx, sy + 78)
c.text(sx, sy + 100, "DRY / REEFER / TANK / OPEN_TOP", 14)
c.text(sx, sy + 124, "(detailed in Figure 3)", 13, italic=True)

# legend
lx, ly = 150, 2820
c.o.append(f'<rect x="{lx-40}" y="{ly-40}" width="620" height="440" fill="none" '
           f'stroke="{FG}" stroke-width="1.5"/>')
c.text(lx - 10, ly, "LEGEND", 17, anchor="start", bold=True)
items = [("rect", "Entity"), ("rect2", "Weak entity"), ("dia", "Relationship"),
         ("dia2", "Identifying relationship"), ("ell", "Attribute"), ("ellk", "Key attribute"),
         ("ellm", "Multivalued attribute"), ("elld", "Derived attribute"),
         ("dbl", "Total participation")]
for i, (k, label) in enumerate(items):
    y = ly + 40 + i * 42
    if k.startswith("rect"):
        c.o.append(f'<rect x="{lx}" y="{y-13}" width="76" height="26" fill="{BG}" stroke="{FG}" stroke-width="2"/>')
        if k == "rect2":
            c.o.append(f'<rect x="{lx+5}" y="{y-8}" width="66" height="16" fill="none" stroke="{FG}" stroke-width="1.5"/>')
    elif k.startswith("dia"):
        p = lambda w, h: f"{lx+38},{y-h/2} {lx+38+w/2},{y} {lx+38},{y+h/2} {lx+38-w/2},{y}"
        c.o.append(f'<polygon points="{p(76,28)}" fill="{BG}" stroke="{FG}" stroke-width="2"/>')
        if k == "dia2":
            c.o.append(f'<polygon points="{p(60,18)}" fill="none" stroke="{FG}" stroke-width="1.5"/>')
    elif k == "dbl":
        c.line(lx, y - 3, lx + 76, y - 3, 2)
        c.line(lx, y + 3, lx + 76, y + 3, 2)
    else:
        d = ' stroke-dasharray="6,4"' if k == "elld" else ""
        c.o.append(f'<ellipse cx="{lx+38}" cy="{y}" rx="38" ry="14" fill="{BG}" stroke="{FG}" stroke-width="2"{d}/>')
        if k == "ellm":
            c.o.append(f'<ellipse cx="{lx+38}" cy="{y}" rx="32" ry="9" fill="none" stroke="{FG}" stroke-width="1.5"/>')
        if k == "ellk":
            c.line(lx + 20, y + 5, lx + 56, y + 5, 1.5)
    c.text(lx + 100, y + 6, label, 18, anchor="start")

open("/home/claude/eer_main.svg", "w").write(c.svg())

# ===================================================== FIGURE 2 — specialization
c2 = Canvas(1900, 880)
SUP = c2.entity(950, 200, "CONTAINER")
c2.line(950, 228, 950, 320)
c2.o.append(f'<circle cx="950" cy="356" r="36" fill="{BG}" stroke="{FG}" stroke-width="2.5"/>')
c2.text(950, 364, "d", 22, bold=True)
c2.text(1040, 362, "disjoint, total", 15, anchor="start", italic=True)
c2.line(950, 392, 950, 470)
c2.line(320, 470, 1580, 470)

subs = [(320, "DRY", []), (740, "REEFER", [("set_point_temp", ""), ("plug_id", "")]),
        (1160, "TANK", [("un_number", ""), ("last_cleaned_on", "")]),
        (1580, "OPEN_TOP", [("over_height_cm", "")])]
for x, name, at in subs:
    c2.line(x, 470, x, 560)
    # subset symbol
    c2.o.append(f'<path d="M {x-15} 508 L {x-15} 532 A 15 15 0 0 0 {x+15} 532 L {x+15} 508" '
                f'fill="none" stroke="{FG}" stroke-width="2.4"/>')
    e = c2.entity(x, 610, name)
    if at:
        c2.attrs(e, at, 250, 290, 150, 195) if len(at) > 1 else c2.attrs(e, at, 270, 270, 150, 150)

c2.text(950, 860, "DRY has no additional attributes; the subtypes differ in the "
                   "constraints they impose on slot assignment.", 15, italic=True)
open("/home/claude/eer_spec.svg", "w").write(c2.svg())
print("ok")
