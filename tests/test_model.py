"""Automated checks for the VeriFlush virtual testbed.

Run with either:   python -m unittest discover -s tests -v
             or:   python -m pytest tests            (if pytest is installed)
"""
from __future__ import annotations

import dataclasses
import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.stats import poisson

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model import params as P  # noqa: E402
from model.decisions import FAILED, UNCERTAIN, VERIFIED, FlowVolume, Known, TimerOnly, VeriFlush  # noqa: E402
from model.hydraulics import Path as HPath, friction_factor, solve  # noqa: E402
from model.sensors import OBS_FIELDS, Observation, Truth  # noqa: E402
from model.simulate import run  # noqa: E402
from model.transport import Transport  # noqa: E402
from scenarios.library import SCENARIOS, perturbed  # noqa: E402


class TestUnitsAndGeometry(unittest.TestCase):
    def test_pipe_volume_6m_8mm(self):
        v_l = P.m3_to_l(P.pipe_volume_m3(0.008, 6.0))
        self.assertAlmostEqual(v_l, 0.3016, places=4)      # spec: ~0.302 L

    def test_pipe_volume_8m_8mm(self):
        self.assertAlmostEqual(P.m3_to_l(P.pipe_volume_m3(0.008, 8.0)), 0.4021, places=4)

    def test_flow_unit_round_trip(self):
        for q in (0.1, 0.63, 1.2, 5.0):
            self.assertAlmostEqual(P.m3s_to_lpm(P.lpm_to_m3s(q)), q, places=12)
        self.assertAlmostEqual(P.lpm_to_m3s(60.0), 1e-3)

    def test_configured_volume_defaults_to_ideal(self):
        self.assertAlmostEqual(P.Config().configured_l, 0.30159, places=4)


class TestHydraulics(unittest.TestCase):
    def test_hagen_poiseuille(self):
        """Laminar friction head equals 128 mu L Q / (pi rho g D^4)."""
        p = HPath(6.0, 0.008, 0.0)
        q = P.lpm_to_m3s(0.3)                                # Re ~ 800, laminar
        expected = 128 * P.MU * 6.0 * q / (math.pi * P.RHO * P.G * 0.008 ** 4)
        self.assertAlmostEqual(p.head(q), expected, delta=expected * 0.02)   # RHO*NU vs MU rounding

    def test_friction_factor_continuity(self):
        self.assertAlmostEqual(friction_factor(1999.9), 64 / 1999.9, places=6)
        self.assertAlmostEqual(friction_factor(4000), 0.316 * 4000 ** -0.25, places=6)

    def test_inverse_flow(self):
        p = HPath(6.0, 0.008, 50.0, 0.15)
        for h in (0.2, 0.3, 0.5):
            self.assertAlmostEqual(p.head(p.flow(h)), h, places=8)

    def test_continuity_at_fault_tee(self):
        cfg = SCENARIOS["S05_diversion"]
        s = solve(cfg, 1.0)
        self.assertAlmostEqual(s.q_meter, s.q_branch + s.q_div, places=14)
        self.assertGreater(s.q_div, 0.0)

    def test_healthy_flow_in_rig_range(self):
        q = P.m3s_to_lpm(solve(P.Config(), 1.0).q_meter)
        self.assertTrue(0.3 <= q <= 1.2, q)                  # rig target 0.3-1.2 L/min

    def test_closed_valve_zero_flow(self):
        self.assertEqual(solve(P.Config(), 0.0).q_meter, 0.0)

    def test_blockage_raises_manifold_pressure(self):
        open_p = solve(P.Config(), 1.0).p_manifold_kpa
        blk_p = solve(SCENARIOS["S04_blockage"], 1.0).p_manifold_kpa
        self.assertGreater(blk_p, open_p)


