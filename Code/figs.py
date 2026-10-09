#!/usr/bin/env python3
"""Figure 1 (data flow) and Figure 4 (mixed fragmentation tree)."""
FG, BG, MUTED, ACCENT = "#1a1a1a", "#ffffff", "#5a5a5a", "#1F3864"


class C:
    def __init__(s, w, h):
        s.w, s.h = w, h
        s.o = [f'<rect width="{w}" height="{h}" fill="{BG}"/>',
               '<defs><marker id="a" markerWidth="11" markerHeight="8" refX="10" refY="4" '
               f'orient="auto"><path d="M0,0 L11,4 L0,8 z" fill="{FG}"/></marker></defs>']

    def svg(s):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{s.w}" height="{s.h}" '
                f'viewBox="0 0 {s.w} {s.h}">' + "".join(s.o) + "</svg>")

    def box(s, cx, cy, w, h, title, sub=None, dashed=False, fill=BG):
        d = ' stroke-dasharray="8,5"' if dashed else ''
        s.o.append(f'<rect x="{cx-w/2}" y="{cy-h/2}" width="{w}" height="{h}" rx="6" '
                   f'fill="{fill}" stroke="{FG}" stroke-width="2.5"{d}/>')
        if sub:
            s.txt(cx, cy - 6, title, 21, bold=True)
            for i, ln in enumerate(sub if isinstance(sub, list) else [sub]):
                s.txt(cx, cy + 18 + i * 22, ln, 17, color=MUTED)
        else:
            s.txt(cx, cy + 7, title, 21, bold=True)
        return (cx, cy, w, h)

    def txt(s, x, y, t, size=18, bold=False, italic=False, color=FG, anchor="middle", mono=False):
        b = ' font-weight="bold"' if bold else ''
        i = ' font-style="italic"' if italic else ''
        f = 'Consolas,monospace' if mono else 'Helvetica,Arial'
        s.o.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{f}" '
                   f'font-size="{size}" fill="{color}"{b}{i}>'
                   f'{t.replace("&","&amp;").replace("<","&lt;")}</text>')

    def arrow(s, x1, y1, x2, y2, label=None, lx=0, ly=0):
        s.o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{FG}" '
                   f'stroke-width="2.5" marker-end="url(#a)"/>')
        if label:
            s.txt((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly, label, 17, italic=True, color=ACCENT)

    def elbow(s, x1, y1, x2, y2, label=None, my=None):
        my = my if my is not None else (y1 + y2) / 2
        s.o.append(f'<path d="M {x1} {y1} L {x1} {my} L {x2} {my} L {x2} {y2}" fill="none" '
                   f'stroke="{FG}" stroke-width="2.5" marker-end="url(#a)"/>')
        if label:
            s.txt((x1 + x2) / 2, my - 12, label, 17, italic=True, color=ACCENT)


# ============================================================ FIGURE 1 — data flow
c = C(1460, 1140)
BW, BH = 380, 86
b1 = c.box(730,  80, BW, BH, "Vessel arrives", "VOYAGE opened — eta, ata, berth")
b2 = c.box(730, 240, BW, BH, "Containers discharged", "CONTAINER created, BILL_OF_LADING linked")
b3 = c.box(730, 400, BW, BH, "Yard slot assigned", "YARD_SLOT occupied (port, block, bay, row, tier)")
c.arrow(730, 123, 730, 194)
c.arrow(730, 283, 730, 354)

c.elbow(730, 443, 390, 545, "import")
c.elbow(730, 443, 1090, 545, "transshipment")

L = [("Customs declaration filed", "CUSTOMS_DECL — duty assessed"),
     ("Cleared", "customs_status = CLEARED"),
     ("Gate move OUT", "GATE_MOVE — truck or rail"),
     ("Slot released", "dwell computed, demurrage if past free period")]
for i, (t, s_) in enumerate(L):
    y = 590 + i * 142
    c.box(390, y, 360, 80, t, s_)
    if i:
        c.arrow(390, y - 122, 390, y - 45)

R = [("Reloaded onto feeder", "outbound voyage confirmed"),
     ("cur_port_id changes", "tuple migrates to the sibling port"),
     ("Cross-site access", "destination port reads origin-port data")]
for i, (t, s_) in enumerate(R):
    y = 590 + i * 142
    c.box(1090, y, 360, 80, t, s_, dashed=(i == 2))
    if i:
        c.arrow(1090, y - 122, 1090, y - 45)
c.txt(1090, 1000, "the reason this is a distributed database", 17, italic=True, color=ACCENT)
c.txt(1090, 1024, "and not four separate ones", 17, italic=True, color=ACCENT)
open("/home/claude/fig_dataflow.svg", "w").write(c.svg())

# ============================================================ FIGURE 4 — fragmentation tree
f = C(1840, 980)
f.box(920, 70, 420, 84, "CONTAINER", "500,000 tuples x 76 B")
f.txt(920, 152, "VERTICAL FRAGMENTATION", 18, bold=True, color=ACCENT)
f.elbow(920, 113, 480, 216, None, my=178)
f.elbow(920, 113, 1360, 216, None, my=178)

f.box(480, 258, 400, 84, "CONTAINER_C", "54 B — cargo, yard, commercial")
f.box(1360, 258, 400, 84, "CONTAINER_G", "33 B — seal_no, customs_status")
f.txt(480, 336, "HORIZONTAL on cur_port_id", 17, italic=True, color=ACCENT)
f.txt(1360, 336, "DERIVED:  CONTAINER_G  |x  CONTAINER_C_k", 17, italic=True, color=ACCENT)

sites = [("S1", "75,000"), ("S2", "200,000"), ("S3", "150,000"), ("S4", "75,000")]
for i, (s_, n) in enumerate(sites):
    x = 165 + i * 210
    f.box(x, 450, 186, 76, f"F1_{i+1}  {s_}", n)
    f.elbow(480, 300, x, 412, None, my=372)
for i, (s_, n) in enumerate(sites):
    x = 1045 + i * 210
    f.box(x, 450, 186, 76, f"F2_{i+1}  {s_}", n)
    f.elbow(1360, 300, x, 412, None, my=372)

f.txt(920, 590, "DERIVED CHILDREN  —  all fragmented by semijoin with CONTAINER_C_k",
      19, bold=True, color=ACCENT)
kids = [("F8", "CUSTOMS_DECL", "450,000"), ("F10", "CONTAINER_REEFER", "40,000"),
        ("F11", "CONTAINER_TANK", "15,000"), ("F12", "CONTAINER_OPEN_TOP", "10,000")]
for i, (fid, nm, n) in enumerate(kids):
    x = 290 + i * 420
    f.box(x, 690, 380, 80, f"{fid}   {nm}", f"{n} tuples, x4 sites")
    f.elbow(920, 612, x, 652, None, my=640)

f.o.append(f'<rect x="120" y="800" width="1600" height="110" rx="6" fill="#F7F7F9" '
           f'stroke="#D0D0D8" stroke-width="1.5"/>')
f.txt(150, 838, "Reconstruction:", 18, bold=True, anchor="start")
f.txt(150, 866, "CONTAINER_C = U(k) CONTAINER_C_k        CONTAINER_G = U(k) CONTAINER_G_k",
      17, anchor="start", mono=True)
f.txt(150, 892, "CONTAINER   = CONTAINER_C |><|(cont_id) CONTAINER_G", 17, anchor="start", mono=True)
f.txt(700, 892, "lossless — cont_id is a candidate key carried in both fragments",
      17, anchor="start", italic=True, color=MUTED)
open("/home/claude/fig_fragtree.svg", "w").write(f.svg())
print("ok")
