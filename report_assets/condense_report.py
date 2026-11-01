"""Third pass: fit report Sections 2-11 into 13 pages without losing the argument.

Run after improve_report.py:  python report_assets/condense_report.py <improved.docx> <out.docx>
- supporting detail moves to a new Appendix E (with a pointer left in the main text)
- boxes that repeat a table or the executive summary are removed
- forced page breaks before Sections 3 and 4 are removed so pages fill
- subsection numbers and cross-references are updated
"""
import copy
import sys
from pathlib import Path

import docx
from docx.oxml.ns import qn

SRC, DST = Path(sys.argv[1]), Path(sys.argv[2])
d = docx.Document(SRC)


def para(start):
    for p in d.paragraphs:
        if p.text.strip().startswith(start):
            return p
    raise KeyError(start)


def table_with(text):
    for t in d.tables:
        if any(text in c.text for r in t.rows for c in r.cells):
            return t
    raise KeyError(text)


def set_text(p, text):
    runs = p.runs
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def replace(p, old, new):
    for r in p.runs:
        if old in r.text:
            r.text = r.text.replace(old, new)
            return
    assert old in p.text, (old, p.text[:80])
    set_text(p, p.text.replace(old, new))


def drop(el):
    el.getparent().remove(el)


def text_of(el):
    return "".join(t.text or "" for t in el.iter(qn("w:t")))


# ---------------- collect what moves (before any edit changes the text) ----------------
moves = [
    ("E.1 State-of-the-art detail (from Section 4)", [para("Manual procedures typically specify")._p]),
    ("E.2 Rig implementation change (from Section 5.1)", [para("The current proof rig intentionally replaces")._p]),
    ("E.3 Decision inputs, frozen rules and reason codes (from Section 5.2)",
     [para("Inputs and frozen rules")._p, para("Reason codes, export and cross-checks.")._p,
      para("The digital prototype is the decision and communication layer")._p]),
    ("E.4 Evidence separation (from Section 5.3)", [para("Every result is classified as")._p]),
    ("E.5 Safety and field boundary (from Section 5.4)", [para("The rig is low voltage, non-potable")._p]),
    ("E.6 Data architecture, uncertainty and digital integration record (from Section 6.5)",
     [para("Each run receives an experiment ID")._p, para("Uncertainty sources include")._p,
      table_with("DIGITAL INTEGRATION RECORD")._tbl]),
    ("E.7 Lifecycle costs and pilot conditions (from Section 7)",
     [para("Scale economics must include")._p, para("The first field study is a supervised")._p]),
    ("E.8 Dashboard presentation rules (from Section 8.4)", [para("The dashboard presents these indicators")._p]),
]
moved = [(h, [copy.deepcopy(el) for el in els]) for h, els in moves]

# ---------------- main-text replacements and pointers ----------------
p22 = para("Manual procedures typically specify")
short22 = d.add_paragraph(
    "Manual procedures specify an elapsed time and record completion. Commercial systems already combine schedules, "
    "usage, volume, temperature, diagnostics, logs and BMS links [8]–[12] (Table 1); these are manufacturer-described "
    "functions, not independent public-health evidence (detail in Appendix E.1).", style="Normal")
p22._p.addprevious(short22._p)
drop(p22._p)

drop(para("The current proof rig intentionally replaces")._p)
replace(para("Evidence boundary:"), "lasting microbial control.",
        "lasting microbial control. The rig is low-voltage, non-potable and never connected to drinking-water "
        "plumbing; the safety rules and the change from the earlier ESP32 design are in Appendix E.2 and E.5.")

p39 = para("Inputs and frozen rules")
ptr = d.add_paragraph(style="Normal")
ptr.add_run("Decision rules. ").bold = True
ptr.add_run("VeriFlush reports Verified only when the valve is confirmed open, the endpoint reaches the feed "
            "temperature and three endpoint-anchored branch volumes have passed; missing, weak or contradictory "
            "evidence gives Uncertain, and blockage or time-out gives Failed (Table 2). Inputs, the thresholds frozen "
            "on 30 October 2026 and all reason codes are in Appendix E.3. Cross-checks: EPANET 2.2 agrees within "
            "0.6 %, the firmware matches Python in 13/13 scenarios, and 42 automated tests pass.")
