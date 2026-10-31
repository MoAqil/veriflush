"""Second pass on the filled report: judge-panel fixes that need no new measurements.

Run after fill_report.py:  python report_assets/improve_report.py <filled.docx> <out.docx>
- consistent false-pass metric, executive summary with key result and ask, no draft language
- design figure for the empty Figure 2 slot, counterexample back as Figure 4
- planning tables (old 4, 5) and go/no-go gates moved to Appendix A; tables renumbered
- current and target TRL, indicative costs and payback, SDG mapping and pilot targets
- SI units, section numbering, citations for previously uncited references
"""
import re
import sys
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[1]
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
    full = p.text
    assert old in full, (old, full[:80])
    set_text(p, full.replace(old, new))


def set_cell(cell, text):
    p = cell.paragraphs[0]
    set_text(p, text) if p.runs else p.add_run(text)
    for extra in cell.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)


def new_para_after(anchor_el, text="", style="Normal"):
    p = d.add_paragraph(text, style=style)
    anchor_el.addnext(p._p)
    return p


def image_para(path, width_cm):
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(str(path), width=Cm(width_cm))
    return p


def remove(p):
    p._p.getparent().remove(p._p)


# ---------------- title block and project information ----------------
set_text(para("VeriFlush Final Report"), "VeriFlush Final Report")
for r in d.tables[0].rows:
    if r.cells[0].text.startswith("One-Sentence"):
        set_cell(r.cells[1], "VeriFlush verifies whether a building flush actually replaced a branch's stagnant "
                             "water, reporting Verified, Failed or Uncertain from flow, volume and endpoint evidence.")
replace(para("Status at 31 October 2026"),
        " A separate digital decision-support prototype is being developed in parallel. Yellow evidence boxes "
        "identify the exact measurements, screenshots and team confirmations required before submission.", "")

# ---------------- executive summary ----------------
set_text(para("Development is split into two connected demonstrations"),
         "Key result (SIMULATED). A digital twin of the proof rig ran 13 normal and fault scenarios 40 times each "
         "(520 flushes per method), scored against a hidden tracer the decision code cannot read. A fixed timer "
         "declared success while more than 5 % old water remained in 37 % of runs, and flow plus configured volume "
         "in 31 %; VeriFlush did so in none and detected 93 % of injected faults. The same Arduino firmware, "
         "compiled for the Uno R3, reproduces these verdicts in 13/13 scenarios. The physical rig (Uno R3, manual "
         "valves, flow sensor, bypass) is being assembled to repeat the key cases with measured data.")
set_text(para("The submission will compare a fixed timer"),
         "Impact and next step. Dubai Municipality's Technical Guideline 44 already requires weekly flushing of "
         "unoccupied hotel rooms and records of system water volume [23]. VeriFlush turns that timer log into "
         "evidence that the water was actually exchanged, and stops early where fixed times over-flush (MODELLED "
         "322 m³ yr⁻¹ for one 300-room hotel). Next we need calibrated rig runs, then a supervised shadow-mode "
         "pilot on one low-use hotel or school branch with a facility-management partner.")

# ---------------- section 3 and 4 citations, units ----------------
replace(para("Premise plumbing is the part"), "not pathogen risk or unsafe water at every low-use outlet.",
        "not pathogen risk or unsafe water at every low-use outlet. How well flushing works also depends on "
        "water age, disinfectant type and temperature [29].")
p = para("Geometry also matters.")
replace(p, "158,359 million imperial gallons of desalinated-water production",
        "about 720 million m³ (158,359 million imperial gallons) of desalinated-water production")
replace(p, "while limiting avoidable potable-water discharge.",
        "while limiting avoidable potable-water discharge [13], [14], [23].")
replace(para("The adversarial question is whether"), "test whether the decision layer detects known weaknesses.",
        "test whether the decision layer detects known weaknesses, in line with statistical fault-detection work "
        "on building water systems [18].")

# ---------------- section 5 ----------------
box = para("TEAM INPUT REQUIRED - Replace this box with one labelled as-built photograph")
img = image_para(ROOT / "3d/renders/S01_healthy_wide_t22.png", 13.0)
box._p.addprevious(img._p)
remove(box)
set_text(para("Figure 2. Final as-built physical proof rig"),
         "Figure 2. Design model of the proof rig (Blender, built from the team's purchased parts; coil colour "
         "from the simulation at t = 22 s): feed tank, pump, pressure gauge, splitters, manual valves, flow "
         "sensor, coil branch, bypass and outlet tanks. DESIGN, not an as-built photograph; the built rig uses a "
         "submersible pump inside the feed tank.")
