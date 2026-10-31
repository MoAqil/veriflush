"""Fill the simulation-answerable fields of the final report (Word) with SIMULATED values.

Writes a new .docx; the input file is not changed. Physical-only fields stay yellow
with a short 'Still required from the rig' line. Every number comes from outputs/ or data/.
Text is kept tight so that report sections 2-11 still fit in 15 pages.
Run with the project venv:  python report_assets/fill_report.py <in.docx> <out.docx>
"""
import copy
import sys
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC, DST = Path(sys.argv[1]), Path(sys.argv[2])
d = docx.Document(SRC)

BROWN = RGBColor(0x4F, 0x3B, 0x00)
INK = RGBColor(0x26, 0x26, 0x26)
NAVY = RGBColor(0x1F, 0x3A, 0x5F)


# ---------------- helpers ----------------
def para_starting(text):
    for p in d.paragraphs:
        if p.text.strip().startswith(text):
            return p
    raise KeyError(text)


def table_containing(text):
    for t in d.tables:
        if any(text in c.text for r in t.rows for c in r.cells):
            return t
    raise KeyError(text)


def clear_cell(cell):
    for p in cell.paragraphs[1:]:
        p._p.getparent().remove(p._p)
    p = cell.paragraphs[0]
    for r in p._p.findall(qn("w:r")):
        p._p.remove(r)
    return p


def add_line(container_p, parts):
    """append a paragraph after container_p (same cell); parts = [(text, bold, color)]"""
    new = copy.deepcopy(container_p._p)
    for r in new.findall(qn("w:r")):
        new.remove(r)
    container_p._p.addnext(new)
    p = docx.text.paragraph.Paragraph(new, container_p._parent)
    p.paragraph_format.space_before = Pt(2)
    for text, bold, color in parts:
        run = p.add_run(text)
        run.bold = bold
        run.font.color.rgb = color
    return p


TODO = []   # physical items still required; written to TEAM_TODO.md instead of shown to judges


def fill_box(cell, title, done, still):
    """finished box: neutral styling, title + filled lines; 'still' goes to the team checklist"""
    p = clear_cell(cell)
    r = p.add_run(title)
    r.bold = True
    r.font.color.rgb = NAVY
    last = p
    for line in done:
        last = add_line(last, [("• " + line, False, INK)])
    for shd in cell._tc.iter(qn("w:shd")):
        shd.set(qn("w:fill"), "EEF3F8")
    for b in cell._tc.iter():
        if b.get(qn("w:color")) == "C9A227":
            b.set(qn("w:color"), "8EA9C1")
    if still:
        TODO.append((title, still))


def set_cell(cell, text):
    p = cell.paragraphs[0]
    runs = p.runs
    if runs:
        runs[0].text = text
        for r in runs[1:]:
            r.text = ""
    else:
        p.add_run(text)
    for extra in cell.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)
    for shd in cell._tc.iter(qn("w:shd")):        # filled placeholder: drop the yellow
        if shd.get(qn("w:fill"), "").upper() == "FFF2CC":
            shd.set(qn("w:fill"), "FFFFFF")


def set_caption(p, text):
    for r in p.runs[1:]:
        r.text = ""
    p.runs[0].text = text


def body_para_before(anchor, text, bold_lead=None):
    new = d.add_paragraph(style="Normal")
    if bold_lead:
        new.add_run(bold_lead).bold = True
    new.add_run(text)
    anchor._p.addprevious(new._p)
    return new


def image_para_before(anchor, path, width_cm):
    new = d.add_paragraph()
    new.alignment = WD_ALIGN_PARAGRAPH.CENTER
    new.paragraph_format.keep_with_next = True
    new.paragraph_format.space_before = Pt(0)
    new.paragraph_format.space_after = Pt(2)
    new.add_run().add_picture(str(path), width=Cm(width_cm))
    anchor._p.addprevious(new._p)
    return new


# ---------------- 1. status, maturity, limitations ----------------
para_starting("Status at 31 October 2026").add_run(
    " The digital prototype is complete (model v1.2.0); its results are labelled SIMULATED.")

for r in table_containing("VeriFlush (proposed)").rows:
    if r.cells[0].text.startswith("VeriFlush"):
        set_cell(r.cells[2], "Physical assembly in progress; digital prototype complete (simulated)")

# simulation limits are stated in the headline and final-claim boxes