p39._p.addprevious(ptr._p)
for start in ("Inputs and frozen rules", "Reason codes, export and cross-checks.",
              "The digital prototype is the decision and communication layer"):
    drop(para(start)._p)

for start in ("5.3 Evidence separation", "Every result is classified as", "5.4 Safety and field boundary",
              "The rig is low voltage, non-potable"):
    drop(para(start)._p)

set_text(para("The digital prototype's values were frozen"),
         "The digital rules were frozen on 30 October 2026 (Appendix E.3); the physical set uses the same frozen "
         "rules, a fixed maximum run time and volume, and reports every exclusion.")

for start in ("6.5 Data architecture", "Each run receives an experiment ID", "Uncertainty sources include"):
    drop(para(start)._p)
drop(table_with("DIGITAL INTEGRATION RECORD")._tbl)
set_text(para("6.6 Results, limitations and technology readiness"), "6.5 Results, limitations and technology readiness")
replace(para("The minimum evidence set is three"), "(Tables A2–A3).",
        "(Tables A2–A3); run records and uncertainty sources are in Appendix E.6.")

drop(table_with("RESULTS SUMMARY")._tbl)
replace(para("Table 3. Calibration plan with design"), "as rig runs are completed.",
        "as rig runs are completed. Design expectation for a healthy run: fresh water at TT-101 after ≈ 34 s and "
        "Verified after ≈ 94 s and ≈ 1 L.")
for p in d.paragraphs:
    if p.text.strip() == "TRL":
        drop(p._p)
        break
drop(para("Using the European Commission TRL scale")._p)
trl = table_with("TECHNOLOGY READINESS")
replace(trl.rows[0].cells[0].paragraphs[0], "TECHNOLOGY READINESS", "TECHNOLOGY READINESS (European Commission scale [20])")

drop(para("Scale economics must include")._p)
set_text(para("The first field study is a supervised"),
         "The first field study is a supervised, reversible shadow-mode pilot on one mapped, non-critical branch; "
         "closed-loop control follows only after leak, valve, sensor, cybersecurity and operator-response tests "
         "pass, consistent with CDC water-management principles [24]. Approvals, site conditions and lifecycle costs "
         "are in Appendix E.7.")
drop(table_with("RESOURCE SUMMARY")._tbl)

set_text(para("The recommended impact unit is one correctly handled"),
         "The impact unit is one correctly handled flush event, not a population-health claim; indicators and pilot "
         "targets are in Table 7.")
drop(para("The dashboard presents these indicators")._p)
drop(table_with("IMPACT SUMMARY")._tbl)
drop(table_with("SUMMARY CLAIM")._tbl)

# ---------------- v12 panel fixes ----------------
set_text(para("Low-use and distal plumbing branches can retain aged water."),
         "Low-use and distal plumbing branches can retain aged water, and the time and volume needed to refresh "
         "one vary with building geometry and hydraulics [1]–[6]. Today a flush is recorded as done when a timer or "
         "volume target is reached [7]–[12]; nobody checks that the old water in the intended branch was actually "
         "displaced.")
replace(para("Impact and next step."), "(0.94 vs 0.82 L per flush)", "(mean 0.94 vs 0.82 L per flush)")
replace(para("Decision rules."), "three endpoint-anchored branch volumes have passed;",
        "three endpoint-anchored branch volumes (counted from the moment fresh water reaches TT-101) have passed;")
replace(para("Decision rules."), "Inputs, the thresholds frozen on 30 October 2026 and all reason codes are in "
        "Appendix E.3.", "Frozen thresholds (30 October 2026): 3 volumes; feed-to-endpoint contrast ≥ 1.5 °C; branch-"
        "volume ratio 0.6–1.4× (Failed above 3×); hard stop 300 s. Inputs and all reason codes are in Appendix E.3.")
replace(para("The physical prototype is a supervised"), "(≈ 0.40 L).",
        "(≈ 0.40 L); the headline simulations use the original 6 m (0.302 L) specification and the 8 m branch is a "
        "sensitivity case (Table 3).")
replace(para("Table 4. SIMULATED results"), "without endpoint evidence.",
        "without endpoint evidence. All 240 come from the six scenarios with a faulted valve, flow sensor or probe, "
        "or weak contrast (S03, S08–S11), 40 runs each.")
