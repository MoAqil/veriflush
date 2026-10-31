"""Checks for the radial transport backend, the WNTR cross-check, truth separation
and the dashboard payload (added in model v1.1)."""
from __future__ import annotations

import ast
import importlib.util
import math
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model import params as P  # noqa: E402
from model.decisions import METHODS, VeriFlush  # noqa: E402
from model.radial import RadialTransport, laminar_bound, make_transport  # noqa: E402
from model.simulate import run  # noqa: E402
from scenarios.library import SCENARIOS  # noqa: E402


def _radial(**tp):
    return P.with_changes(P.Config(), transport=dict(model="radial", **tp))


def _flush(tr, cfg, volumes, per_volume_s=30):
    v = cfg.geometry.branch_volume_l / 1000
    q = v / per_volume_s
    for _ in range(int(volumes * per_volume_s)):
        tr.step(1.0, q, q, 13.0)
    return tr


class TestRadialTransport(unittest.TestCase):
    def test_laminar_bound_formula(self):
        self.assertAlmostEqual(float(laminar_bound(0.25)), 0.75)
        self.assertAlmostEqual(float(laminar_bound(0.5)), 0.5)
        self.assertAlmostEqual(float(laminar_bound(3.0)), 1 / 12)

    def test_zero_diffusion_matches_laminar_bound(self):
        """Poiseuille rings with D = 0 reproduce r = 1/(4 theta)."""
        for theta in (1.0, 2.0, 3.0, 5.0):
            cfg = _radial(d_salt_m2s=0.0, n_rings=40, n_axial=240)
            tr = _flush(RadialTransport(cfg), cfg, theta)
            self.assertAlmostEqual(tr.residual_old_fraction, float(laminar_bound(theta)), delta=0.003, msg=theta)

    def test_grid_convergence(self):
        res = []
        for m, nz in ((20, 120), (40, 240)):
            cfg = _radial(n_rings=m, n_axial=nz)
            res.append(_flush(RadialTransport(cfg), cfg, 3.0).residual_old_fraction)
        self.assertLess(abs(res[0] - res[1]), 0.002)

    def test_diffusion_only_reduces_residual(self):
        cfg0, cfg1 = _radial(d_salt_m2s=0.0), _radial()
        r0 = _flush(RadialTransport(cfg0), cfg0, 3.0).residual_old_fraction
        r1 = _flush(RadialTransport(cfg1), cfg1, 3.0).residual_old_fraction
        self.assertLess(r1, r0)

    def test_tracer_conservation(self):
        cfg = _radial()
        tr = RadialTransport(cfg)
        m0 = tr.tracer_inventory()
        _flush(tr, cfg, 2.0)
        self.assertAlmostEqual((tr.tracer_inventory() + tr.tracer_out) / m0, 1.0, places=9)

    def test_temperature_bounded(self):
        cfg = _radial()
        tr = _flush(RadialTransport(cfg), cfg, 4.0)
        self.assertTrue(np.all(tr.x[2] >= 13.0 - 1e-9) and np.all(tr.x[2] <= 24.0 + 1e-9))

    def test_profile_shape_and_range(self):
        for model in ("two_region", "radial"):
            cfg = P.with_changes(P.Config(), transport=dict(model=model))
            tr = _flush(make_transport(cfg), cfg, 1.0)
            p = tr.profile(20)
            self.assertEqual(p.shape, (20,))
            self.assertTrue(np.all((p >= -1e-12) & (p <= 1 + 1e-12)))
            self.assertLess(p[0], p[-1])                    # inlet fresher than endpoint


