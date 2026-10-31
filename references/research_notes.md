# VeriFlush: research notes (references and parameter evidence)

Compiled 30 Oct 2026 for KU–UNESCO Water Hackathon 2026, Theme 3.

Verification legend:
- **Opened: yes (full text)**: I read the relevant passage in the document myself.
- **Opened: yes (metadata/abstract)**: I confirmed title, authors, venue, year and DOI (Crossref API, publisher or repository page), and read the abstract only.
- **Seen in search results only**: details came from a search snippet; the source itself was not opened.
- **NOT VERIFIED**: I could not confirm it. Do not cite it as fact without checking.

Paraphrases are mine. Numbers are as printed in the source.

Rig numbers used below (my own arithmetic, not from any source): ID 8 mm, so the cross-section is 5.03e-5 m². The 6 m tube volume is 0.302 L, so the mean residence time tau is about 30 s at 0.6 L/min. The mean velocity is 0.20 m/s, which gives Re of about 1590 at nu = 1.0e-6 m²/s. With a coil diameter of 0.30 m, sqrt(d/Dc) = 0.163, so the Dean number Dn = Re * sqrt(d/Dc) is about 260.

---

## A. Transport and residence-time distribution (RTD)

### A1. Laminar segregated-flow RTD in a straight tube

[1] N. Kockmann, "Entwurf und Betrieb eines Rohrreaktors mit enger Verweilzeitverteilung" (Design and operation of a tubular reactor with narrow residence time distribution), *Chem. Ing. Tech.*, vol. 92, no. 6, pp. 685–691, 2020, doi: 10.1002/cite.202000028. (Open access.)
- URL: https://doi.org/10.1002/cite.202000028 (PDF via TU Dortmund Eldorado repository)
- Opened: yes (full text, German, extracted from the PDF).
- Supports:
  - Eq. (8) gives the cumulative RTD for laminar flow in a straight tube without molecular diffusion as F(theta) = 1 − 1/(4 theta²), with theta = t/tau. The paper attributes it to the textbook Baerns et al., *Technische Chemie*, 2nd ed., 2013, ch. 6. **Use this as the citable source for the formula.**
  - Fig. 2 compares the ideal laminar straight-tube F-curve with measured F-curves for a helical coil and for coiled flow inverters (CFIs). See A3 for the numbers.
  - The abstract (English) says axial dispersion in laminar flow in a straight tube is very high and gives a wide RTD, and that secondary flows in curved tubes improve radial mixing.

[2] P. V. Danckwerts, "Continuous flow systems: Distribution of residence times," *Chem. Eng. Sci.*, vol. 2, no. 1, pp. 1–13, 1953, doi: 10.1016/0009-2509(53)80001-1.
- Opened: yes (metadata via Crossref). Full text not opened.
- Supports: the foundational definitions of E(t) and F(t) from tracer pulse and step responses. This is seen in secondary descriptions only. I did **not** confirm that this paper contains the 1 − 1/(4 theta²) result; cite [1] or [3] for the formula.

[3] O. Levenspiel, *Chemical Reaction Engineering*, 3rd ed. New York, NY, USA: Wiley, 1999, ch. 11.
- Opened: NO. The book was not opened. The bibliographic details come from reference [5] of [1], which cites it for the Taylor–Aris dispersion relation. Page and equation numbers are NOT VERIFIED.
- Use it as the standard textbook for the dispersion model, the tanks-in-series model and laminar-flow RTD, citing chapters only.

### A2. Taylor dispersion and its validity condition

[4] G. I. Taylor, "Dispersion of soluble matter in solvent flowing slowly through a tube," *Proc. R. Soc. Lond. A*, vol. 219, no. 1137, pp. 186–203, 1953, doi: 10.1098/rspa.1953.0139.
- Opened: yes (metadata and abstract via Crossref). The PDF I downloaded was an image scan with no text layer, so I could **not** read the validity inequality in the original.
- Supports (from the abstract): a solute slug in slow laminar tube flow eventually spreads symmetrically about a point moving at the mean speed, and the spreading is described by an effective diffusion coefficient tied to molecular diffusivity.
- From [1] (full text): the Taylor–Aris form 1/Pe_ax = 1/(Re·Sc) + Re·Sc/192 is valid for Bo > 200 (citing Levenspiel). [1] also states that for low-viscosity liquids the molecular diffusivity is about 1e-9 m²/s and Sc is about 1000.
- Validity condition t >> R²/D: this is the standard statement of Taylor's long-time limit. It is **NOT VERIFIED in the original text** (scan unreadable), so cite it as "Taylor [4]; see also [3]".
- Argument for VeriFlush (my arithmetic): with R = 4 mm and D ≈ 1e-9 m²/s [1], R²/D ≈ 1.6e4 s, about 4.4 h. Since tau ≈ 30 s, tau/(R²/D) ≈ 0.002, far below 1. The straight-tube limit is therefore convective (segregated, diffusion-free), not Taylor-dispersed. The NaCl diffusivity is about 1.5e-9 m²/s, which is ASSUMED and does not change the conclusion.