replace(para("Mechanical assembly is in progress"), "unless a 5-volume policy is used.",
        "unless a 5-volume policy is used. The tracer truth comes from the team's own transport model, but it is "
        "computed separately from the decision rules, the thresholds were frozen before scoring, and a second "
        "(radial) transport model also gives 0 false passes. The 5 % old-water threshold is an engineering choice; "
        "at 2 % VeriFlush produces false passes in the sensitivity study.")
replace(para("Lifecycle needs") if any(p.text.startswith("Lifecycle needs") for p in d.paragraphs)
        else para("The first field study is a supervised"), "Approvals, site conditions and lifecycle costs are in "
        "Appendix E.7.", "Each node needs scheduled gravimetric flow checks, valve proof tests, probe cleaning and "
        "recalibration, power and configuration audits, firmware and security updates, spares, and recertification "
        "after any branch change (AED 100–300 per branch a year, ASSUMED; Table 5). Approvals and site conditions "
        "are in Appendix E.7.")
for p in d.paragraphs:
    if "against SDG indicator 6.4.1" in p.text:
        replace(p, "report litres per verified event against SDG indicator 6.4.1 (water-use efficiency).",
                "report litres per verified event as site evidence for target 6.4 that can feed sector-level 6.4.1 "
                "reporting.")
        new = d.add_paragraph("• WHO Water Safety in Buildings users [25]: treat flush completion as a verification "
                              "step with an Uncertain escalation path, and adopt the flush-event record as an open "
                              "schema.", style=p.style)
        p._p.addnext(new._p)
        break
t7 = table_with("Stop on evidence")
for r in t7.rows:
    if r.cells[0].text.strip() == "Stop on evidence":
        c = r.cells[4]
        set_text(c.paragraphs[0], "L per event ≤ the site's actual timer (simulated vs a correctly sized timer: "
                                  "0.94 vs 0.82 L)")
replace(para("The UAE’s reliance on desalinated potable water"), "would raise the Uncertain rate.",
        "would raise the Uncertain rate. VeriFlush targets cold-water branches; hot-water outlets can already be "
        "checked against a temperature target.")
replace(para("The digital prototype exposes"), "rather than assume one vendor:",
        "rather than assume one vendor, and each event exports as a closed work order to the site's CAFM/CMMS, "
        "where TG-44 records are kept:")
replace(para("The first model to test is a verification service"), "set in the pilot.",
        "set in the pilot, and the price must stay below the 8–22 staff-hours per branch a year it saves "
        "(Section 7.2).")
replace(para("Go/no-go: the owner assigns authority"), "substitute for water-safety validation.",
        "substitute for water-safety validation. Approval steps: wetted parts certified for potable contact (e.g. "
        "NSF/ANSI 61 or WRAS), UAE conformity marking, installer sign-off, and IEC 62443-aligned security for any "
        "BMS link.")
t1 = table_with("Connected products")
cost = {"Approach": "Maturity / indicative cost", "Manual / timer": "Established; operator time only",
        "Flow + volume": "Commercial; price not published in reviewed sources",
        "Volume + temperature": "Research/commercial; price not published",
        "Connected products": "High; price not published",
        "VeriFlush (proposed)": "Physical assembly in progress; digital prototype complete (simulated); node "
                                "≈ AED 1,500–4,000 installed (ASSUMED)"}
ref_size = t1.rows[1].cells[2].paragraphs[0].runs[0].font.size
for r in t1.rows:
    k = r.cells[0].text.strip()
    if k in cost:
        set_text(r.cells[2].paragraphs[0], cost[k])
    if r is not t1.rows[0]:
        for c in r.cells:
            for cp in c.paragraphs:
                for run in cp.runs:
                    run.font.size = ref_size

replace(para("Platform and architecture."), "live or offline dashboard (Figure 3).",
        "live or offline dashboard (Figure 3). Code, data and the dashboard are public at "
        "https://github.com/MoAqil/veriflush.")

# ---------------- v13 panel fixes ----------------
replace(para("Low-use and distal plumbing branches can retain aged water,"),
        "nobody checks that the old water in the intended branch was actually displaced.",
        "the record rarely shows whether the old water in the intended branch was actually displaced.")
replace(para("Table 4. SIMULATED results"), "(S03, S08–S11), 40 runs each.",
        "(S03, S08, S09a, S09b, S10, S11), 40 runs each.")