replace(para("The physical prototype is a supervised"), "by a nominal 12 V, 240 L h-1 brushless pump.",
        "by a submersible nominal 12 V, 240 L·h⁻¹ brushless pump placed in the tank.")
replace(para("Platform and architecture."), "cross-checked by a radial laminar model.",
        "cross-checked by a radial laminar model (dead-end transport remains an active research topic [19]).")

# ---------------- section 6 ----------------
replace(para("Before the final demonstration set, the team will freeze"),
        "Before the final demonstration set, the team will freeze:",
        "The digital prototype's values were frozen on 30 October 2026 (Section 5.2); before the final physical "
        "set the team freezes:")

# move old Table 4, Table 5 and 6.6 go/no-go to the end of Appendix A
anchor = para("Appendix B")._p.getprevious()          # last element of Appendix A
moved = []
for cap_start in ("Table 4. Minimum weekend demonstration matrix", "Table 5. Planned analysis and evidence labels"):
    cap = para(cap_start)
    tbl = cap._p.getnext()
    while tbl.tag != qn("w:tbl"):
        tbl = tbl.getnext()
    moved += [cap._p, tbl]
gonogo = para("6.6 Go/no-go logic")
moved.append(gonogo._p)
el = gonogo._p.getnext()
while el is not None and el.tag == qn("w:p") and "".join(t.text or "" for t in el.iter(qn("w:t"))).startswith("•"):
    moved.append(el)
    el = el.getnext()
for el in moved:
    anchor.addnext(el)
    anchor = el
replace(para("Table 4. Minimum weekend demonstration matrix"), "Table 4.", "Table A7.")
replace(para("Table 5. Planned analysis and evidence labels"), "Table 5.", "Table A8.")
set_text(gonogo, "Go/no-go gates")
gonogo.style = d.styles["Heading 3"]
replace(para("The minimum evidence set is three"), "the report presents the exact achieved n and narrows its claims.",
        "the report presents the exact achieved n and narrows its claims. The full demonstration matrix, analysis "
        "plan and go/no-go gates are in Appendix A (Tables A7–A8).")
set_text(para("6.7 Results, limitations and technology readiness"), "6.6 Results, limitations and technology readiness")

# Table 6: one metric over all runs; drop the unmodelled row
t6 = table_with("Median L / true Verified")
set_cell(t6.rows[0].cells[2], "False pass (of all runs)")
fp = {"Fixed timer": "194/520 (37 %)", "Flow + configured-volume threshold": "160/520 (31 %)",
      "Full VeriFlush": "0/520 (0 %)"}
for r in list(t6.rows[1:]):
    k = r.cells[0].text.strip()
    if k in fp:
        set_cell(r.cells[2], fp[k])
    else:
        r._tr.getparent().remove(r._tr)
set_text(para("Table 6. SIMULATED results"),
         "Table 6. SIMULATED results (two-region transport; 13 scenarios × 40 seeds = 520 runs per method). False "
         "pass = Verified while more than 5 % old water remained at that method's own stop. Among each method's "
         "unsuccessful runs (Eq. 4) the rates are 100 % (194/194; a timer always reports complete), 80 % (160/200) "
         "and 0 % (0/80). Seeds within a scenario are not independent, so this is scenario coverage, not a "
         "statistical rate. Physical results are pending.")

# replace the 'required plots' plan with the counterexample figure
req = para("Required representative plots")
el = req._p.getnext()
while el is not None and "".join(t.text or "" for t in el.iter(qn("w:t"))).startswith("•"):
    nxt = el.getnext()
    el.getparent().remove(el)
    el = nxt
fig = image_para(ROOT / "outputs/figures/fig02_diversion_comparison.png", 11.5)
req._p.addprevious(fig._p)
cap = d.add_paragraph("Figure 4. SIMULATED counterexample (S05 diversion, seed 0): DV-101 diverts about half the "
                      "metered water. Timer-only stops with 5.1 % old water left and flow + volume with 7.0 %, both "
                      "reporting complete; VeriFlush continues to 2.2 %.", style="Figure Caption")