### A3. RTD and axial dispersion in helically coiled tubes (Dean vortices)

[5] D. M. Ruthven, "The residence time distribution for ideal laminar flow in a helical tube," *Chem. Eng. Sci.*, vol. 26, pp. 1113–1121, 1971, doi: 10.1016/0009-2509(71)80025-8.
- Opened: yes (metadata via Crossref). No abstract or results seen, so no quantitative claim is taken from it.

[6] R. N. Trivedi and K. Vasudeva, "RTD for diffusion free laminar flow in helical coils," *Chem. Eng. Sci.*, vol. 29, pp. 2291–2295, 1974, doi: 10.1016/0009-2509(74)80005-9.
- Opened: yes (metadata via Crossref). No results seen.

[7] R. N. Trivedi and K. Vasudeva, "Axial dispersion in laminar flow in helical coils," *Chem. Eng. Sci.*, vol. 30, pp. 317–325, 1975, doi: 10.1016/0009-2509(75)80081-9.
- Opened: yes (metadata via Crossref). No results seen.

[8] E. B. Nauman, "The residence time distribution for laminar flow in helically coiled tubes," *Chem. Eng. Sci.*, vol. 32, pp. 287–293, 1977, doi: 10.1016/0009-2509(77)80207-8.
- Opened: yes (metadata via Crossref). A 2025 *Chem. Eng. Sci.* paper by Wörner, seen in search results only, says Nauman obtained an approximate diffusion-free RTD for helical coils. Its numerical form is NOT VERIFIED.

[9] A. K. Saxena and K. D. P. Nigam, "Coiled configuration for flow inversion and its effect on residence time distribution," *AIChE J.*, vol. 30, no. 3, pp. 363–368, 1984.
- Opened: NO. Bibliographic details seen in the reference lists of [1] and [11]. DOI NOT VERIFIED.
- Supports: introduces the coiled flow inverter (CFI), per [11].

[10] S. Klutz, S. K. Kurt, M. Lobedann, and N. Kockmann, "Narrow residence time distribution in tubular reactor concept for Reynolds number range of 10–100," *Chem. Eng. Res. Des.*, vol. 95, pp. 22–33, 2015, doi: 10.1016/j.cherd.2015.01.003.
- Opened: yes (metadata via Crossref). The data is seen in full text as reproduced in Fig. 2 of [1].
- Supports (via [1], Fig. 2): water at Re = 24 in coils of 3 mm ID, fitted Bodenstein numbers:
  - straight helical coil: Bo = 80 (tau ≈ 23 min)
  - CFI with 15 bends: Bo = 302 (tau ≈ 87 min)
  - CFI with 27 bends: Bo = 549 (tau ≈ 157 min)
  - Every coiled device gives a far narrower RTD than the laminar straight tube.
- [1] also gives the design window for a narrow RTD in CFIs: Dn > 3 and modified torsion number T* > 1000. It recommends a coil diameter of at least 15 times the tube ID (the VeriFlush ratio is 300/8, about 37, which satisfies this). [1] adds that a large coil pitch displaces and eventually suppresses the Dean vortices, which widens the RTD again.

[11] G. Valitov, D. Rossi, C. Price, A. Gavriilidis, and L. Mazzei, "Axial dispersion in curved channels in the presence of pulsating flow," *Chem. Eng. Process. – Process Intensif.*, vol. 180, Art. no. 108629, 2022, doi: 10.1016/j.cep.2021.108629.
- Opened: yes (full text, UCL Discovery author version).
- Supports:
  - In the introduction, steady-state studies show helically coiled tubes reduce axial dispersion compared with straight tubes, and CFIs reduce it further.
  - A helical coil has two dead zones at the centres of the Dean vortices.
  - Dean vortices develop fully within the first coil turn.
  - Their experiments (1 mm ID, 5 m long, Re = 21, Dn = 5) are at much lower Dean number than VeriFlush, so their dispersion numbers are **not transferable**.