replace(para("Electrical consumption is estimated similarly"),
        "Electrical consumption is estimated similarly from measured current/time or rated power clearly labelled "
        "as an upper-bound assumption.",
        "Electrical use is small: at an ASSUMED 5–10 W pump rating (replaced by the label value once read) a 94 s "
        "flush uses about 0.1–0.3 Wh, plus about 0.25 W for the controller.")
p81 = para("VeriFlush aligns most directly with Theme 3")
full = p81.text
cut_a = full.index("Secondary links are")
cut_b = full.index("Scaled linearly per room")
cut_c = full.index("Among the 2026 UN Water Conference themes")
scale = full[cut_b:cut_c].strip()
set_text(p81, full[:cut_a].strip())
second = d.add_paragraph((full[cut_a:cut_b] + full[cut_c:]).strip(), style=p81.style)
p81._p.addnext(second._p)
t8cap = para("Table 8. MODELLED 300-room hotel")
t8 = t8cap._p.getnext()
while t8.tag != qn("w:tbl"):
    t8 = t8.getnext()
moved_scale = d.add_paragraph(scale, style="Normal")
t8.addnext(moved_scale._p)

# ---------------- authoritative rig brief (1 Nov 2026): assembled, 4.8 W pump, YF-S401, probes on D4 ----------------
def rep_all(old, new):
    hits = 0
    paras = list(d.paragraphs) + [cp for t in d.tables for r in t.rows for c in r.cells for cp in c.paragraphs]
    for p in paras:
        if old in p.text:
            replace(p, old, new)
            hits += 1
    assert hits, old


rep_all("mechanical assembly of the non-potable proof rig is in progress using",
        "the non-potable proof rig is fully assembled, with calibration and validation runs in progress, using")
rep_all("The physical rig (Uno R3, manual valves, flow sensor, bypass) is being assembled to repeat the key cases "
        "with measured data.", "The physical rig (Uno R3, manual valves, YF-S401 flow sensor, bypass) is now "
        "assembled; calibration and validation runs will repeat the key cases with measured data.")
rep_all("Physical assembly in progress; digital prototype complete (simulated)",
        "Physical rig assembled, calibration pending; digital prototype complete (simulated)")
rep_all("by a submersible nominal 12 V, 240 L·h⁻¹ brushless pump placed in the tank.",
        "by a submersible 12 V, 4.8 W brushless pump (nominal maximum 240 L·h⁻¹) placed in the tank.")
rep_all("which contains flow sensor FT-101,", "which contains YF-S401 flow sensor FT-101 (nominal 0.5–5 L/min),")
rep_all("The monitored branch is planned as 8 m of 8 mm ID silicone tubing (≈ 0.40 L);",
        "The monitored branch is a coil of 8 mm ID silicone tubing, about 6–8 m long (0.30–0.40 L; centreline "
        "length to be measured);")
rep_all("The two DS18B20 endpoint probes (TT-100 feed, TT-101 endpoint) are not yet fitted; one is being "
        "bench-tested, so endpoint results remain SIMULATED.",
        "Two waterproof DS18B20 probes (TT-100 feed tank, TT-101 endpoint) share pin D4 with one 4.7 kΩ pull-up "
        "and already log on the rig; until their offsets are calibrated, endpoint results remain SIMULATED.")
rep_all("Mechanical assembly is in progress, so no calibrated physical result is reported yet;",
        "The rig is assembled but not yet calibrated, so no calibrated physical result is reported yet;")
rep_all("TRL 2 for the physical subsystem, which is being assembled.",
        "TRL 2 for the physical subsystem, which is assembled and awaiting calibration.")
rep_all("Electrical use is small: at an ASSUMED 5–10 W pump rating (replaced by the label value once read) a 94 s "
        "flush uses about 0.1–0.3 Wh, plus about 0.25 W for the controller.",
        "Electrical use is small: the pump is rated 4.8 W, so a 94 s flush uses at most about 0.13 Wh, plus about "
        "0.25 W (ASSUMED) for the USB-powered controller.")