req._p.addprevious(cap._p)
remove(req)
set_text(para("At this evidence-completion stage"),
         "Mechanical assembly is in progress, so no calibrated physical result is reported yet; all quantitative "
         "results here are SIMULATED. The rig uses one small geometry, clean non-potable water, manual valves and "
         "low-cost sensors. It cannot represent all building materials, disinfectants, biofilms, temperatures, "
         "mixing patterns or installation conditions. A manual valve record is weaker than automated position "
         "feedback, temperature may be uninformative, and a flow meter does not independently prove endpoint "
         "arrival. In simulation, a heavier laminar tail than assumed (e.g. β = 0.20) causes false passes unless a "
         "5-volume policy is used. VeriFlush therefore claims event-level hydraulic evidence only, not pathogen "
         "removal, potability, durable microbial control or a water-safety certificate.")
replace(para("Using the European Commission interpretation"),
        " The final selected TRL must match the evidence inserted in the yellow box below.", "")

# ---------------- section 7 ----------------
t7 = table_with("Installed cost")
for r in t7.rows:
    k = r.cells[0].text.strip()
    if k == "Future automated node":
        set_cell(r.cells[1], "AED 1,000–2,500 hardware per branch (ASSUMED, not quoted)")
    if k == "Installed cost":
        set_cell(r.cells[1], "AED 500–1,500 per branch (ASSUMED)")
    if k == "Operating cost":
        set_cell(r.cells[1], "Recalibration and inspection; measured in the pilot")
p = para("Electrical consumption should similarly")
new_para_after(p._p,
               "Indicative economics (ASSUMED order of magnitude, not supplier quotes). In the base hotel scenario "
               "(Table 10), avoided water is worth about 322 m³ × AED 8.80 m⁻³ ≈ AED 2,800 per year before VAT for "
               "300 outlets [28], far less than outlet-level nodes would cost. The business case therefore rests on "
               "compliance evidence, avoided repeat flushing and staff time, and on instrumenting only selected "
               "high-risk low-use branches (Tier 2), not every outlet.")
set_text(para("7.5 Scale scenarios"), "7.4 Scale scenarios")

# ---------------- section 8 ----------------
replace(para("VeriFlush aligns most directly with Theme 3"),
        "Planet and Cooperation are secondary pathways requiring measured avoided demand and an independently "
        "evaluated, shared-schema university–facility pilot—not a claimed transboundary impact [22].",
        "Secondary links are SDG 7 and 13 (every cubic metre of desalinated water not produced avoids its "
        "desalination energy and emissions), SDG 14 (less brine discharged) and, only indirectly, SDG 11 and 3 "
        "through stronger building water-management records, with no health claim. Among the 2026 UN Water "
        "Conference themes [22] it serves Prosperity (efficient use), Planet (avoided demand) and Cooperation (a "
        "shared, auditable flush-event schema).")
t9 = table_with("Share standard event schema")
targets = {"Action": "Pilot target",
           "Verify selected branch flush": "≥ 95 % of events with a complete record",
           "Return Uncertain": "≤ 20 % Uncertain on healthy branches with ≥ 1.5 °C contrast (summer reported "
                               "separately); resolved < 24 h",
           "Stop on evidence": "L per event ≤ the site's timer baseline",
           "Detect sensor/valve faults": "≥ 90 % of scripted faults (simulated: 93 %)",
           "Share standard event schema": "Mapped to ≥ 2 vendor systems"}
for r in t9.rows:
    k = r.cells[0].text.strip()
    if k in targets:
        set_cell(r.cells[4], targets[k])
replace(para("Table 9. UN/SDG contribution logic"), "Table 9. UN/SDG contribution logic with measurable indicators.",
        "Table 9. UN/SDG contribution logic with measurable indicators and pilot targets. Limits: hydraulic evidence "
        "only; Uncertain adds staff work; bench faults may not transfer.")
set_text(para("• Pilot verification at selected low-use branches"),
         "• Dubai Municipality: in the next revision of Technical Guideline 44 [23], accept measured-volume and "
         "endpoint logs as the determination method for system water volume, and pilot verification at selected "
         "low-use branches before broad mandates.")

# ---------------- section 9 ----------------
set_text(para("Digital integration and governance"), "9.1 Digital integration and governance")
set_text(para("Potential models—hardware plus commissioning"),
         "The first model to test is a verification service for hotels and schools that must flush under TG-44 "
         "[23], sold through facility-management contractors and priced per verified branch per year. "
         "It starts with the Tier 0 audit kit (Section 7.3) and adds fixed nodes only on Tier 2 branches; pricing "
         "and ownership of Uncertain events are set in the pilot.")

