# Software decision matrix: VeriFlush digital prototype

*Status: desk review, 30 Oct 2026. Ratings are the team's engineering judgement for this specific job: one 6–8 m branch, sensor and controller behaviour, fault injection, and a one-minute video. They are not general rankings of the tools.*

## What the digital prototype must do

The tool has to reproduce **one small rig**, not a city network. That rig has:

- a pump and a bypass;
- one monitored branch (8 mm ID, 6 m) and one reference branch;
- a diversion tee placed after the meter;
- a servo-driven ball valve with limit switches;
- a Hall-effect flow sensor;
- two DS18B20 temperature probes;
- an independent saline tracer.

Most of the difficulty sits in **sensor faults, controller logic and evidence handling**. The hydraulics are comparatively simple.

## Matrix

Scores run from 1 (poor) to 5 (excellent) for this use. "Time to build" is the estimated time to a working VeriFlush prototype for a student team.

| Option | Hydraulics | Tracer / water age | Thermal | Sensor + controller simulation | Fault modelling | Dashboard / animation | Learning effort | Licence / cost | Install | Time to build | Reproducibility | Report outputs | 1-min video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **MATLAB + Simulink + Simscape Fluids** | 5: isothermal and thermal-liquid pipe blocks [3] | 3: no built-in tracer; possible via a thermal-liquid analogy or custom blocks | 5 [3] | 5: Stateflow logic, sensors and noise blocks | 5 | 4: scopes, App Designer | 3 | 2: paid; university licence needed, Simscape Fluids is an add-on | 3: large | 3 | 3: needs licence to rerun | 5 | 4 |
| **EPANET 2.2** | 4: network hydraulics, extended period [1] | 4: age, trace and chemical; plug-flow Lagrangian, **no axial dispersion** [1] | 1 | 1: rules and controls only | 2: valves and controls | 1 | 4 | 5: public domain (US EPA) | 5 | 4 | 5 | 3 | 2 |
| **Python + WNTR** (wraps EPANET) | 4 [2] | 4: EPANET quality engine [1], [2] | 1 | 3: you write it in Python | 4: built-in damage and leak scenarios [2] | 3: with Plotly | 3 | 5: open source (Revised BSD) | 4: `pip install wntr` | 4 | 5 | 4 | 3 |
| **EPANET-MSX 2.0** | 4 | 5: multi-species, **includes longitudinal dispersion** [9] | 1 | 1 | 2 | 1 | 2 | 5 | 3 | 3 | 5 | 3 | 1 |
| **Python scientific stack** (NumPy, SciPy, pandas) + Streamlit/Dash | 3: write your own; adequate for one branch | 4: write your own 1-D transport, dispersion is controllable | 4: write your own lumped model | 5: same language as the logic | 5 | 4: Streamlit [7] or Dash | 3 | 5 | 5 | **5** | 5 | 5 (matplotlib) | 4 |
| **OpenModelica + Modelica.Fluid** | 5: pipes, valves, pumps, heat transfer [4] | 3: trace substances supported in Media, but harder | 4 | 4: Modelica state machines | 4 | 2: plots only | 2 | 5: open source | 3 | 2 | 4 | 4 | 2 |
| **COMSOL Pipe Flow Module** | 5: 1-D pipe flow, heat transfer and transport of diluted species [5] | 5 | 5 | 2 | 3 | 3 | 2 | 1: commercial plus module licence | 2 | 2 | 2 | 5 | 3 |
| **ANSYS Fluent (CFD)** | 5: 3-D, resolves laminar profile and Dean vortices | 5 | 5 | 1 | 2 | 3 | 1 | 2: free student version has mesh limits | 2 | 1 | 2 | 5 | 3 |
| **AnyLogic PLE** | 2: Fluid Library is "limited" in PLE [6] | 1 | 1 | 4: agent and state charts | 4 | 5: built-in animation | 3 | 4: free PLE, learning use only [6] | 4 | 3 | 3 | 3 | 5 |
| **Wokwi** (Arduino simulator) | 0 | 0 | 0 | 5: Uno, DS18B20, servo, buttons supported [8]; no flow-sensor part listed (custom chip or clock generator needed) | 3 | 3: live circuit | 4 | 4: free tier | 5: browser | 4 | 4 | 2 | 4 |
| **Tinkercad Circuits / Proteus** | 0 | 0 | 0 | 3–4: Arduino simulation; Proteus is paid | 2 | 2 | 4 | 3–5 | 5 / 3 | 4 | 3 | 2 | 3 |

## Decision

**Selected route:** Python scientific stack as the primary simulator, which is the route the brief suggested. Three things are built in plain Python:

