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
replace(para("Table 3. Calibration plan with PREDICTED"), "when the rig run is complete.",
        "when the rig run is complete. PREDICTED healthy run: fresh water at TT-101 after ≈ 34 s, Verified after "
        "≈ 94 s and ≈ 1 L.")
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
d.save(DST)
print("saved", DST)