# ---------------- sections 10 and 11 ----------------
replace(para("Confirmed team identity"),
        " Before submission, the team must name the owner of mechanical assembly, Arduino/electronics, digital "
        "prototype, experimentation, data analysis, report and video, and link each role to a specific output.", "")
set_text(para("The decisive next step is to finish"),
         "The decisive next step is to finish the rig safely, release the minimum calibrations and replay measured "
         "runs through the same frozen engine; the results will show whether endpoint temperature adds value and "
         "how far the system can progress beyond TRL 2–3. Prize funding would buy production-grade flow and valve "
         "hardware and calibration equipment for a two-branch pilot; mentoring from Borouge would target "
         "materials, installation and route to market. A building pilot follows only after independent review "
         "of the laboratory evidence.")

# ---------------- round 2: tense, TRL consistency, trade-offs, derivations ----------------
replace(para("Impact and next step."), "and stops early where fixed times over-flush (MODELLED 322 m³ yr⁻¹ for one "
        "300-room hotel).", "and saves water where site timers over-flush (MODELLED 322 m³ yr⁻¹ for one 300-room "
        "hotel); against a correctly sized bench timer it uses slightly more (0.94 vs 0.82 L per flush) because it "
        "refuses false completions.")
replace(para("Key result (SIMULATED)."), "detected 93 % of injected faults", "flagged 410 of 440 runs with injected "
        "faults (93 %)")
replace(para("The final report will classify every result"), "The final report will classify every result as",
        "Every result is classified as")
replace(para("Uncertainty sources include"), "The report will propagate or bound these where they affect "
        "classification; it will not combine unlike uncertainties into a decorative single number.",
        "These are propagated or bounded where they affect classification; unlike uncertainties are not combined "
        "into a single number.")
t3 = table_with("Practical procedure")
set_cell(t3.rows[0].cells[2], "PREDICTED pre-test value (replaced when measured)")
pred = {"As-built geometry": "Planned 8 m of 8 mm ID silicone. Headline runs use 6 m; in the 8 m sensitivity case "
                             "VeriFlush still gives 0 false passes (timer 40 %, flow + volume 45 %)",
        "Wet volume": "≈ 0.40 L branch (8 m) + 0.04 L upstream",
        "Flow sensor": "≈ 5,900 pulses/L (nominal Hall sensor); healthy branch ≈ 0.63 L/min",
        "Temperature": "Feed ≈ 13 °C (ice packs) vs stagnant ≈ 24 °C: ≈ 11 °C contrast, above the 1.5 °C rule",
        "Pressure and leakage": "Manifold ≈ 3.3 kPa healthy, ≈ 3.2 kPa with bypass open: below the 0–3 bar gauge's "
                                "resolution, so PG-101 is a safety indicator only; leak check before wet runs",
        "Digital system": "Complete: model v1.2.0; firmware replay 13/13 (Section 5.2)"}
for r in t3.rows[1:]:
    k = r.cells[0].text.strip()
    if k in pred:
        set_cell(r.cells[2], pred[k])
replace(para("Table 3. Calibration, integration"), "Table 3. Calibration, integration and evidence-release plan.",
        "Table 3. Calibration plan with PREDICTED pre-test values from the digital twin; each is replaced by the "
        "measured value when the rig run is complete.")
t_cost = table_with("Cost layer")
set_cell(t_cost.rows[0].cells[2], "Evidence basis")
for r in t_cost.rows:
    if r.cells[0].text.strip() == "Prototype total":
        set_cell(r.cells[1], "≈ AED 837 order plus owned items; receipt reconciliation pending")
    if r.cells[0].text.strip() == "Amazon order":
        set_cell(r.cells[1], "≈ AED 837 cart total at ordering (incl. pump, AED 36.99); receipt pending")
replace(para("The team reports an Amazon order"), " The purchased BOM remains a frozen procurement record; the final "
        "report should add only a receipt-supported total, borrowed-item list and actual substitutions, without "
        "retrospectively rewriting what was purchased.", "")
remove(para("The remaining critical path is"))
replace(para("Indicative economics"), "not every outlet.", "not every outlet. Water alone never pays back: the "
        "base case saves about 1.07 m³ (≈ AED 9) per outlet a year. Amortised over 5 years, a node costs AED "
        "400–1,100 per branch a year, so at an ASSUMED AED 50 per staff-hour it must save 8–22 staff-hours per "
        "branch a year (9–25 minutes per weekly flush), plausible only where it replaces attended flushing or "
        "repeat visits; the pilot measures this.")
