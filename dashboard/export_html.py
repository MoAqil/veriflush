"""Export the self-contained offline dashboard (all 13 scenarios x 3 methods x 2 transport models, seed 0).

    python dashboard/export_html.py      ->  outputs/veriflush_dashboard.html

The page has no external dependencies and works offline. All data are SIMULATED.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from payload import ROOT, build, render  # noqa: E402

OUT = ROOT / "outputs" / "veriflush_dashboard.html"


def main():
    html = render(build())
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