**Quantitative gap:** I found no opened source giving N or Pe for Dn ≈ 200–300 with a short residence time (tau ≈ 30 s), Sc ≈ 1000 and L/d ≈ 750, which is the VeriFlush regime. Bo = 80 from [10] is a Taylor-regime result at long tau and should not be copied over. In the VeriFlush regime the relevant limit is the diffusion-free coil RTD of [5]–[8]: Dean vortices still redistribute fluid across the section convectively, so the RTD is narrower than 1 − 1/(4 theta²) even without diffusion. Treat N as a fitted or swept parameter (see Recommended values).

### A4. Tanks-in-series and mobile–immobile (two-region) models

- Tanks-in-series and axial-dispersion models: cite [3], chapters 13–14 (chapter numbers NOT VERIFIED; [1] cites only ch. 11 for dispersion). Standard relations, which I am inferring and did not check against the text:
  - tanks-in-series variance: sigma²_theta = 1/N
  - large-Bo dispersion model: sigma²_theta ≈ 2/Bo, so N ≈ Bo/2
- [1] (full text) states that for Bo > 100 the step response is the two-parameter Gaussian error-function solution, F = ½[1 − erf(...)] (Eq. 13).

[12] M. Th. van Genuchten and P. J. Wierenga, "Mass transfer studies in sorbing porous media I. Analytical solutions," *Soil Sci. Soc. Am. J.*, vol. 40, no. 4, pp. 473–480, 1976, doi: 10.2136/sssaj1976.03615995004000040011x.
- Opened: yes (metadata via Crossref). The issue number comes from the DOI string; Crossref did not return it.
- Supports: the mobile–immobile (two-region) advection–dispersion model form, with first-order exchange between mobile and stagnant water. The model content is from my own knowledge, not read here. Cite it for the model form only.

### A5. Network models: EPANET, EPANET-MSX, WNTR

[13] L. A. Rossman, H. Woo, M. Tryby, F. Shang, R. Janke, and T. Haxton, "EPANET 2.2 User Manual," U.S. EPA, Cincinnati, OH, USA, Rep. EPA/600/R-20/133, 2020.
- URL: https://epanet22.readthedocs.io (web version); EPA PDF at https://www.epa.gov/water-research/epanet
- Seen in search results only for the authors and report number. The PDF was not opened; the readthedocs chapter URLs returned 404.

[14] F. Shang, L. A. Rossman, and J. G. Uber, "EPANET-MSX 2.0 Multi-Species Extension User's Manual," U.S. EPA, 2023.
- URL: https://epanetmsx2manual.readthedocs.io/en/latest/1_introduction.html
- Opened: yes (introduction chapter). The title, author list and report number are NOT VERIFIED on the page I opened; the authors come from search results.
- Supports:
  - The introduction states that longitudinal dispersion is not modelled in EPANET, and that EPANET and the original MSX are advection–reaction only.
  - MSX 2.0 solves 1-D advection–dispersion–reaction equations and adds dispersion as an option.
- This supports the claim that standard EPANET water-age and quality runs are plug-flow and cannot represent the laminar-tail RTD of a short, stagnant branch.

[15] K. A. Klise, M. Bynum, D. Moriarty, and R. Murray, "A software framework for assessing the resilience of drinking water systems to disasters with an example earthquake case study," *Environ. Model. Softw.*, vol. 95, pp. 420–431, 2017, doi: 10.1016/j.envsoft.2017.06.022.
- Seen in search results only (Sandia publication page and the WNTR citation list). Supports that WNTR is an open-source Python package built on EPANET.
- Alternative citation: K. A. Klise, R. Murray, and T. Haxton, "An overview of the Water Network Tool for Resilience (WNTR)," in *Proc. 1st Int. WDSA/CCWI Joint Conf.*, Kingston, ON, Canada, 2018. Seen in search results only.

---

## B. Sensor realism

### B6. DS18B20 digital thermometer