class TestTransport(unittest.TestCase):
    def _pure_tis(self, n):
        # upstream cells already hold fresh water (F=0), so they do not affect the old-fraction result
        return P.with_changes(P.Config(), transport=dict(n_cells_branch=n, slow_fraction=0.0, max_cell_fraction=0.02))

    def test_tanks_in_series_matches_erlang(self):
        """Mean old fraction in N stirred tanks after throughput theta (exact Poisson/Erlang result)."""
        n = 10
        cfg = self._pure_tis(n)
        tr = Transport(cfg)
        v = cfg.geometry.branch_volume_l / 1000
        q = v / 60.0                                          # one volume per minute
        for _ in range(90):                                   # theta = 1.5
            tr.step(1.0, q, q, 13.0)
        k = np.arange(1, n + 1)
        exact = poisson.cdf(k - 1, n * 1.5).mean()
        self.assertAlmostEqual(tr.residual_old_fraction, exact, delta=0.01)

    def test_tracer_mass_conservation(self):
        cfg = SCENARIOS["S05_diversion"]
        tr = Transport(cfg)
        m0 = tr.tracer_inventory()
        hs = solve(cfg, 1.0)
        for _ in range(120):
            tr.step(1.0, hs.q_meter, hs.q_branch, 13.0)
        self.assertAlmostEqual((tr.tracer_inventory() + tr.tracer_out) / m0, 1.0, places=9)

    def test_water_volume_balance(self):
        cfg = SCENARIOS["S05_diversion"]
        tr = Transport(cfg)
        hs = solve(cfg, 1.0)
        for _ in range(60):
            tr.step(1.0, hs.q_meter, hs.q_branch, 13.0)
        self.assertAlmostEqual(tr.vol_out + tr.vol_div, hs.q_meter * 60, places=12)

    def test_temperature_bounds(self):
        cfg = P.Config()
        tr = Transport(cfg)
        hs = solve(cfg, 1.0)
        lo, hi = cfg.thermal.t_feed_c, max(cfg.thermal.t_old_c, cfg.thermal.t_env_c)
        for _ in range(200):
            tr.step(1.0, hs.q_meter, hs.q_branch, cfg.thermal.t_feed_c)
            self.assertTrue(np.all(tr.br[2] >= lo - 1e-9) and np.all(tr.br[2] <= hi + 1e-9))
            self.assertTrue(np.all((tr.br[0] >= -1e-12) & (tr.br[0] <= 1 + 1e-12)))

    def test_time_step_convergence(self):
        """Halving the sub-step limit changes the residual by < 0.002."""
        res = []
        for f in (0.2, 0.1, 0.05):
            cfg = P.with_changes(P.Config(), transport=dict(max_cell_fraction=f))
            tr = Transport(cfg)
            hs = solve(cfg, 1.0)
            for _ in range(80):
                tr.step(1.0, hs.q_meter, hs.q_branch, 13.0)
            res.append(tr.residual_old_fraction)
        self.assertLess(abs(res[0] - res[2]), 0.002)
        self.assertLess(abs(res[1] - res[2]), 0.001)

    def test_no_flow_no_exchange(self):
        tr = Transport(P.Config())
        for _ in range(100):
            tr.step(1.0, 0.0, 0.0, 13.0)
        self.assertAlmostEqual(tr.residual_old_fraction, 1.0, places=12)