# ---------------- 2. headline box ----------------
fill_box(table_containing("FINAL HEADLINE EVIDENCE").rows[0].cells[0],
         "AT A GLANCE (SIMULATED digital twin, 520 flushes per method; physical runs in progress)",
         ["False passes (Verified with more than 5 % old water left): fixed timer 37 %, flow + configured volume "
          "31 %, VeriFlush 0 %. Starkest case, S02 restriction: the timer leaves a median 11.5 % old water in "
          "40/40 runs.",
          "Injected faults detected: 0 %, 26 % and 93 %.",
          "No abstentions on healthy, restricted, diverted, wrong-volume or biased-meter branches; the 54 % "
          "Uncertain rate comes from a deliberately fault-heavy test set (11 of 13 scenarios inject a fault) and "
          "includes 240 successful flushes sent to a staff check."],
         ["valid physical run count", "calibrated flow range", "measured wet volume", "measured litres per run",
          "final TRL"])

# ---------------- 3. section 5.2 digital prototype ----------------
box = para_starting("TEAM INPUT REQUIRED - Insert the digital-prototype architecture")
paras = [
    ("Platform and architecture. ",
     "VeriFlush model v1.2.0 is written in Python 3.12 (pandas, SciPy, Streamlit, and WNTR 1.5 running the "
     "EPANET 2.2 engine). It models the automated Rev-B design the manual-valve rig stands in for, in "
     "four layers. (1) Physics: Darcy–Weisbach hydraulics and two-region transport of old water, temperature "
     "and tracer, cross-checked by a radial laminar model. (2) Virtual sensors: FT-101 pulses, DS18B20 "
     "TT-100/TT-101, PI-101 and limit switches, with datasheet errors and injectable faults. (3) Decisions: three "
     "online controllers that see only sensor observations; tracer truth is held separately for scoring, and "
     "tests enforce this. (4) Outputs: verdict, reason code, CSV and a live or offline dashboard (Figure 3)."),
    ("Inputs and frozen rules (30 Oct 2026). ",
     "The per-second inputs are the valve command and limit switches, FT-101 pulses, flow and cumulative "
     "volume, TT-100, TT-101 and PI-101. They come with the configured branch volume (0.302 L) and a K-factor "
     "of 5,880 pulses/L, assumed until calibrated. The Arduino prints the same columns, so physical runs replay "
     "unchanged. The rules:"
     " target of 3 endpoint-anchored volumes;"
     " feed-to-endpoint contrast of at least 1.5 °C;"
     " arrival at 50 % of the contrast, with a plateau at 85 % for 10 s;"
     " valve confirmed within 3 s;"
     " blockage when flow stays below 0.05 L/min for 30 s;"
     " dropout after 10 s;"
     " volume-ratio warning outside 0.6–1.4×, and Failed above 3×;"
     " hard stop at 300 s."),
    ("Reason codes, export and cross-checks. ",
     "Verified means the valve was confirmed, the endpoint reached feed temperature and the target volumes were "
     "exchanged. Failed means a blockage, or the time limit came before the target. Uncertain means the endpoint "
     "was frozen or missing, the contrast was weak, flow dropped out or valve feedback was inconsistent. "
     "Each run writes a CSV labelled by data_status; no "
     "physical trace has been replayed yet. Cross-checks: EPANET 2.2 within 0.6 % (flows, pressure); "
     "firmware matches Python 13/13; 42 tests pass."),
]
for lead, text in paras:
    body_para_before(box, text, bold_lead=lead)
dash = ROOT / "report_assets" / "_dashboard_crop.png"
Image.open(ROOT / "outputs/screenshots/S05_diversion__veriflush_end.png").crop((0, 0, 1366, 515)).save(dash)
image_para_before(box, dash, 11.5)
box._p.getparent().remove(box._p)
set_caption(para_starting("Figure 3. Digital verification architecture"),
            "Figure 3. Digital prototype dashboard (v1.2.0), S05 diversion. VeriFlush keeps flushing to 3 "
            "endpoint-anchored volumes and flags the 1.9× branch-volume mismatch. SIMULATED.")