[16] Dallas Semiconductor, "DS18B20 Programmable Resolution 1-Wire Digital Thermometer," datasheet (preliminary). Mirror: https://cdn.sparkfun.com/datasheets/Sensors/Temp/DS18B20.pdf
- Opened: yes (full text). This is the old Dallas preliminary revision. The current Analog Devices (Maxim) datasheet at https://www.analog.com/media/en/technical-documentation/data-sheets/DS18B20.pdf timed out twice, so its revision letter and date are NOT VERIFIED. The specs below are unchanged in later revisions to my knowledge, but cite the ADI version if you can open it.
- Supports:
  - ±0.5 °C error from −10 to +85 °C; ±2 °C over −55 to +125 °C (DC characteristics table).
  - Selectable resolution of 9–12 bits, corresponding to 0.5, 0.25, 0.125 or 0.0625 °C.
  - Maximum conversion time 93.75 ms at 9 bit and 750 ms at 12 bit.
  - The power-on reset value of the temperature register is +85 °C. A reading of exactly 85.0 at start-up should be treated as "not converted yet".
  - Supply 3.0–5.5 V.

[17] M. Burton et al., "Arduino-Temperature-Control-Library," DallasTemperature.h, v4.0.5, GitHub. URL: https://github.com/milesburton/Arduino-Temperature-Control-Library
- Opened: yes (raw header file on the master branch).
- Supports: DEVICE_DISCONNECTED_C = −127, DEVICE_DISCONNECTED_F = −196.6 and DEVICE_DISCONNECTED_RAW = −7040, listed under "Error Codes". **−127 °C is a library sentinel, not a datasheet value.**

### B7. Time constant of a stainless-steel-sheathed DS18B20 probe in water

[18] J. E. M. Perea Martins, "Physical analysis of a waterproof temperature sensor responsiveness for agricultural applications," *J. Agric. Informatics*, vol. 13, no. 2, pp. 7–13 (approx.), 2022, doi: 10.17700/jai.2022.13.2.623.
- URL: https://real.mtak.hu/197184/1/document%20%2867%29.pdf
- Opened: yes (full text). The page range is inferred from the PDF page footers and is NOT VERIFIED.
- Supports:
  - Method: a waterproof DS18B20 probe was plunged between two insulated cups of still water at different temperatures, sampled at 1 s and 12-bit resolution, 10 repetitions each.
  - Time constant (63.2 %): heating mean 6.20 s (SD 0.41, max 7.0); cooling mean 6.90 s (SD 0.47, max 7.5).
  - Comparison: a mercury-in-glass thermometer is about 10 s. The author notes the stainless sheath increases the time constant.

[19] "DS18B20 thermo sensor," MultiFlexMeter project wiki (user "goossenzeeland"), updated 10 Apr 2021. URL: https://multiflexmeter.atlassian.net/wiki/spaces/MFM/pages/1219690497/DS18B20+thermo+sensor
- Opened: yes. This is an informal source.
- Supports: transition times in water for stainless DS18B20 probes. A 20 °C step took 137 s (cooling) and 70 s (heating); a 1.8 °C step took 49 s and 21 s. These are settling times with no stated criterion, not time constants; they are consistent with tau of a few seconds plus a long tail.
- Note: in a flowing pipe at 0.2 m/s the convective coefficient is higher than in a still cup, so tau ≈ 6–7 s is a conservative (slow) upper estimate. The in-flow value is ASSUMED to be about 3–7 s.

### B8. YF-S401 Hall-effect flow sensor

[20] DFRobot, "Gravity: Digital Water Flow Sensor (SEN0216, YF-S401)," product wiki. URL: https://wiki.dfrobot.com/SEN0216
- Opened: yes.
- Supports:
  - Range 0.3–6 L/min.
  - Accuracy ±5 % over 0.3–3 L/min only.
  - 1 L = 5880 pulses, which implies F ≈ 98·Q Hz with Q in L/min (my derivation).
  - 5–12 V, 15 mA at 5 V; proof pressure < 0.8 MPa.
  - No statement on behaviour below 0.3 L/min.

[21] TinyTronics, "YF-S401 water flow sensor," product page. URL: https://www.tinytronics.nl/shop/en/sensors/liquid/yf-s401-water-flow-sensor
- Opened: yes.
- Supports:
  - About 98 pulses/s per L/min (Q = f/98), 50 % ± 10 % duty cycle.
  - Range 0.3–6 L/min with ±10 % accuracy.
  - 5–24 V, max 8 bar, −25 to 80 °C.