- quasi-steady hydraulics;
- 1-D two-region transport;
- virtual sensors and the decision engines.

The shareable dashboard is a self-contained HTML page. A Streamlit app is also provided.

### Changes from the brief's suggested architecture

**1. EPANET/WNTR is a cross-check, not the core.** Three reasons:

- **No dispersion.** EPANET 2.2's quality engine is plug flow with no axial dispersion [1]. In a 6 m laminar branch, the RTD tail is exactly what decides whether 3 volumes is enough. A plug-flow model would declare the branch 100 % exchanged after 1.0 volume.
- **No sensor or controller layer.** EPANET has no sensors, valve feedback or controller layer. All of that would still be written in Python.
- **Now run as a cross-check.** WNTR 1.5.0 (EPANET 2.2) is installed and `model/wntr_crosscheck.py` runs it on the same 6 m × 8 mm branch. In the plug-flow limit it agrees with the Python model: endpoint travel time 33 s (Python) vs 34 s (EPANET) vs 32.5 s analytical; endpoint water age 32.5 s vs 32.0 s; head loss within 2 %. See `outputs/tables/wntr_crosscheck.csv` and Figure 8c. EPANET-MSX 2.0 (bundled with WNTR) was tried with a molecular diffusivity, but the WNTR 1.5 MSX writer did not carry the initial tracer state through, so no MSX result is reported. MSX's Taylor-type dispersion also assumes t ≫ R²/D (≈ 10⁴ s for salt here) while the branch residence time is ≈ 30 s, so it would not represent this branch anyway. The laminar tail is instead handled by a radially resolved laminar model written for this work (`model/radial.py`).

**2. MATLAB/Simscape was not selected.** It would give stronger thermal-hydraulics, but it needs a licence, so results are not reproducible by judges or other teams. The extra fidelity also does not change any decision in this problem.

**3. Wokwi is the recommended next step for hardware-in-the-loop.** The same rules can run on a simulated Uno with simulated DS18B20s and servo before the physical rig is ready.

## References

*Check status: [1] = references.md [13] (seen in search results only; EPANET 2.2 itself was run via WNTR), [2] = [15] (seen in search results only; WNTR 1.5 installed and run), [9] = [14] (opened). [3]–[8] are vendor documentation pages; in the final review [3], [4], [5] and [7] were opened and live, [6] returned 403 (supported via search), [8] Wokwi was unreachable.*

[1] L. A. Rossman, H. Woo, M. Tryby, F. Shang, R. Janke, and T. Haxton, *EPANET 2.2 User Manual*, EPA/600/R-20/133. Cincinnati, OH, USA: U.S. Environmental Protection Agency, 2020. [Online]. Available: https://www.epa.gov/system/files/documents/2021-07/epanet_users_manual_2.2.0-1.pdf

[2] K. A. Klise, M. Bynum, D. Moriarty, and R. Murray, "A software framework for assessing the resilience of drinking water systems to disasters with an example earthquake case study," *Environmental Modelling & Software*, vol. 95, pp. 420–431, 2017. Code: https://github.com/USEPA/WNTR

[3] MathWorks, "Modeling Isothermal Liquid Systems" and "Thermal Liquid Modeling Framework," Simscape documentation. [Online]. Available: https://www.mathworks.com/help/simscape/ug/modeling-isothermal-liquid-systems.html ; https://www.mathworks.com/help/simscape/ug/thermal-liquid-modeling-framework.html

[4] Modelica Association, "Modelica.Fluid User's Guide," Modelica Standard Library documentation (OpenModelica build). [Online]. Available: https://build.openmodelica.org/Documentation/Modelica.Fluid.UsersGuide.html

[5] COMSOL AB, *Pipe Flow Module User's Guide*, v6.4. [Online]. Available: https://doc.comsol.com/6.4/doc/com.comsol.help.pipe/PipeFlowModuleUsersGuide.pdf

[6] The AnyLogic Company, "AnyLogic editions," AnyLogic Help. [Online]. Available: https://anylogic.help/anylogic/ui/editions.html

[7] Snowflake Inc., "st.download_button," Streamlit documentation. [Online]. Available: https://docs.streamlit.io/develop/api-reference/widgets/st.download_button

[8] Wokwi, "Supported Hardware" and "wokwi-ds18b20 Reference." [Online]. Available: https://docs.wokwi.com/getting-started/supported-hardware ; https://docs.wokwi.com/parts/wokwi-ds18b20

[9] U.S. EPA, *EPANET-MSX 2.0 User Manual*, ch. 1 "Introduction," 2022. [Online]. Available: https://epanetmsx2manual.readthedocs.io/en/latest/1_introduction.html
