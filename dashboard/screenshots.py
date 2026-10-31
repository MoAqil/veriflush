"""Screenshot every scenario of the offline dashboard with a locally installed
Chromium browser (Edge or Chrome) in headless mode.

    python dashboard/screenshots.py      ->  outputs/screenshots/*.png

Uses the player's deep links (#s=<scenario>&m=<method>&t=end). SIMULATED data.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from payload import ROOT  # noqa: E402

from scenarios.library import SCENARIOS  # noqa: E402

HTML = ROOT / "outputs" / "veriflush_dashboard.html"
OUT = ROOT / "outputs" / "screenshots"
CANDIDATES = [
    os.environ.get("VF_BROWSER", ""),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("chromium") or "", shutil.which("google-chrome") or "", shutil.which("microsoft-edge") or "",
]


def browser() -> str:
    for c in CANDIDATES:
        if c and Path(c).exists():
            return c
    raise SystemExit("No Chromium-based browser found; set VF_BROWSER to its executable.")


def shot(exe: str, frag: str, out: Path, size=(1366, 1540)):
    url = HTML.resolve().as_uri() + "#" + frag
    profile = tempfile.mkdtemp(prefix="vfb_")     # fresh short-path profile per shot: never reuse a running browser
    subprocess.run([exe, "--headless=new", f"--user-data-dir={profile}", "--no-first-run", "--disable-gpu", "--hide-scrollbars", f"--window-size={size[0]},{size[1]}",
                    "--virtual-time-budget=4000", f"--screenshot={Path(profile) / 'shot.png'}", url],
                   check=True, capture_output=True, timeout=120)
    shutil.move(Path(profile) / "shot.png", out)     # browser output path kept short (Windows MAX_PATH)
    shutil.rmtree(profile, ignore_errors=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    exe = browser()
    jobs = [(f"s={i}&m=VeriFlush&t=end", f"{k}__veriflush_end.png") for i, k in enumerate(SCENARIOS)]
    jobs += [("s=0&m=VeriFlush&t=20", "S01_healthy__veriflush_t20_arrival.png"),
             ("s=4&m=Timer-only&t=end", "S05_diversion__timeronly_end.png"),
             ("s=4&m=Flow + configured volume&t=end", "S05_diversion__flow_end.png"),
             ("s=0&m=VeriFlush&t=end&b=radial", "S01_healthy__veriflush_end_radial.png")]
    for frag, name in jobs:
        shot(exe, frag.replace(" ", "%20"), OUT / name)
        print("ok", name)


if __name__ == "__main__":
    main()