set_text(para("Using the European Commission interpretation"),
         "Using the European Commission TRL scale [20], the decision logic is at TRL 3 (simulation plus compiled, "
         "replay-matched firmware) and the physical subsystem at TRL 2 while assembly is completed. A calibrated rig "
         "with matched physical replay reaches TRL 4; a supervised shadow-mode branch pilot targets TRL 5–6.")
replace(para("The decisive next step is to finish"), "how far the system can progress beyond TRL 2–3",
        "how quickly the integrated system reaches TRL 4")
replace(para("Table 6. SIMULATED results"), "statistical rate.", "statistical rate. VeriFlush's 281 Uncertain verdicts "
        "include 240 on flushes that had in fact succeeded: the cost of refusing to verify without endpoint "
        "evidence.")
set_text(para("Table 10. MODELLED"),
         "Table 10. MODELLED 300-room hotel: 15/25/35 % of rooms empty × 3/4/5 outlets; fixed flush 2/3/5 min at "
         "6/8/9 L/min. Verified L/event = branch volume (πD²L/4 for 12/6/3 m of 16/15/13 mm pipe) × 5/3/3 volumes × "
         "1.065 simulated overhead.")
replace(para("The recommended impact unit"), "The team will report:", "Pilot indicators are:")
replace(para("The dashboard should present"), "The dashboard should present", "The dashboard presents")
replace(para("The digital prototype should expose"), "The digital prototype should expose", "The digital prototype exposes")
replace(para("Environmental benefit depends on avoiding"), "future public-health outcomes.",
        "future public-health outcomes. The social indicator is staff minutes per event, including Uncertain "
        "follow-up; in the UAE, low use peaks in periods such as summer school closures and low hotel seasons.")

replace(para("Electrical consumption should similarly use"), "Electrical consumption should similarly use",
        "Electrical consumption is estimated similarly from")
replace(para("A first field study should be"), "A first field study should be", "The first field study is")
replace(para("Environmental benefit depends on avoiding"), "The project will therefore report hydraulic, "
        "operational and water-use indicators separately", "Hydraulic, operational and water-use indicators are "
        "therefore reported separately")
for r in t_cost.rows:
    if r.cells[0].text.strip() == "Prototype total":
        set_cell(r.cells[2], "Receipt-supported cash total")
replace(para("VeriFlush aligns most directly with Theme 3"), "with no health claim.",
        "with no health claim. Scaled linearly per room to Dubai's 154,264 hotel rooms [27], the MODELLED saving is about 166,000 "
        "m³ yr⁻¹ (range −3,000 to 614,000), roughly 0.02 % of DEWA's annual desalinated production [15]; the SDG 7, "
        "13 and 14 effects scale with this small volume, so VeriFlush's main value is assurance evidence.")

# ---------------- round 3 (fresh panel) ----------------
replace(para("Key result (SIMULATED)."), "ran 13 normal and fault scenarios 40 times each",
        "ran 2 fault-free and 11 fault scenarios 40 times each")
replace(para("Key result (SIMULATED)."), "flagged 410 of 440 runs with injected faults (93 %)",
        "flagged 410 of the 440 fault-injected runs (93 %)")
replace(para("The physical prototype is a supervised"), "approved test procedure.",
        "approved test procedure. The monitored branch is planned as 8 m of 8 mm ID silicone tubing (≈ 0.40 L). "
        "The two DS18B20 endpoint probes (TT-100 feed, TT-101 endpoint) are not yet fitted; one is being bench-tested, "
        "so endpoint results remain SIMULATED.")
replace(para("The current proof rig intentionally replaces"), "Any component not physically installed must be "
        "described as proposed or digitally demonstrated, never as physically validated.",
        "Components not physically installed are described as proposed or digitally demonstrated.")
replace(para("The digital prototype is the decision and communication layer"), "Physical Arduino data should be "
        "imported wherever available. Synthetic traces may demonstrate missing-sensor, wrong-volume and "
        "communication-fault cases only when they are visibly labelled Simulated and kept separate from measured "
        "performance results.", "Physical Arduino data are imported where available; synthetic traces are visibly "
        "labelled Simulated and kept separate from measured results.")