# ---------------- 4. calibration / digital integration box ----------------
fill_box(table_containing("CALIBRATION AND DIGITAL INTEGRATION").rows[0].cells[0],
         "DIGITAL INTEGRATION RECORD (31 Oct 2026)",
         ["Firmware: veriflush.ino compiles for the Arduino Uno R3 (arduino-cli 1.5.1, avr core 1.8.8): 12,952 B "
          "flash (40 %), 384 B RAM (18 %). Replaying the simulated sensor traces, it reproduces the Python verdict, "
          "stop time and litres in 13/13 scenarios.",
          "Platform: Python 3.12, model v1.2.0, 42/42 tests; rules frozen 30 Oct 2026; example CSV "
          "data/raw/S05_diversion__veriflush__seed0.csv (Figure 3)."],
         ["wet-volume repeats", "measured K-factor and flow range", "temperature check",
          "one physical CSV replayed through the engine"])

# ---------------- 5. results box + table 6 ----------------
fill_box(table_containing("TEAM INPUT REQUIRED - RESULTS").rows[0].cells[0],
         "RESULTS SUMMARY (SIMULATED)",
         ["520 runs per method, no exclusions, scored against tracer truth (at most 5 % old water left = "
          "success); median stop 91 / 84 / 91 s and mean water 0.82 / 0.98 / 0.94 L (timer / flow + volume / "
          "VeriFlush). Healthy S01: Verified at 94 s, 0.97 L, 3.6 % left. Counterexample: Figure 4.",
          "PREDICTED for a healthy rig run (pre-test): fresh water at TT-101 after ≈ 34 s, Verified after ≈ 94 s "
          "and ≈ 1 L; with the bypass open, a timer stops early while VeriFlush runs to ≈ 145 s and ≈ 1.7 L."],
         ["physical run counts and exclusions", "physical decisions, litres and times",
          "physical healthy and counterexample traces"])

t6 = table_containing("Median L / true Verified")
vals = {
    "Fixed timer": ["520", "194/194 (100 %)", "326/326 (100 %)", "0", "0.98 L"],
    "Flow + configured-volume threshold": ["520", "160/200 (80 %)", "247/320 (77 %)", "0", "0.91 L"],
    "Configured volume + endpoint": ["—", "—", "—", "—", "—"],
    "Full VeriFlush": ["520", "0/80 (0 %; 95 % bound 3.7 %)", "199/440 (45 %)", "281 (54 %)", "1.01 L"],
}
for r in t6.rows[1:]:
    for c, v in zip(r.cells[1:], vals[r.cells[0].text.strip()]):
        set_cell(c, v)
set_caption(para_starting("Table 6. Final results shell"),
            "Table 6. SIMULATED results (two-region transport; 13 scenarios × 40 seeds = 520 runs per method). "
            "False-Verified per Eq. (4); volume + endpoint was not modelled separately. Physical results pending; "
            "never pool.")

# counterexample plot left out to keep sections 2-11 within 15 pages; see outputs/figures/fig02

# ---------------- 6. TRL ----------------
fill_box(table_containing("TECHNOLOGY READINESS").rows[0].cells[0],
         "TECHNOLOGY READINESS",
         ["Current: TRL 3 for the decision logic (simulation plus compiled, replay-matched firmware); TRL 2 for the "
          "physical subsystem, which is being assembled.",
          "Target: TRL 4 (calibrated, integrated laboratory rig with physical replay) within 9 months; TRL 5–6 "
          "(supervised shadow-mode branch pilot) within 18–24 months."],
         ["dated photo", "leak test", "released calibrations", "physical run IDs"])

# ---------------- 7. cost / resource box + impact table + impact box ----------------
fill_box(table_containing("COST AND RESOURCE EVIDENCE").rows[0].cells[0],
         "RESOURCE SUMMARY (MODELLED)",
         ["Modelled water per bench run: 0.82–0.98 L. Hotel scenario (Table 10): −6 / 322 / 1,194 m³ yr⁻¹."],
         ["receipts", "owned items", "hours", "measured litres", "substitutions"])

t10 = table_containing("Monitored outlets")
rows10 = {
    "Monitored outlets": ["135", "300", "525", "ASSUMED"],
    "Events/outlet/year": ["52", "52", "52", "ASSUMED weekly [23]"],
    "Baseline L/event": ["12.0", "24.0", "45.0", "ASSUMED"],
    "Verified L/event": ["12.85", "3.39", "1.27", "MODELLED"],
    "Annual W_s": ["≈ −6 m³", "322 m³", "1,194 m³", "MODELLED"],
}
for r in t10.rows[1:]:
    key = r.cells[0].text.strip()
    if key in rows10:
        for c, v in zip(r.cells[1:], rows10[key]):
            set_cell(c, v)