for old, new in (("Mohammed Aqil", "Mohammed Aqil Mohideen"), ("Alvin Alex", "Alvin Titus Alex"),
                 ("Fawaz Ahmad", "Fawaz Ahmed")):          # full names confirmed by the team, 1 Nov 2026
    paras_all = list(d.paragraphs) + [cp for t in d.tables for r in t.rows for c in r.cells for cp in c.paragraphs]
    for p in paras_all:
        if old in p.text and new not in p.text:
            replace(p, old, new)
for p in [cp for t in d.tables for r in t.rows for c in r.cells for cp in c.paragraphs]:
    if p.text.startswith("Planned 8 m of 8 mm ID silicone."):
        set_text(p, "Coil of 8 mm ID silicone, about 6–8 m (to be measured). Headline runs use 6 m; in the 8 m "
                    "sensitivity case VeriFlush still gives 0 false passes (timer 40 %, flow + volume 45 %)")
    elif p.text.startswith("≈ 0.40 L branch (8 m) + 0.04 L upstream"):
        set_text(p, "0.30–0.40 L branch (6–8 m) + 0.04 L upstream")
    elif p.text.startswith("≈ 5,900 pulses/L (nominal Hall sensor)"):
        set_text(p, "≈ 5,900 pulses/L (YF-S401 nominal); healthy branch ≈ 0.63 L/min; valid range 0.5–5 L/min")

# ---------------- Figure 2: as-built photograph replaces the design render ----------------
photo = Path(__file__).resolve().parent / "_rig_asbuilt_labelled.png"
if photo.exists():
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt
    cap2 = para("Figure 2. Design model of the proof rig")
    old_img = cap2._p.getprevious()
    pic = d.add_paragraph()
    pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic.paragraph_format.keep_with_next = True
    pic.paragraph_format.space_after = Pt(2)
    pic.add_run().add_picture(str(photo), width=Cm(14.0))
    old_img.addprevious(pic._p)
    drop(old_img)
    set_text(cap2, "Figure 2. As-built physical proof rig, photographed 1 November 2026 (non-potable, tabletop). "
                   "Water flows from the feed tank (feed probe TT-100 inside) through the Y splitter and FT-101 "
                   "into the monitored coil, past "
                   "endpoint probe TT-101 and the manual outlet valve; side branches feed the diversion and "
                   "reference boxes. The dead-end gauge leg PG-101 is just outside the frame, and tubing lengths "
                   "are still to be measured.")

replace(para("Generative-AI disclosure:"), "Another AI tool was used once to critique the parts list.",
        "Another AI tool was used once to critique the parts list. The design values in Table 3 come from the "
        "digital twin and component datasheets; this version reports no rig measurement, and no value was invented.")

# ---------------- tone pass: evidence labels in plain lowercase instead of all-caps ----------------
import re
CAPS = [(r"\(SIMULATED\)", "(simulated)"), (r"\bSIMULATED\b", "simulated"), (r"\bPREDICTED\b", "predicted"),
        (r"\bMODELLED\b", "modelled"), (r"\bASSUMED\b", "assumed"), (r"\bDESIGN\b", "design")]
for p in list(d.paragraphs) + [cp for t in d.tables for r in t.rows for c in r.cells for cp in c.paragraphs]:
    if p.style is not None and p.style.name.startswith("Heading"):
        continue
    for r in p.runs:
        txt = r.text
        for pat, rep in CAPS:
            txt = re.sub(pat, rep, txt)
        if txt != r.text:
            r.text = txt
for p in list(d.paragraphs) + [cp for t in d.tables for r in t.rows for c in r.cells for cp in c.paragraphs]:
    for r in p.runs:                      # sentence starts that became lowercase (never touch break-only runs)
        new = re.sub(r"(^|[.:;]\s+)(simulated|predicted|modelled|assumed)\b",
                     lambda m: m.group(1) + m.group(2).capitalize(), r.text)
        if new != r.text:
            r.text = new

# ---------------- template format: body text Calibri 11 pt, 1.15 line spacing ----------------
from docx.shared import Pt as _Pt
normal = d.styles["Normal"]
normal.font.name, normal.font.size = "Calibri", _Pt(11)
normal.paragraph_format.line_spacing = 1.15
for p in d.paragraphs:                    # body paragraphs only (tables and captions keep their own sizes)
    if p.style.name in ("Normal", "List Paragraph"):
        p.paragraph_format.line_spacing = 1.15
        for r in p.runs:
            if r.font.size is not None and r.font.size.pt < 11 and r.font.name != "Cambria Math":
                r.font.size = None