- Conflicts: one vendor (Electrokit, seen in search results only) lists F = 43·Q next to 5880 pulses/L, which is inconsistent. Use 5880 pulses/L and calibrate on the rig.
- Low-flow behaviour: no source specifies it below 0.3 L/min. The rig minimum (0.3 L/min, about 29 Hz) sits exactly at the bottom of the specified range. ASSUMED: treat Q < 0.3 L/min as unreliable or under-reading, with possible stall to 0 Hz.

### B9. MG996R servo

[22] "MG996R High Torque Metal Gear Dual Ball Bearing Servo," spec sheet (no manufacturer revision or date printed; commonly attributed to Tower Pro). Copy hosted by Cornell ECE: https://courses.ece.cornell.edu/ece5990/ECE5725_Spring2020_Projects/May_15_Demo/Smart%20Lock/W_pp445_yl656/datasheet/MG996R_Tower-Pro.pdf
- Opened: yes (full text).
- Supports:
  - Operating speed 0.17 s/60° at 4.8 V and 0.14 s/60° at 6 V.
  - Stall torque 9.4 kgf·cm at 4.8 V and 11 kgf·cm at 6 V.
  - Supply 4.8–7.2 V; running current 500–900 mA at 6 V; stall current 2.5 A at 6 V.
  - Dead band 5 µs; travel about 120°; operating temperature 0–55 °C.
- Conflict: several retailer pages (seen in search results only) list 0.19 s/60° at 4.8 V and 0.15 s/60° at 6 V. A 90° quarter-turn valve then takes roughly 0.21–0.29 s unloaded, more under valve torque (my arithmetic).

---

## C. Report evidence

### C10. Proctor et al. 2020

[23] C. R. Proctor, W. J. Rhoads, T. Keane, M. Salehi, K. Hamilton, K. J. Pieper, D. M. Cwiertny, M. Prévost, and A. J. Whelton, "Considerations for large building water quality after extended stagnation," *AWWA Water Sci.*, vol. 2, no. 4, Art. no. e1186, 2020, doi: 10.1002/aws2.1186.
- Opened: yes (metadata and abstract via Crossref; full text via Europe PMC, PMC7323006).
- Supports:
  - Flushing duration is very hard to generalise. Volume estimates or diagnostic testing (disinfectant residual and/or temperature) can help decide how much water to flush at each outlet.
  - Temperature stabilisation (< 0.1 °C change, citing EPA Region 4, 2019) is easy to measure and may indicate water is now coming from the distribution main. **But the paper warns that in hot climates in summer the water will not get cold.** This matters for the UAE and justifies VeriFlush using feed-vs-endpoint temperature, not an absolute threshold.
  - Disinfectant residual is unlikely to survive water heaters, so temperature is the flushing diagnostic for hot systems.
  - Building water management plans often include weekly flushing of unused or unoccupied outlets, but the criteria for its efficacy have not been thoroughly documented. **This is the key gap VeriFlush addresses.**
  - Example: more than 80 min of flushing was needed to obtain a residual at distal outlets in one green healthcare building (citing Rhoads et al.).

### C11. Dubai Municipality Legionella guideline

[24] Dubai Municipality, Health & Safety Dept. (Environmental Health Section), "Technical Guidelines for Legionella Control in Water System," Doc. DM-HSD-GU44-LCWS2, Version 6, 19 Aug. 2025 (supersedes 17 Dec. 2024). URL: https://dmpmedia.dm.gov.ae/uploads/2022/10/DM-HSD-GU44-LCWS2_Technical-Guidelines-for-Legionella-Control-in-Water-System_V6-002.pdf
- Opened: yes (full text, 42 pp.).
- Supports (Sec. 12-1 "Regular Maintenance Procedures", p. 19 of 42):
  - Premises must have a flushing policy and run all taps and showers in guest rooms for several minutes, at least once a week if rooms are unoccupied, and always before occupation.
  - All dead legs should be removed or disconnected.
  - Hot water must be kept at 50–60 °C and cold water below 20 °C.
  - The system must be flushed at least every six months with water at ≥ 70 °C for 5 min, or chlorinated to give 1–2 mg/L free chlorine at all outlets.
- The guideline defines the requirement in time ("several minutes") with no verification criterion.

### C12. HSE HSG274 Part 2