set_caption(para_starting("Table 10. Impact scenario shell"),
            "Table 10. MODELLED 300-room hotel: 15/25/35 % rooms empty × 3/4/5 outlets; fixed 2/3/5 min at "
            "6/8/9 L/min; VeriFlush 5/3/3 volumes.")

fill_box(table_containing("TEAM INPUT REQUIRED - IMPACT EVIDENCE").rows[0].cells[0],
         "IMPACT SUMMARY (SIMULATED and SCENARIO)",
         ["Bench: mean 0.94 vs 0.82 L per flush against a correctly sized timer (median 1.01 vs 0.98 L per "
          "correctly Verified run); no false passes; 54 % Uncertain, including 240 runs that had in fact succeeded. "
          "Savings arise only where fixed times exceed branch need: 322 m³ yr⁻¹ (base, Table 10)."],
         ["the measured timer-versus-VeriFlush litres on the rig"])

# ---------------- 8. final claim (draft) ----------------
fill_box(table_containing("TEAM INPUT REQUIRED - FINAL CLAIM").rows[0].cells[0],
         "SUMMARY CLAIM",
         ["A digital twin and replay-matched firmware show that, in simulation, VeriFlush gave no false passes "
          "where a timer gave 37 %, at the cost of abstaining in fault cases. Next: calibrated rig runs, then a "
          "shadow-mode pilot on one low-use branch."],
         [])

# ---------------- 9. appendix E status ----------------
for r in table_containing("Current draft status").rows[1:]:
    k = r.cells[0].text.strip()
    if k == "Technical evidence":
        set_cell(r.cells[2], "Digital evidence complete (SIMULATED); physical calibrations and runs pending")
    if k == "Cross-deliverable":
        set_cell(r.cells[2], "Simulated values agree between Table 6 and the video (37 %, 31 %, 0); physical run "
                             "ID and video pending")

# the hard break after the final-claim box can spill onto its own blank page: move it onto the heading
refs = para_starting("12. References")
prev = refs._p.getprevious()
for br in list(prev.iter(qn("w:br"))):
    if br.get(qn("w:type")) == "page":
        br.getparent().remove(br)
gap = docx.text.paragraph.Paragraph(prev, refs._parent)
gap.paragraph_format.space_before = gap.paragraph_format.space_after = Pt(0)
gap.paragraph_format.line_spacing = Pt(1)
refs.paragraph_format.page_break_before = True

d.save(DST)
todo = ["# Still required from the team before submission", "",
        "- **Section 1**: video link (viewable without sign-in); each member's programme and level; mentor position",
        "- **Section 5.1, Figure 2**: as-built photos (replace the labelled design render, same size)",
        "- **Section 5.2**: public link to the prototype (repository, demo or dataset), which the template requires",
        "- **Section 10**: one line per member naming a concrete output; dated advisor and mentor input",
        "- **Section 14**: both signatures and dates",
        "- **References**: [17] Dubai Building Code is never cited; cite it where it applies or remove it",
        "- **Section 5.1**: DS18B20 probes not yet fitted (one on bench test); once both read correctly, update the 5.1 sentence",
        "- **Section 5.1 / Table 3**: measure the as-built branch length (planned 8 m of 8 mm ID silicone)",
        "- **Section 7.2**: pump rated power (W, or V and A) from its label: ASIN B0HFN91BS4, 12 V, 240 L/h",
        "- **Table 5**: real Amazon receipt total (the AED 836.57 cart total is not the paid amount) and locally bought parts",
        "- **K-factor**: run the 500 mL jug test 3 times with the flow test sketch; send the pulse counts",
        "- **Rig build**: still to buy rigid PE stubs for the push-fit valves, small blade fuses (1/3/5 A) and tanks; fix the DS18B20 bench wiring",
        "- **Section 10 / AI disclosure**: confirm which other AI tool critiqued the parts list (named generically for now)",
        "- **Valves**: the report calls them manual; if XV-101 ends up servo-driven, update Sections 5.1 and 5.2",
        "- **Table 3 / results**: replace PREDICTED values with any measured ones (wet volume, K-factor, runs)",
        ""]
for title, items in TODO:
    todo.append(f"- **{title}**: " + "; ".join(items))
(ROOT / "report_assets" / "TEAM_TODO.md").write_text("\n".join(todo) + "\n", encoding="utf-8")
print("saved", DST)