# forced page breaks before Sections 3 and 4
for head in ("3. Problem Definition and Context", "4. State of the Art and Gap"):
    el = para(head)._p.getprevious()
    while el is not None and text_of(el).strip() == "":
        for br in list(el.iter(qn("w:br"))):
            if br.get(qn("w:type")) == "page":
                br.getparent().remove(br)
        el = el.getprevious()

# ---------------- Appendix E ----------------
decl = para("14. Team Leader and Academic Advisor Declaration")._p
anchor = decl.getprevious()               # the page-break paragraph before the declaration
h = d.add_paragraph("Appendix E — Supporting design, method and scale-up detail", style="Heading 2")
anchor.addprevious(h._p)
for title, els in moved:
    sub = d.add_paragraph(title, style="Heading 3")
    anchor.addprevious(sub._p)
    for el in els:
        anchor.addprevious(el)

# ---------------- fit Sections 2-11 into 15 pages at Calibri 11 / 1.15 ----------------
def to_appendix(title, elements):
    sub = d.add_paragraph(title, style="Heading 3")
    anchor.addprevious(sub._p)
    for el in elements:
        anchor.addprevious(el)               # moves the element


p26 = para("The project does not claim invention")
to_appendix("E.9 Prior automated-flushing work (from Section 4)", [p26._p])
contrib = d.add_paragraph("VeriFlush does not claim to invent automatic flushing, flow integration, temperature "
                          "sensing or digital records; prior systems are reviewed in Appendix E.9. Its contribution "
                          "is branch-level evidence fusion with an explicit Uncertain outcome, a reproducible "
                          "comparison against timer-only completion, and an audit record of why a flush was or was "
                          "not verified.", style="Normal")
para("The adversarial question is whether")._p.addprevious(contrib._p)

gov = para("The digital prototype exposes")
gov_ptr = d.add_paragraph("Each flush event exports as a closed work order to the site's CAFM/CMMS, where TG-44 "
                          "records are kept; interfaces, cybersecurity and data-governance requirements are in "
                          "Appendix E.10.", style="Normal")
gov._p.addprevious(gov_ptr._p)
to_appendix("E.10 Digital integration and governance (from Section 9.1)", [gov._p])

cap9 = para("Table 9. Stage-gated adoption decisions")
tbl9 = cap9._p.getnext()
while tbl9.tag != qn("w:tbl"):
    tbl9 = tbl9.getnext()
replace(cap9, "Table 9.", "Table A8.")
to_appendix("E.11 Stage-gated adoption decisions (from Section 9)", [cap9._p, tbl9])
replace(para("Go/no-go: the owner assigns authority"), "Go/no-go:", "Stage gates are listed in Appendix E.11 "
        "(Table A8). Go/no-go:")

set_text(para("VeriFlush addresses the evidence gap between"),
         "VeriFlush addresses the gap between a completed flush and branch-level exchange. It does not decide when a "
         "facility must flush, detect microorganisms or certify potability; those decisions remain with qualified "
         "facility and public-health professionals.")
replace(para("The UAE’s reliance on desalinated potable water"),
        "Dubai Municipality’s current Technical Guideline 44 (Version 6) requires a flushing policy, weekly flushing of "
        "taps and showers in unoccupied guest rooms/areas and flushing before occupation; it also calls for schematics, "
        "operating records and system water volume with the date and determination method [23]",
        "Technical Guideline 44 (Version 6) requires weekly flushing of unoccupied guest rooms and records of system "
        "water volume and how it was determined [23]")
replace(para("The first field study is a supervised"),
        "Each node needs scheduled gravimetric flow checks, valve proof tests, probe cleaning and recalibration, power "
        "and configuration audits, firmware and security updates, spares, and recertification after any branch change "
        "(AED 100–300 per branch a year, assumed; Table 5).",
        "Each node needs periodic flow checks, valve tests, probe recalibration and firmware updates (AED 100–300 per "
        "branch a year, assumed; Table 5).")
# ---------------- summary boxes become ordinary paragraphs with a bold lead-in ----------------
LEADS = {"AT A GLANCE": "In short (simulated digital twin, 520 flushes per method). ",
         "TECHNOLOGY READINESS": "Technology readiness (European Commission scale [20]). ",
         "DIGITAL INTEGRATION RECORD": "Digital integration record (31 Oct 2026). "}