[25] Health and Safety Executive, *Legionnaires' disease: Technical guidance. Part 2: The control of legionella bacteria in hot and cold water systems*, HSG274 Part 2. London, U.K.: TSO, 2024. URL: https://www.hse.gov.uk/pubns/priced/hsg274part2.pdf (index: https://www.hse.gov.uk/pubns/books/hsg274.htm)
- Opened: yes (full text). The cover says "Published 2024". The HSE index page labels the series "second edition, March 2024" but says only Part 1 was reviewed and updated.
- Supports:
  - Para. 2.78: when outlets are not in regular use, weekly flushing for several minutes can significantly reduce Legionella risk. Once started, flushing must be sustained and logged. Healthcare settings may need more frequent flushing.
  - Para. 2.47: weekly flushing keeps temperatures below 20 °C and maintains residual chemical treatment.
  - Checklist table ("Infrequently used outlets", weekly or per risk assessment): flush outlets until the outlet temperature stabilises and is comparable to the supply water. **This directly supports VeriFlush's endpoint-vs-feed temperature convergence criterion.** Equipment unused for seven days or more counts as infrequently used.

### C13. CDC Legionella Water Management Program toolkit

[26] U.S. Centers for Disease Control and Prevention, "Toolkit: Developing a Legionella Water Management Program," web page, 15 Mar. 2024. URL: https://www.cdc.gov/control-legionella/php/toolkit/wmp-toolkit.html
- Opened: yes (web page only; the page shows the date 15 Mar 2024). The linked PDF (https://www.cdc.gov/control-legionella/media/pdfs/toolkit.pdf) returned "Access Denied" or exceeded the size limit.
- A search result says the PDF is labelled "Version 1.2, September 30, 2025". This is NOT VERIFIED (seen in search results only).
- Older version: "Developing a water management program to reduce Legionella growth & spread in buildings: a practical guide to implementing industry standards, Version 1.1," NCIRD/NCEH, 5 Jun. 2017, iii + 31 pp. Opened: yes (CDC Stacks record https://stacks.cdc.gov/view/cdc/46266, metadata only).
- Supports: Legionella water management programs are an industry standard for large US buildings (references ASHRAE 188). Statements about control limits and validation vs verification are NOT VERIFIED (PDF not opened).

### C14. UAE per-capita water use

[27] UAE Government Portal, "The UAE Water Security Strategy 2036." URL: https://u.ae/en/about-the-uae/strategies-initiatives-and-awards/strategies-plans-and-visions/environment-and-energy/the-uae-water-security-strategy-2036
- Opened: yes.
- Supports these targets: reduce total water demand by 21 %; raise the water productivity index to USD 110/m³; raise reuse of treated water to 95 %. The page, as I read it, did **not** state a per-capita baseline.

[28] "Energy ministry unveils national water strategy," *Gulf News*, Sep. 2017 (last updated 15 Sep. 2018). URL: https://gulfnews.com/uae/environment/energy-ministry-unveils-national-water-strategy-1.2097151
- Opened: yes.
- Supports:
  - Minister Suhail Al Mazrouei states the strategy aims to reduce average per-capita consumption by half.
  - Other targets: −21 % demand, 95 % reuse, two days of national storage.
  - Emergency supply of 91 L/person/day, and 30 L/person/day in extreme emergencies.
  - No per-capita baseline is given.

Per-capita baseline:
- The figure of about 550 L/person/day appears in a u.ae case study ("Clean Water and Sanitation", CS16), which attributes it to the MOCCAE *State of Environment Report 2015*. Seen in search results only; the u.ae PDF returned 404.
- The same figure appears in *Khaleej Times* (2016) and is attributed to EAD for Abu Dhabi. Seen in search results only.
- **No better official per-capita figure was verified.** Statistics Centre Abu Dhabi and DEWA statistics booklets were not opened. A Dubai figure of 546 → 430 L/day by 2030 appeared in a search summary, but the cited Oxford Business Group page did **not** contain it, so it is NOT VERIFIED.
- Recommended framing: "about 550 L/capita/day (MOCCAE 2015, as reported by the UAE Government Portal); national target to halve per-capita use by 2036 [27], [28]".

### C15. Water used by building flushing; fixture flow rates

[29] M. Salehi, D. DeSimone, K. Aghilinasrollahabadi, and T. Ahamed, "A case study on tap water quality in large buildings recommissioned after extended closure due to the COVID-19 pandemic," *Environ. Sci.: Water Res. Technol.*, vol. 7, no. 11, pp. 1996–2009, 2021, doi: 10.1039/D1EW00428J.
- Opened: yes (metadata via Crossref; abstract via NSF PAR https://par.nsf.gov/biblio/10380648).
- Supports:
  - Ten university buildings were flushed using volume-based and constant-duration protocols, using more than 14 m³ of water in total (about 1.4 m³ per building, my arithmetic).
  - At the point of entry, total chlorine rose from 0.6 to 1.1 mg/L.
  - Median fixture chlorine rose from < 0.1 to 1.0 mg/L (academic buildings) and from < 0.1 to 0.75 mg/L (athletic buildings).
  - Chlorine was absent in 69–71 % of fixture samples during stagnation.
- Also use [23] for ">80 min of flushing to reach residual at distal outlets".

Fixture flow rates:
- UAE (ESMA) Water Efficiency Label: *Gulf News*, "Low water flow in new buildings to save 60% water" (about 2015). URL: https://gulfnews.com/uae/environment/low-water-flow-in-new-buildings-to-save-60-water-1.1460636. Seen in search results only. The example given is ordinary fixtures at about 12 L/min dropping to about 5 L/min with water-saving fixtures.
- Estidama and Al Sa'fat numeric fixture limits: NOT VERIFIED (technical manuals not opened).
- For a water-saving estimate, ASSUMED: a hotel basin tap at 6 L/min and a shower at 9 L/min. Replace with the Al Sa'fat or Estidama manual values if obtained.

### C16. UN SDG 6

[30] United Nations, "Goal 6: Clean Water and Sanitation," Sustainable Development Goals. URL: https://www.un.org/sustainabledevelopment/water-and-sanitation/
- Opened: yes.
- Supports:
  - Target 6.1: by 2030, universal and equitable access to safe and affordable drinking water for all.
  - Target 6.4: by 2030, substantially increase water-use efficiency across all sectors and ensure sustainable withdrawals.
- VeriFlush maps to 6.1 (safe water at the tap) and 6.4 (no over-flushing).

---

## Recommended values

| Parameter | Value | Source / status |
|---|---|---|
| Coil RTD: tanks-in-series N (equivalently Bo ≈ 2N) | Baseline N = 10; sweep 3–40. Lower bound is the straight laminar tube (F = 1 − 1/(4 theta²), first arrival at theta = 0.5) [1]. Upper reference is Bo = 80 (N ≈ 40) for a helical coil at Re = 24 [10] via [1], which is a long-tau Taylor regime and probably an overestimate for tau ≈ 30 s. | **ASSUMED** for Dn ≈ 260. No opened source at this Dn and tau. Fit N to the saline-tracer truth data. |
| Straight-tube regime check | tau/(R²/D) ≈ 0.002, so convective (segregated), not Taylor | Arithmetic with D ≈ 1e-9 m²/s [1]; Taylor condition [4] not verified in original text |
| DS18B20 probe time constant (63 %) | 6–7 s in still water (6.2 heating / 6.9 cooling); use tau = 5 s nominal in flowing water, sweep 3–8 s | [18] measured (still water); in-flow value **ASSUMED** |
| DS18B20 accuracy / resolution / conversion | ±0.5 °C (−10 to +85 °C); 0.0625 °C; 750 ms at 12 bit; 85.0 = power-on reset; −127 = library "disconnected" | [16], [17] |
| Flow sensor low-flow limit | Specified 0.3–6 L/min; ±5 % (0.3–3 L/min) [20] or ±10 % [21]; treat < 0.3 L/min as unreliable; K = 5880 pulses/L (98 Hz per L/min) | [20], [21]; behaviour below 0.3 L/min **ASSUMED** |
| MG996R speed | 0.17 s/60° at 4.8 V; 0.14 s/60° at 6 V, so about 0.21–0.26 s per 90° unloaded; model valve travel at 0.3–0.5 s with load | [22]; loaded time **ASSUMED** |
| UAE per-capita use | About 550 L/person/day (MOCCAE 2015 via u.ae, unopened); national target is −50 % per capita and −21 % total demand by 2036 | Target verified [27], [28]; baseline seen in search results only |
| Flushing practice | Weekly, "several minutes", until outlet temperature stabilises and matches supply; cold water < 20 °C | [24], [25], [23] |
