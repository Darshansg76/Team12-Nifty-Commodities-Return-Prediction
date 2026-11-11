"""Round-trip inference checks against real evaluated project observations.

Run after training with: python -m unittest discover -s tests -p test_saved_models.py
The checks skip cleanly if the trained project artifacts do not yet exist.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from demo import FEATURE_COLUMNS, TOLERANCE, historical_inputs, predict_saved


class SavedModelRoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        needed = [ROOT / "results" / "test_predictions.csv"]
        needed += [ROOT / "models" / name / f"{name}_metadata.json"
                   for name in ["xgboost", "keras", "fastai", "tabnet", "flash"]]
        if not all(path.exists() for path in needed):
            raise unittest.SkipTest("Train the project first to check saved model inference.")
        saved, features, scaler, _ = historical_inputs(ROOT)
        # Cover the beginning, middle and end of the actual frozen test era.
        indices = np.unique(np.linspace(0, len(saved) - 1, min(12, len(saved)), dtype=int))
        cls.sample = saved.iloc[indices].reset_index(drop=True)
        rows = features.loc[cls.sample.Date]
        cls.X = scaler.transform(rows[FEATURE_COLUMNS]).astype(np.float32)
        cls.report = {"sample": "12 evenly spaced real frozen test observations",
                      "feature_dates": [str(d.date()) for d in cls.sample.Date],
                      "tolerance_percentage_points": TOLERANCE,
                      "models": {}}

    def _check(self, name):
        actual = predict_saved(name, self.X, ROOT)
        expected = self.sample[name].to_numpy(dtype=float)
        max_difference = float(np.max(np.abs(actual - expected)))
        self.report["models"][name] = {"max_absolute_difference_pp": max_difference,
                                       "passed": bool(max_difference < TOLERANCE),
                                       "observations": len(expected)}
        self.assertEqual(len(actual), len(expected))
        self.assertTrue(np.isfinite(actual).all())
        self.assertLess(max_difference, TOLERANCE, f"{name}: loaded checkpoint prediction changed")

    def test_xgboost(self):
        self._check("xgboost")

    def test_keras(self):
        self._check("keras")

    def test_fastai(self):
        self._check("fastai")

    def test_tabnet(self):
        self._check("tabnet")

    def test_flash(self):
        self._check("flash")

    @classmethod
    def tearDownClass(cls):
        (ROOT / "results" / "model_reload_checks.json").write_text(
            json.dumps(cls.report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