for t in list(d.tables):
    cell = t.rows[0].cells[0]
    if len(t.rows) != 1 or not any(s.get(qn("w:fill"), "").upper() == "EEF3F8" for s in cell._tc.iter(qn("w:shd"))):
        continue
    lines = [cp.text.strip() for cp in cell.paragraphs if cp.text.strip()]
    lead = next((v for k, v in LEADS.items() if lines[0].upper().startswith(k)), lines[0].capitalize() + ". ")
    body = " ".join(l.lstrip("• ").strip() for l in lines[1:])
    np_ = d.add_paragraph(style="Normal")
    np_.add_run(lead).bold = True
    np_.add_run(body)
    t._tbl.addprevious(np_._p)
    t._tbl.getparent().remove(t._tbl)

cb = table_with("TEAM INPUT REQUIRED - CONTRIBUTIONS").rows[0].cells[0]   # blank lines for the team to fill
for extra in cb.paragraphs[1:]:
    extra._p.getparent().remove(extra._p)
first = cb.paragraphs[0]
for r in list(first.runs):
    r._r.getparent().remove(r._r)
first.add_run("Mohamad Zaheen (team leader): ")
drop(para("Confirmed team identity:")._p)       # the box below lists everyone
for who in ("Mohammed Aqil Mohideen: ", "Fawaz Ahmed: ", "Alvin Titus Alex: ",
            "Advisor Prof. Manzar Abbas / mentor Nishant Keloth (Borouge), input and dates: "):
    np_ = cb.add_paragraph(who)
for cp in cb.paragraphs:
    cp.paragraph_format.space_after = _Pt(1)
    for r in cp.runs:
        r.bold, r.font.color.rgb = False, None
for shd in cb._tc.iter(qn("w:shd")):
    shd.set(qn("w:fill"), "FFFFFF")
for b in cb._tc.iter():
    if b.get(qn("w:color")) == "C9A227":
        b.set(qn("w:color"), "BFBFBF")