replace(para("The digital prototype's values were frozen"), " Development trials may tune these values.", "")
for r in t3.rows:
    if r.cells[0].text.strip() == "Temperature":
        set_cell(r.cells[2], "Feed ≈ 13 °C (chilled feed tank) vs stagnant ≈ 24 °C: ≈ 11 °C contrast, above the "
                             "1.5 °C rule (absolute difference, so a warmer feed also works)")
replace(para("Table 6. SIMULATED results"), "Physical results are pending.",
        "Verified coverage = Verified among truly successful flushes. Physical results are pending.")
replace(para("Figure 4. SIMULATED counterexample"), "VeriFlush continues to 2.2 %.",
        "VeriFlush continues to 2.2 %. Across all 40 S05 seeds the medians are 5.2 % (timer, 28 false passes), 7.2 % "
        "(flow + volume, 40) and 2.2 % (VeriFlush, 0); the starkest case is S02 restriction, where the timer leaves "
        "a median 11.5 % in all 40 runs.")
set_text(para("• Permit Uncertain with an escalation path"),
         "• Facility operators and water-safety teams: permit Uncertain with an escalation path, and publish "
         "minimum event, calibration, sensor-health and configuration fields.")
set_text(para("• Require manual override, audit trails"),
         "• BMS and valve vendors: provide manual override, audit trails, device identity and data-retention rules "
         "for connected nodes.")
set_text(para("• Keep water, workflow and water-quality outcomes separate"),
         "• Regulators and operators: keep water, workflow and water-quality outcomes separate, and report litres "
         "per verified event against SDG indicator 6.4.1 (water-use efficiency).")
replace(para("The UAE’s reliance on desalinated potable water"), "accredited microbiological testing.",
        "accredited microbiological testing. The same audit need exists wherever water-management programmes are "
        "expected [13], [24], [25]. The temperature rule uses the absolute feed-to-endpoint difference, but small "
        "summer contrasts in the UAE would raise the Uncertain rate.")
replace(para("Every digital screen") if any(p.text.startswith("Every digital screen") for p in d.paragraphs)
        else para("The dashboard presents these indicators"),
        "Digital screens used in the final report and video must identify whether",
        "Every digital screen in this report and the video states whether")
for r in t_cost.rows:
    if r.cells[0].text.strip() == "Operating cost":
        set_cell(r.cells[1], "≈ AED 100–300 per branch per year for recalibration and inspection (ASSUMED)")
replace(para("The digital prototype exposes"), " Vendor neutrality remains a design objective until demonstrated "
        "with real interfaces.", "")
replace(para("A practical deployment need not instrument every outlet."), "Tier 1 uses existing usage/BMS data",
        "Tier 0, the first product (PROPOSED), is a portable clamp-on flow and surface-temperature kit for "
        "technician audits with no plumbing tie-in; clamp-on accuracy on small-bore, low-flow pipe is untested, so it is first checked against FT-101 on the rig. Tier 1 uses existing usage/BMS data")
replace(para("Table A7. Minimum weekend demonstration matrix") if any(p.text.startswith("Table A7. Minimum")
        for p in d.paragraphs) else para("Table 4. Minimum weekend"), "Minimum weekend demonstration",
        "Minimum demonstration")
t8 = table_with("Monitored outlets")
for row in t8.rows:
    trPr = row._tr.get_or_add_trPr()
    if trPr.find(qn("w:cantSplit")) is None:
        trPr.append(trPr.makeelement(qn("w:cantSplit"), {}))
    for c in row.cells:
        for cp in c.paragraphs:
            cp.paragraph_format.keep_with_next = True
para("Table 10. MODELLED").paragraph_format.keep_with_next = True
replace(para("Table 9. UN/SDG contribution logic"), "Limits: hydraulic evidence only;",
        "Baselines come from site timer logs, BMS or maintenance-management records and operator timesheets. "
        "Limits: hydraulic evidence only;")

# labelled design figure
from PIL import Image, ImageDraw, ImageFont
im = Image.open(ROOT / "3d/renders/S01_healthy_wide_t22.png").convert("RGB")
dr = ImageDraw.Draw(im)
font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 34)
tags = [("TK-101 feed tank", (130, 560), (30, 330)),
        ("P-101 pump", (405, 690), (250, 770)),
        ("PG-101 gauge", (552, 545), (420, 420)),
        ("Manual valves", (712, 500), (640, 330)),
        ("FT-101 flow sensor", (858, 618), (800, 700)),
        ("Branch coil (planned 8 m × 8 mm ID, ≈ 0.40 L)", (1200, 520), (1000, 640)),
        ("TK-102", (1290, 250), (1420, 120)),
        ("TK-103 outlet", (1720, 440), (1620, 600)),
        ("Arduino Uno R3", (700, 830), (840, 900))]
