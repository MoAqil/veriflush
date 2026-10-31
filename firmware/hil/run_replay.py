"""Firmware replay test: compile firmware/veriflush/veriflush.ino on the host (g++, with Arduino
stand-ins in this folder) and feed it the sensor observations the Python simulation produced for
every scenario (seed 0, VeriFlush run). Compares the firmware's verdict and stop time with the
Python decision engine.

    python firmware/hil/run_replay.py      ->  outputs/tables/firmware_vs_python.csv

Open-loop replay: the observations come from the Python run, so the comparison is valid up to the
moment either side closes the valve. Requires g++ (e.g. MSYS2 on Windows). SIMULATED inputs.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from scenarios.library import SCENARIOS  # noqa: E402

COLS = ["obs_t_s", "obs_ft_pulses", "obs_tt100_c", "obs_tt101_c", "obs_ls_open", "obs_ls_closed", "obs_pt_kpa"]


def compiler() -> str | None:
    for c in (os.environ.get("CXX"), shutil.which("g++"), r"C:\msys64\ucrt64\bin\g++.exe", r"C:\msys64\mingw64\bin\g++.exe"):
        if c and Path(c).exists():
            return c
    return None


def build(exe: Path) -> None:
    cxx = compiler()
    if cxx is None:
        raise RuntimeError("g++ not found (set CXX)")
    env = dict(os.environ, PATH=str(Path(cxx).parent) + os.pathsep + os.environ.get("PATH", ""))
    subprocess.run([cxx, "-std=c++17", "-Wall", "-Wno-unused", "-DVF_HAVE_PRESSURE=1", "-Istubs", "-I.",
                    "harness.cpp", "-o", str(exe)], cwd=HERE, check=True, env=env)


def replay(exe: Path, key: str) -> dict:
    raw = pd.read_csv(ROOT / "data" / "raw" / f"{key}__veriflush__seed0.csv")
    trace = "\n".join(" ".join(f"{v:.6g}" for v in row) for row in raw[COLS].itertuples(index=False)) + "\n"
    out = subprocess.run([str(exe)], input=trace, capture_output=True, text=True, check=True,
                         env=dict(os.environ, PATH=str(Path(compiler()).parent) + os.pathsep + os.environ["PATH"])).stdout
    lines = out.splitlines()
    v = next((l for l in lines if l.startswith("VERDICT")), "")
    parts = v.split(",", 6)
    warns = [l.split(",", 2)[2] for l in lines if l.startswith("WARN")]
    return dict(fw_verdict=parts[1] if v else "none", fw_t_close_s=float(parts[2]) if v else float("nan"),
                fw_v_l=float(parts[3]) if v else float("nan"), fw_reason=parts[6] if v else "", fw_warnings=" | ".join(warns))


def main():
    rep = pd.read_csv(ROOT / "data" / "processed" / "representative_runs_seed0.csv")
    rep = rep[(rep.method == "VeriFlush") & (rep.backend == "two_region")].set_index("scenario")
    with tempfile.TemporaryDirectory() as d:
        exe = Path(d) / "vf_harness.exe"
        build(exe)
        rows = []
        for key in SCENARIOS:
            r = replay(exe, key)
            py = rep.loc[key]
            rows.append(dict(scenario=key, python_verdict=py.verdict, fw_verdict=r["fw_verdict"],
                             python_t_close_s=py.t_close_s, fw_t_close_s=r["fw_t_close_s"],
                             python_v_l=round(py.v_recorded_l, 3), fw_v_l=r["fw_v_l"],
                             verdict_match=py.verdict == r["fw_verdict"],
                             t_close_match=abs(py.t_close_s - r["fw_t_close_s"]) <= 1.0,
                             fw_reason=r["fw_reason"], fw_warnings=r["fw_warnings"]))
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "outputs" / "tables" / "firmware_vs_python.csv", index=False)
    print(df[["scenario", "python_verdict", "fw_verdict", "python_t_close_s", "fw_t_close_s", "python_v_l", "fw_v_l"]].to_string(index=False))
    print(f"verdicts matching: {df.verdict_match.sum()}/{len(df)}; stop time within 1 s: {df.t_close_match.sum()}/{len(df)}")
    return df


if __name__ == "__main__":
    main()
