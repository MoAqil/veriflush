# References (IEEE)

**How to read this list:**
- Numbers are shared by all documents in this folder. `software_comparison.md` keeps its own local list, cross-referenced at the end.
- **Status** records how the source was checked on 30 Oct 2026. Details are in [research_notes.md](research_notes.md).
  - **FULL**: the passage supporting the claim was read in the source.
  - **META**: title, authors, venue, year and DOI were confirmed on Crossref or the publisher page, and the abstract was read. No claim beyond the abstract is taken from it.
  - **NOT OPENED**: real, and cited elsewhere, but not opened by us. **Do not use it in the report for any specific claim** until a team member opens it.

## Transport, residence time and network models

[1] N. Kockmann, "Entwurf und Betrieb eines Rohrreaktors mit enger Verweilzeitverteilung," *Chem. Ing. Tech.*, vol. 92, no. 6, pp. 685–691, 2020, doi: 10.1002/cite.202000028.
- **FULL.**
- Laminar straight-tube F(θ) = 1 − 1/(4θ²) (Eq. 8).
- Coiled tubes narrow the residence-time distribution (RTD).
- Taylor–Aris validity.
- D ≈ 10⁻⁹ m²/s for liquids.

[2] P. V. Danckwerts, "Continuous flow systems: Distribution of residence times," *Chem. Eng. Sci.*, vol. 2, no. 1, pp. 1–13, 1953, doi: 10.1016/0009-2509(53)80001-1.
- **META.**
- Used only for the RTD definitions E(t), F(t).

[3] O. Levenspiel, *Chemical Reaction Engineering*, 3rd ed. New York, NY, USA: Wiley, 1999.
- **NOT OPENED.**
- Standard textbook for tanks-in-series and the dispersion model.

[4] G. I. Taylor, "Dispersion of soluble matter in solvent flowing slowly through a tube," *Proc. R. Soc. Lond. A*, vol. 219, no. 1137, pp. 186–203, 1953, doi: 10.1098/rspa.1953.0139.
- **META.**
- Taylor dispersion as a long-time effective diffusion. The t ≫ R²/D condition is taken via [1].

[5] D. M. Ruthven, "The residence time distribution for ideal laminar flow in a helical tube," *Chem. Eng. Sci.*, vol. 26, pp. 1113–1121, 1971, doi: 10.1016/0009-2509(71)80025-8.
- **META.**
- Background only.

[6] R. N. Trivedi and K. Vasudeva, "RTD for diffusion free laminar flow in helical coils," *Chem. Eng. Sci.*, vol. 29, pp. 2291–2295, 1974, doi: 10.1016/0009-2509(74)80005-9.
- **META.**
- Background only.

[7] R. N. Trivedi and K. Vasudeva, "Axial dispersion in laminar flow in helical coils," *Chem. Eng. Sci.*, vol. 30, pp. 317–325, 1975, doi: 10.1016/0009-2509(75)80081-9.
- **META.**
- Background only.

[8] E. B. Nauman, "The residence time distribution for laminar flow in helically coiled tubes," *Chem. Eng. Sci.*, vol. 32, pp. 287–293, 1977, doi: 10.1016/0009-2509(77)80207-8.
- **META.**
- Background only.

[9] A. K. Saxena and K. D. P. Nigam, "Coiled configuration for flow inversion and its effect on residence time distribution," *AIChE J.*, vol. 30, no. 3, pp. 363–368, 1984.
- **NOT OPENED.**

[10] S. Klutz, S. K. Kurt, M. Lobedann, and N. Kockmann, "Narrow residence time distribution in tubular reactor concept for Reynolds number range of 10–100," *Chem. Eng. Res. Des.*, vol. 95, pp. 22–33, 2015, doi: 10.1016/j.cherd.2015.01.003.
- **META.** Data seen as reproduced in [1], Fig. 2.
- Helical coil Bo = 80 at Re = 24.

[11] G. Valitov, D. Rossi, C. Price, A. Gavriilidis, and L. Mazzei, "Axial dispersion in curved channels in the presence of pulsating flow," *Chem. Eng. Process. – Process Intensif.*, vol. 180, Art. no. 108629, 2022, doi: 10.1016/j.cep.2021.108629.
- **FULL.**
- Coils reduce axial dispersion compared with straight tubes.