class TestTruthSeparation(unittest.TestCase):
    def test_decision_module_never_touches_truth(self):
        """Static proof: decisions.py imports nothing that carries truth and names no truth field."""
        src = (ROOT / "model" / "decisions.py").read_text()
        tree = ast.parse(src)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported |= {a.name for a in node.names}
        self.assertTrue(imported <= {"annotations", "math", "dataclass", "field", "Config", "Policy",
                                     "DS18B20_DISCONNECTED", "Observation"}, imported)
        for word in ("Truth", "truth", "Transport", "residual_old", "c_endpoint", "tracer"):
            self.assertNotIn(word, src, word)

    def test_truth_threshold_not_in_controller_inputs(self):
        """The adequacy threshold is evaluation-only: it is not in Policy, which every controller receives."""
        self.assertNotIn("adequate_residual", {f.name for f in __import__("dataclasses").fields(P.Policy)})
        a = SCENARIOS["S05_diversion"]
        for m in METHODS:
            sa, _, _ = run(a, m, 1, record=False)
            sb, _, _ = run(P.with_changes(a, adequate_residual=0.5), m, 1, record=False)
            self.assertEqual((sa["verdict"], sa["t_close_s"]), (sb["verdict"], sb["t_close_s"]), m.name)

    def test_radial_decisions_independent_of_tracer(self):
        a = P.with_changes(SCENARIOS["S05_diversion"], transport=dict(model="radial"))
        b = P.with_changes(a, tracer=dict(c_old_uscm=5000.0, c_fresh_uscm=10.0))
        for m in METHODS:
            sa, _, _ = run(a, m, 2, record=False)
            sb, _, _ = run(b, m, 2, record=False)
            self.assertEqual((sa["verdict"], sa["t_close_s"]), (sb["verdict"], sb["t_close_s"]), m.name)

    def test_radial_expected_verdicts(self):
        for key, v in {"S01_healthy": "Verified", "S04_blockage": "Failed", "S10_weak_contrast": "Uncertain"}.items():
            s, _, _ = run(P.with_changes(SCENARIOS[key], transport=dict(model="radial")), VeriFlush, 0, record=False)
            self.assertEqual(s["verdict"], v, key)


@unittest.skipUnless(importlib.util.find_spec("wntr"), "wntr not installed")
class TestWntrCrosscheck(unittest.TestCase):
    def test_epanet_agrees_in_plug_flow_limit(self):
        from model.wntr_crosscheck import crosscheck
        r = crosscheck()
        self.assertLess(abs(r["travel_time_epanet_s"] - r["travel_time_analytic_s"]), 2.0)
        self.assertLess(abs(r["travel_time_python_plug_s"] - r["travel_time_analytic_s"]), 1.5)
        self.assertLess(abs(r["endpoint_age_epanet_s"] - r["endpoint_age_python_plug_s"]), 2.0)
        self.assertLess(abs(r["headloss_branch_epanet_m"] / r["headloss_branch_python_m"] - 1), 0.05)
        self.assertLess(r["reynolds"], 2000)


def _gpp():
    sys.path.insert(0, str(ROOT / "firmware" / "hil"))
    from run_replay import compiler
    return compiler()


@unittest.skipUnless(_gpp(), "g++ not available")
class TestFirmwareReplay(unittest.TestCase):
    def test_firmware_matches_python_engine(self):
        """veriflush.ino, compiled on the host, reaches the same verdict at the same second as decisions.py."""
        from run_replay import main
        df = main()
        self.assertTrue(df.verdict_match.all(), df[~df.verdict_match])
        self.assertTrue(df.t_close_match.all(), df[~df.t_close_match])


class TestDashboardPayload(unittest.TestCase):
    def test_payload_and_render(self):
        sys.path.insert(0, str(ROOT / "dashboard"))
        from payload import render, scenario_payload
        sp = scenario_payload("S05_diversion", SCENARIOS["S05_diversion"], 0)
        self.assertEqual(set(sp["runs"]), {m.name for m in METHODS})
        r = sp["runs"]["VeriFlush"]
        n = len(r["series"]["t"])
        for k in ("q", "tt101", "res", "fo", "prof"):
            self.assertEqual(len(r["series"][k]), n, k)
        html = render(dict(meta=dict(status="SIMULATED", model_version=P.MODEL_VERSION, seed=0, generated_utc="test",
                                     backends={"two_region": "x"}), data={"two_region": [sp]}))
        self.assertIn("SIMULATED DATA", html)
        self.assertIn("TRUTH: NOT USED BY VERIFLUSH", html)
        self.assertNotIn("/*__PAYLOAD__*/null", html)
        self.assertFalse(math.isnan(r["t_close"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
