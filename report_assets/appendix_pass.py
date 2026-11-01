"""Fourth pass: appendices A-D with a figure gallery, within the 10-page appendix limit.

python report_assets/appendix_pass.py <in.docx> <out.docx>
- removes the process-only appendices (data-sheet field lists, video map, QA audit)
- adds Appendix B, a gallery of the digital prototype, EPANET and the as-built rig
- old Appendix E becomes C and old F becomes D; table numbers and main-text pointers follow
"""
import re
import sys
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from PIL import Image

HERE = Path(__file__).resolve().parent
DP = HERE.parent
d = docx.Document(sys.argv[1])
txt = lambda el: "".join(t.text or "" for t in el.iter(qn("w:t")))


def para(start):
    for p in d.paragraphs:
        if p.text.strip().startswith(start):
            return p
    raise KeyError(start)


def set_text(p, text):
    p.runs[0].text = text
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)


# 1. drop old Appendix B, C and D (process artefacts)
start, stop = para("Appendix B — Separated data sheets")._p, para("Appendix E — Supporting design")._p
el = start
while el is not stop:
    nxt = el.getnext()
    el.getparent().remove(el)
    el = nxt

# 2. rename E -> C, F -> D
set_text(para("Appendix E — Supporting design"), "Appendix C — Supporting design, method and scale-up detail")
set_text(para("Appendix F — Data tables"), "Appendix D — Data tables")
TMAP = {8: 4, 9: 5, 10: 6, 11: 7, 12: 8}
everything = list(d.paragraphs) + [cp for t in d.tables for r in t.rows for c in r.cells for cp in c.paragraphs]
for p in everything:
    for r in p.runs:
        new = re.sub(r"\bE\.(\d{1,2})\b", r"C.\1", r.text)
        new = re.sub(r"\bTable A(\d+)\b", lambda m: f"Table A{TMAP.get(int(m.group(1)), int(m.group(1)))}", new)
        new = new.replace("Tables A8", "Tables A4")
        if new != r.text:
            r.text = new

# 3. Appendix B gallery, before Appendix C
anchor = para("Appendix C — Supporting design")._p
crop = Image.open(DP / "outputs/screenshots/S05_diversion__veriflush_end.png").convert("RGB").crop((0, 0, 1366, 1150))
crop.save(HERE / "_gal_dash.png")
gallery = [
    ("_gal_dash.png", 13.0, "Figure A1. VeriFlush digital twin dashboard, scenario S05 (side branch open): rig schematic, "
                            "verdict with reason, live sensor values and tracer truth that the decision code cannot read. "
                            "Simulated."),
    ("_gal_epanet.png", 16.0, "Figure A2. The same rig modelled in the EPANET 2.2 desktop application (S05): (a) water-"
                              "quality map at 30 s, (b) fresh-water fraction at endpoint TT101. Simulated."),
    (str(DP / "outputs/figures/fig03_verdict_grid.png"), 14.5,
     "Figure A3. Outcome of every method in every scenario, 40 runs each, scored against tracer truth: (a) baseline "
     "transport, (b) laminar straight-tube transport. Simulated."),
    (str(DP / "outputs/figures/fig01_healthy_timeseries.png"), 8.5,
     "Figure A4. Healthy flush (S01) with VeriFlush in control: flow, valve, feed and endpoint temperatures, and the "
     "tracer truth; the valve closes with Verified at 94 s. Simulated."),
    ("_gal_rig.png", 16.0, "Figure A5. The as-built physical prototype and its first shakedown log (1 November 2026)."),
]


def add_before(p):
    anchor.addprevious(p._p)
    return p


h = add_before(d.add_paragraph("Appendix B — Digital prototype and rig gallery", style="Heading 2"))
h.paragraph_format.keep_with_next = True
intro_p = add_before(d.add_paragraph("The figures below come from the VeriFlush digital prototype (public repository "
                           "github.com/MoAqil/veriflush), the EPANET 2.2 desktop application and the team's as-built "
                           "rig.", style="Normal"))
intro_p.paragraph_format.keep_with_next = True
for img, width, caption in gallery:
    path = Path(img) if Path(img).is_absolute() else HERE / img
    pic = d.add_paragraph()
    pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic.paragraph_format.keep_with_next = True
    pic.paragraph_format.space_before = Pt(6)
    pic.paragraph_format.space_after = Pt(2)
    pic.add_run().add_picture(str(path), width=Cm(width))
    add_before(pic)
    add_before(d.add_paragraph(caption, style="Figure Caption"))

d.save(sys.argv[2])
print("saved", sys.argv[2])