[12] M. Th. van Genuchten and P. J. Wierenga, "Mass transfer studies in sorbing porous media I. Analytical solutions," *Soil Sci. Soc. Am. J.*, vol. 40, no. 4, pp. 473–480, 1976, doi: 10.2136/sssaj1976.03615995004000040011x.
- **META.**
- Cited for the form of the mobile–immobile (two-region) model only.

[13] L. A. Rossman, H. Woo, M. Tryby, F. Shang, R. Janke, and T. Haxton, *EPANET 2.2 User Manual*, U.S. EPA, Cincinnati, OH, USA, Rep. EPA/600/R-20/133, 2020.
- **Seen in search results only.**
- Plug-flow quality model. Also confirmed through [14] and by running EPANET 2.2 via WNTR in this work.

[14] F. Shang, L. A. Rossman, and J. G. Uber, *EPANET-MSX 2.0 Multi-Species Extension User's Manual*, U.S. EPA, 2023. [Online]. Available: https://epanetmsx2manual.readthedocs.io/en/latest/1_introduction.html
- **FULL** (introduction chapter).
- EPANET has no longitudinal dispersion; MSX 2.0 adds it as an option.

[15] K. A. Klise, M. Bynum, D. Moriarty, and R. Murray, "A software framework for assessing the resilience of drinking water systems to disasters with an example earthquake case study," *Environ. Model. Softw.*, vol. 95, pp. 420–431, 2017, doi: 10.1016/j.envsoft.2017.06.022.
- **Seen in search results only.**
- WNTR 1.5.0 was installed and run in this work.

## Sensors and actuators

[16] Dallas Semiconductor, "DS18B20 Programmable Resolution 1-Wire Digital Thermometer," datasheet. [Online]. Available: https://cdn.sparkfun.com/datasheets/Sensors/Temp/DS18B20.pdf
- **FULL.**
- ±0.5 °C (−10…85 °C).
- 12-bit, 0.0625 °C.
- 750 ms conversion.
- 85 °C power-on value.

[17] M. Burton et al., "Arduino-Temperature-Control-Library (DallasTemperature)," v4.0.5, GitHub. [Online]. Available: https://github.com/milesburton/Arduino-Temperature-Control-Library
- **FULL** (header file).
- DEVICE_DISCONNECTED_C = −127.

[18] J. E. M. Perea Martins, "Physical analysis of a waterproof temperature sensor responsiveness for agricultural applications," *J. Agric. Informatics*, vol. 13, no. 2, 2022, doi: 10.17700/jai.2022.13.2.623.
- **FULL.**
- Waterproof DS18B20 probe τ = 6.2 s (heating) and 6.9 s (cooling) in still water.

[19] "DS18B20 thermo sensor," MultiFlexMeter project wiki, 10 Apr. 2021. [Online]. Available: https://multiflexmeter.atlassian.net/wiki/spaces/MFM/pages/1219690497/DS18B20+thermo+sensor
- **FULL.** Informal source; settling times only.

[20] DFRobot, "Gravity: Digital Water Flow Sensor (SEN0216)," product wiki. [Online]. Available: https://wiki.dfrobot.com/SEN0216
- **FULL.**
- 0.3–6 L/min.
- ±5 % (0.3–3 L/min).
- 5880 pulses/L.

[21] TinyTronics, "YF-S401 water flow sensor," product page. [Online]. Available: https://www.tinytronics.nl/shop/en/sensors/liquid/yf-s401-water-flow-sensor
- **FULL.**
- ≈ 98 Hz per L/min.
- 0.3–6 L/min.
- ±10 %.

[22] "MG996R High Torque Metal Gear Dual Ball Bearing Servo," spec sheet. [Online]. Available: https://courses.ece.cornell.edu/ece5990/ECE5725_Spring2020_Projects/May_15_Demo/Smart%20Lock/W_pp445_yl656/datasheet/MG996R_Tower-Pro.pdf
- **FULL.**
- 0.17 s/60° at 4.8 V; 0.14 s/60° at 6 V.

## Problem context, guidance and policy

[23] C. R. Proctor, W. J. Rhoads, T. Keane, M. Salehi, K. Hamilton, K. J. Pieper, D. M. Cwiertny, M. Prévost, and A. J. Whelton, "Considerations for large building water quality after extended stagnation," *AWWA Water Sci.*, vol. 2, no. 4, Art. no. e1186, 2020, doi: 10.1002/aws2.1186.
- **FULL.**
- Flushing duration is hard to generalise.
- Diagnostic tests (temperature, residual) can guide flushing.
- Temperature stabilisation can fail in hot climates.
- Efficacy criteria for weekly flushing are undocumented.