# ---------------- Appendix F: data tables, read directly from the project's output files ----------------
import csv

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    with open(ROOT / path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def nice(s):
    return s.replace("_", " ", 1).replace("_", " ")


def add_table(caption, header, body, widths_cm):
    from docx.shared import Cm
    cap = d.add_paragraph(caption, style="Figure Caption")
    anchor.addprevious(cap._p)
    t = d.add_table(rows=1 + len(body), cols=len(header))
    t.style = d.styles["Table Grid"]
    for r_i, vals in enumerate([header] + body):
        for c_i, v in enumerate(vals):
            cell = t.rows[r_i].cells[c_i]
            cell.width = Cm(widths_cm[c_i])
            cp = cell.paragraphs[0]
            cp.paragraph_format.space_after = _Pt(0)
            cp.paragraph_format.line_spacing = 1.0
            run = cp.add_run(str(v))
            run.font.size = _Pt(8.5)
            run.bold = r_i == 0
            cp.paragraph_format.keep_with_next = r_i < len(body)      # keep each table on one page
    cap.paragraph_format.keep_with_next = True
    if True:
        for c in t.rows[0].cells:
            tcPr = c._tc.get_or_add_tcPr()
            shd = tcPr.makeelement(qn("w:shd"), {qn("w:val"): "clear", qn("w:color"): "auto", qn("w:fill"): "E7ECF2"})
            tcPr.append(shd)
    anchor.addprevious(t._tbl)
    gap = d.add_paragraph("", style="Normal")
    gap.paragraph_format.space_after = _Pt(2)
    anchor.addprevious(gap._p)


hF = d.add_paragraph("Appendix F — Data tables", style="Heading 2")
anchor.addprevious(hF._p)
intro = d.add_paragraph("All values below are taken directly from the project files in the public repository "
                        "(github.com/MoAqil/veriflush): outputs/tables, epanet/ and data/physical. Digital results are "
                        "simulated; Table A12 is the first physical shakedown log, before calibration.", style="Normal")
anchor.addprevious(intro._p)

by = {}
for r in rows("outputs/tables/method_comparison_by_scenario.csv"):
    by.setdefault(r["scenario"], {})[r["method"]] = r
body = []
for sc, m in by.items():
    vf = m["VeriFlush"]
    body.append([nice(sc), m["Timer-only"]["False pass"], m["Flow + configured volume"]["False pass"],
                 int(vf["True pass"]) + int(vf["False pass"]), int(vf["True failure"]) + int(vf["False failure"]),
                 vf["Uncertain"], vf["False pass"]])
tot = [sum(int(r[k]) for r in body) for k in range(1, 7)]
body.append(["All 13 scenarios"] + tot)
add_table("Table A9. Simulated results by scenario (40 runs per scenario per method; two-region transport).",
          ["Scenario", "Timer false passes", "Flow + volume false passes", "VeriFlush Verified", "VeriFlush Failed",
           "VeriFlush Uncertain", "VeriFlush false passes"], body, [4.2, 2.0, 2.4, 2.0, 2.0, 2.2, 2.2])

body = [[nice(r["scenario"]), f"{float(r['epanet_branch_flow_lpm']):.3f} / {float(r['python_branch_flow_lpm']):.3f}",
         f"{float(r['epanet_manifold_kpa']):.2f} / {float(r['python_manifold_kpa']):.2f}",
         (f"{float(r['epanet_t50_endpoint_s']):.0f} / {float(r['plug_flow_t50_s']):.0f}"
          if r["epanet_t50_endpoint_s"] else "no flow")]
        for r in rows("epanet/epanet_vs_python.csv")]
add_table("Table A10. EPANET 2.2 rig models against the Python model (simulated).",
          ["Scenario", "Branch flow, L/min (EPANET / Python)", "Manifold pressure, kPa (EPANET / Python)",
           "Endpoint 50 % arrival, s (EPANET / plug flow)"], body, [4.0, 4.0, 4.0, 4.0])

body = [[nice(r["scenario"]), f"{r['python_verdict']} / {r['fw_verdict']}",
         f"{float(r['python_t_close_s']):.0f} / {float(r['fw_t_close_s']):.0f}",
         f"{float(r['python_v_l']):.3f} / {float(r['fw_v_l']):.3f}",
         "yes" if r["verdict_match"] == "True" and r["t_close_match"] == "True" else "no"]
        for r in rows("outputs/tables/firmware_vs_python.csv")]
add_table("Table A11. Arduino firmware replay against the Python engine (same simulated sensor traces).",
          ["Scenario", "Verdict (Python / firmware)", "Stop time, s", "Litres", "Match"], body,
          [4.2, 4.6, 2.6, 3.0, 1.6])

log = []
with open(ROOT / "data/physical/shakedown_run1.csv", encoding="utf-8") as f:
    log = [r for r in csv.DictReader(l for l in f if not l.startswith("#"))]
flowing = [r for r in log if int(r["pulses_per_s"]) > 0]
pulses = sum(int(r["pulses_per_s"]) for r in flowing)
rate = [int(r["pulses_per_s"]) for r in flowing if int(r["pulses_per_s"]) >= 10]
body = [["Date and run", "1 November 2026, shakedown run 1 (Serial Monitor log)"],
        ["Flow logged", f"{flowing[0]['time_s']}–{flowing[-1]['time_s']} s ({len(flowing)} s with pulses)"],
        ["Total pulses", f"{pulses}"],
        ["Steady pulse rate", f"{min(rate)}–{max(rate)} pulses/s"],
        ["Volume and flow at the uncalibrated K = 5,880 /L",
         f"{pulses / 5880:.3f} L; {min(rate) / 5880 * 60:.2f}–{max(rate) / 5880 * 60:.2f} L/min"],
        ["Probe readings (T1 / T2)", f"{log[0]['T1_C']} °C / {log[0]['T2_C']} °C (offset not yet calibrated)"],
        ["Status", "Hardware and logging check only; K-factor, wet volume and probe offsets still to be calibrated"]]
add_table("Table A12. Physical shakedown run 1 on the as-built rig (measured, uncalibrated).",
          ["Item", "Value"], body, [5.5, 11.0])

for p in d.paragraphs:                    # moved and new paragraphs follow the 11 pt / 1.15 body format
    if p.style.name in ("Normal", "List Paragraph"):
        p.paragraph_format.line_spacing = 1.15
d.save(DST)
print("saved", DST)