for text, target, (x, y) in tags:
    w, h = dr.textbbox((0, 0), text, font=font)[2:]
    box = (x - 10, y - 6, x + w + 10, y + h + 10)
    cx = min(max(target[0], box[0]), box[2])
    cy = box[1] if target[1] < box[1] else box[3]
    dr.line([target, (cx, cy)], fill=(31, 58, 95), width=4)
    dr.ellipse([target[0] - 7, target[1] - 7, target[0] + 7, target[1] + 7], fill=(31, 58, 95))
    dr.rectangle(box, fill=(255, 255, 255), outline=(31, 58, 95), width=3)
    dr.text((x, y), text, fill=(31, 58, 95), font=font)
lab = ROOT / "report_assets" / "_rig_design_labelled.png"
im.save(lab)
fig2 = para("Figure 2. Design model of the proof rig")._p.getprevious()
img2 = image_para(lab, 13.0)
fig2.addprevious(img2._p)
fig2.getparent().remove(fig2)

# appendix: drop process artefacts, renumber tables in order
remove(para("TEAM INPUT REQUIRED - Replace this box with the final operating flowchart"))
remove(para("Figure A1. Final physical-to-digital operating flowchart"))
cap = para("Table A2. Deadline-driven critical path")
tbl = cap._p.getnext()
while tbl.tag != qn("w:tbl"):
    tbl = tbl.getnext()
tbl.getparent().remove(tbl)
remove(cap)
apd = para("Appendix D — Submission data still required")
el = apd._p.getnext()
while el is not None and "".join(t.text or "" for t in el.iter(qn("w:t"))).startswith("•"):
    nxt = el.getnext()
    el.getparent().remove(el)
    el = nxt
remove(apd)
set_text(para("Appendix E — Final evidence and submission audit"), "Appendix D — Final evidence and submission audit")
qa = table_with("Current draft status")
for tr in qa._tbl.tr_lst:
    tr.remove(tr.tc_lst[2])
grid = qa._tbl.tblGrid
grid.remove(grid.gridCol_lst[2])
remove(para("Evidence-completion status:"))
order = [p for p in d.paragraphs if re.match(r"Table A\d+\.", p.text.strip())]
amap = {re.match(r"Table (A\d+)\.", p.text.strip()).group(1): f"A{i + 1}" for i, p in enumerate(order)}
for p in order:
    old = re.match(r"Table (A\d+)\.", p.text.strip()).group(1)
    replace(p, f"Table {old}.", f"Table {amap[old]}.")
replace(para("The minimum evidence set is three"), "(Tables A7–A8)", f"(Tables {amap['A7']}–{amap['A8']})")

replace(para("Generative-AI disclosure:"), "AI tools supported literature discovery, document structuring, drafting, "
        "editing, diagram generation and code/calculation planning.",
        "Claude (Anthropic) was used through claude.ai for project explanation, the parts list and compatibility "
        "checks, wiring diagrams, Arduino test sketches and a build manual, and through Claude Code for the "
        "digital-prototype simulation, firmware, EPANET and 3D models, report drafting and editing, and rubric-based "
        "review. Another AI tool was used once to critique the parts list.")

# ---------------- renumber main-text tables (old 4, 5 moved to the appendix) ----------------
remap = {6: 4, 7: 5, 8: 6, 9: 7, 10: 8, 11: 9}
pat = re.compile(r"\bTable (\d+)\b")


def renum(text):
    return pat.sub(lambda m: f"Table {remap.get(int(m.group(1)), int(m.group(1)))}", text)


def renum_par(p):
    if not pat.search(p.text):
        return
    if all(not pat.search(r.text) for r in p.runs):
        set_text(p, renum(p.text))
    for r in p.runs:
        r.text = renum(r.text)


for p in d.paragraphs:
    renum_par(p)
for t in d.tables:
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                renum_par(p)

# roadmap figure follows the new Figure 4
replace(para("Figure 4. Proposed 12–36 month"), "Figure 4.", "Figure 5.")

d.save(DST)
print("saved", DST)