[24] Dubai Municipality, "Technical Guidelines for Legionella Control in Water System," DM-HSD-GU44-LCWS2, Version 6, 19 Aug. 2025. [Online]. Available: https://dmpmedia.dm.gov.ae/uploads/2022/10/DM-HSD-GU44-LCWS2_Technical-Guidelines-for-Legionella-Control-in-Water-System_V6-002.pdf
- **FULL.** Sec. 12-1:
  - weekly flushing of unoccupied guest rooms for "several minutes";
  - remove dead legs;
  - cold water < 20 °C.

[25] Health and Safety Executive, *Legionnaires' disease: Technical guidance. Part 2: The control of legionella bacteria in hot and cold water systems*, HSG274 Part 2. London, U.K.: TSO, 2024. [Online]. Available: https://www.hse.gov.uk/pubns/priced/hsg274part2.pdf
- **FULL.**
- Para. 2.78: weekly flushing for several minutes.
- Checklist: flush until outlet temperature stabilises and is comparable to the supply.

[26] U.S. Centers for Disease Control and Prevention, "Toolkit: Developing a Legionella Water Management Program," 15 Mar. 2024. [Online]. Available: https://www.cdc.gov/control-legionella/php/toolkit/wmp-toolkit.html
- **FULL** (web page only; the PDF was blocked).

[27] UAE Government Portal, "The UAE Water Security Strategy 2036." [Online]. Available: https://u.ae/en/about-the-uae/strategies-initiatives-and-awards/strategies-plans-and-visions/environment-and-energy/the-uae-water-security-strategy-2036
- **FULL.** −21 % total demand; 95 % reuse.

[28] "Energy ministry unveils national water strategy," *Gulf News*, Sep. 2017. [Online]. Available: https://gulfnews.com/uae/environment/energy-ministry-unveils-national-water-strategy-1.2097151
- **FULL.** Aim to halve average per-capita consumption.

[29] M. Salehi, D. DeSimone, K. Aghilinasrollahabadi, and T. Ahamed, "A case study on tap water quality in large buildings recommissioned after extended closure due to the COVID-19 pandemic," *Environ. Sci.: Water Res. Technol.*, vol. 7, no. 11, pp. 1996–2009, 2021, doi: 10.1039/D1EW00428J.
- **META.**
- More than 14 m³ used to flush 10 buildings.

[30] United Nations, "Goal 6: Clean Water and Sanitation." [Online]. Available: https://www.un.org/sustainabledevelopment/water-and-sanitation/
- **FULL.** SDG targets 6.1 and 6.4.

## Figures used with a caveat

- **UAE per-capita use ≈ 550 L/person/day.**
  - Attributed to the MOCCAE *State of Environment Report 2015* by a UAE Government Portal case study, and to EAD/FEWA in *Khaleej Times* (2016).
  - **Seen in search results only.** Present it as "about 550 L/person/day (reported)", or open one of those sources first.
- **UAE fixture-flow limits (Estidama, Al Sa'fat, ESMA label):** NOT VERIFIED. The water-saving estimate uses ASSUMED fixture flows.

## 3D model and tools credits

[31] Poly Haven, "Studio Small 09" HDRI, CC0 1.0. [Online]. Available: https://polyhaven.com/a/studio_small_09
- Downloaded 30 Oct 2026; used for lighting the Blender renders only.

[32] Blender Foundation, *Blender* 5.1, GPL. [Online]. Available: https://www.blender.org
- All rig geometry was modelled parametrically for this project (`3d/build_rig.py`). No third-party 3D meshes are used.

[33] U.S. EPA, *EPANET 2.2* (desktop and toolkit, public domain). [Online]. Available: https://www.epa.gov/water-research/epanet
- Run via WNTR 1.5 [15]. The `.inp` files open in the desktop application.

[34] Wokwi, "Custom Chips API" and "wokwi-ds18b20" part reference, documentation source on GitHub. [Online]. Available: https://github.com/wokwi/wokwi-docs
- Opened: the chips-api pages (getting-started, attributes, time, gpio, chip-json) and parts/wokwi-ds18b20.md.

## Software sources (local list in software_comparison.md)

`software_comparison.md` cites MathWorks Simscape docs, Modelica.Fluid, COMSOL Pipe Flow Module, AnyLogic editions, Streamlit docs, Wokwi docs, EPANET 2.2 [13], WNTR [15] and EPANET-MSX 2.0 [14]. Their check status is stated in that file.