class TestDecisionLogic(unittest.TestCase):
    def test_truth_not_visible_to_methods(self):
        truth_names = {f.name for f in dataclasses.fields(Truth)} - {"t_s"}
        self.assertFalse(truth_names & set(OBS_FIELDS))
        for cls in (TimerOnly, FlowVolume, VeriFlush):
            for f in dataclasses.fields(Known):
                self.assertNotIn("true", f.name)

    def test_decisions_independent_of_truth_tracer(self):
        """Changing the tracer concentration (truth only) must not change any decision."""
        a = SCENARIOS["S05_diversion"]
        b = P.with_changes(a, tracer=dict(c_old_uscm=9999.0, c_fresh_uscm=1.0))
        for m in (TimerOnly, FlowVolume, VeriFlush):
            sa, _, _ = run(a, m, 3, record=False)
            sb, _, _ = run(b, m, 3, record=False)
            for k in ("verdict", "reason", "t_close_s", "water_used_l"):
                self.assertEqual(sa[k], sb[k], (m.name, k))

    def test_repeatable_with_seed(self):
        cfg = perturbed(SCENARIOS["S07_flow_bias"], 4)
        s1, d1, _ = run(cfg, VeriFlush, 4)
        s2, d2, _ = run(cfg, VeriFlush, 4)
        self.assertEqual(s1["verdict"], s2["verdict"])
        self.assertTrue(d1.equals(d2))

    def test_expected_verdicts(self):
        expect = {
            "S01_healthy": VERIFIED, "S04_blockage": FAILED, "S08_flow_dropout": UNCERTAIN,
            "S09a_tt101_frozen": UNCERTAIN, "S09b_tt101_disconnected": UNCERTAIN,
            "S10_weak_contrast": UNCERTAIN, "S11_valve_feedback": UNCERTAIN, "S12_multiple": UNCERTAIN,
        }
        for key, v in expect.items():
            s, _, _ = run(SCENARIOS[key], VeriFlush, 0, record=False)
            self.assertEqual(s["verdict"], v, key)

    def test_diversion_and_wrong_volume_are_flagged(self):
        for key in ("S05_diversion", "S06_wrong_volume", "S07_flow_bias"):
            s, _, _ = run(SCENARIOS[key], VeriFlush, 0, record=False)
            self.assertIn("Endpoint-anchored branch volume", s["warnings"], key)

    def test_timer_never_detects(self):
        for key, cfg in SCENARIOS.items():
            s, _, _ = run(cfg, TimerOnly, 0, record=False)
            self.assertEqual(s["verdict"], VERIFIED, key)

    def test_missing_values_handled(self):
        """NaN / None samples must not crash the engines; persistent NaN -> not Verified."""
        known = Known.from_config(P.Config())
        for cls in (TimerOnly, FlowVolume, VeriFlush):
            c = cls(known)
            t = 0
            while not c.done and t < 400:
                t += 1
                c.step(Observation(t, c.cmd, 0, math.nan, math.nan, math.nan, None, 0, 0))
            self.assertTrue(c.done)
            if cls is not TimerOnly:
                self.assertNotEqual(c.res.verdict, VERIFIED, cls.name)

    def test_every_result_has_reason(self):
        for key, cfg in SCENARIOS.items():
            for m in (TimerOnly, FlowVolume, VeriFlush):
                s, _, _ = run(cfg, m, 1, record=False)
                self.assertTrue(len(s["reason"]) > 10, (key, m.name))
                self.assertIn(s["verdict"], (VERIFIED, FAILED, UNCERTAIN))

    def test_all_methods_stop_by_time_limit(self):
        for key, cfg in SCENARIOS.items():
            for m in (TimerOnly, FlowVolume, VeriFlush):
                s, _, _ = run(cfg, m, 0, record=False)
                self.assertLessEqual(s["t_close_s"], cfg.policy.t_max_s + 1e-9)


class TestPlausibility(unittest.TestCase):
    def test_sensor_ranges(self):
        s, df, _ = run(SCENARIOS["S01_healthy"], VeriFlush, 2)
        self.assertTrue((df.obs_ft_flow_lpm >= 0).all())
        self.assertTrue(df.obs_tt101_c.between(-10, 60).all())
        self.assertTrue((df.truth_residual_old_fraction.diff().fillna(0) <= 1e-9).all())   # never increases
        self.assertTrue(df.truth_c_endpoint_uscm.between(200, 1700).all())

    def test_csv_and_figure_generation(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        s, df, _ = run(SCENARIOS["S01_healthy"], VeriFlush, 0)
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.csv"
            df.to_csv(f, index=False)
            self.assertGreater(f.stat().st_size, 1000)
            fig, ax = plt.subplots()
            ax.plot(df.obs_t_s, df.obs_tt101_c)
            g = Path(d) / "x.png"
            fig.savefig(g)
            self.assertGreater(g.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
