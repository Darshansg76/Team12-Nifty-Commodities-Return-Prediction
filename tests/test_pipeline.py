"""Independent checks for chronology, feature causality and preprocessing.

Run from the project root: python -m unittest discover -s tests -v
These tests use deterministic market-shaped fixtures, not downloaded observations.
"""
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from src import pipeline


def example_ohlc(start="2018-01-01", end="2025-12-31"):
    dates = pd.bdate_range(start, end)
    k = np.arange(len(dates), dtype=float)
    # Nonconstant returns and ranges expose accidental shifts and scaling leaks.
    close = 2500.0 * np.exp(0.0002 * k + 0.025 * np.sin(k / 13.0)
                            + 0.008 * np.cos(k / 3.0))
    open_ = close * (1.0 + 0.002 * np.sin(k / 5.0))
    high = np.maximum(open_, close) * (1.007 + 0.001 * np.cos(k / 7.0))
    low = np.minimum(open_, close) * (0.993 - 0.001 * np.sin(k / 9.0))
    return pd.DataFrame({"Date": dates, "Open": open_, "High": high,
                         "Low": low, "Close": close})


class PipelineChronologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = example_ohlc()
        cls.frame = pipeline.build_features(cls.raw.copy())
        cls.features = list(pipeline.FEATURE_COLUMNS)

    def test_next_observation_target_and_target_date(self):
        """Catch same-day targets, wrong return units and calendar-day shifts."""
        raw = self.raw.sort_values("Date").reset_index(drop=True)
        expected = pd.DataFrame({
            "Date": raw["Date"],
            "TargetDate": raw["Date"].shift(-1),
            "target_return": 100.0 * (raw["Close"].shift(-1) / raw["Close"] - 1.0),
        }).set_index("Date")
        actual = self.frame.set_index("Date")
        self.assertGreater(len(actual), 200)
        self.assertTrue(actual.index.is_unique)
        self.assertTrue(actual.index.is_monotonic_increasing)
        self.assertTrue((pd.to_datetime(actual["TargetDate"]) > actual.index).all())
        pd.testing.assert_series_equal(
            pd.to_datetime(actual["TargetDate"]),
            pd.to_datetime(expected.loc[actual.index, "TargetDate"]),
            check_names=False,
        )
        np.testing.assert_allclose(
            actual["target_return"].to_numpy(),
            expected.loc[actual.index, "target_return"].to_numpy(),
            rtol=1e-10, atol=1e-10,
        )

    def test_weekend_sessions_keep_distinct_weekday_features(self):
        """Special Saturday/Sunday sessions must not look like Monday/Tuesday."""
        raw = example_ohlc(start="2024-01-01", end="2024-07-01")
        raw["Date"] = pd.date_range("2024-01-01", periods=len(raw), freq="D")
        encoded = pipeline.build_features(raw)
        representatives = encoded.groupby(encoded.Date.dt.dayofweek).first()
        self.assertEqual(list(representatives.index), list(range(7)))
        actual = representatives[["weekday_sin", "weekday_cos"]].to_numpy()
        expected = np.column_stack((np.sin(2*np.pi*np.arange(7)/7),
                                    np.cos(2*np.pi*np.arange(7)/7)))
        np.testing.assert_allclose(actual, expected, atol=1e-12)
        self.assertEqual(len(np.unique(np.round(actual, 12), axis=0)), 7)

    def test_feature_values_do_not_change_when_future_is_appended(self):
        """A full-history fit/centered window/backfill would alter past features."""
        for stop in (900, 1500):
            with self.subTest(stop=stop):
                truncated = pipeline.build_features(self.raw.iloc[:stop].copy())
                earlier = truncated.set_index("Date")
                full = self.frame.set_index("Date")
                common = earlier.index.intersection(full.index)
                self.assertGreater(len(common), 100)
                np.testing.assert_allclose(
                    earlier.loc[common, self.features].to_numpy(dtype=float),
                    full.loc[common, self.features].to_numpy(dtype=float),
                    rtol=1e-10, atol=1e-10, equal_nan=True,
                )

    def test_modifying_future_does_not_change_historical_features(self):
        """An extreme future shock must not affect any earlier feature row."""
        stop = 1200
        shocked = self.raw.copy()
        changed_from = shocked.loc[stop, "Date"]
        shocked.loc[stop:, ["Open", "High", "Low", "Close"]] *= 4.0
        altered = pipeline.build_features(shocked).set_index("Date")
        original = self.frame.set_index("Date")
        common = original.index.intersection(altered.index)
        historical = common[common < changed_from]
        self.assertGreater(len(historical), 100)
        np.testing.assert_allclose(
            original.loc[historical, self.features].to_numpy(dtype=float),
            altered.loc[historical, self.features].to_numpy(dtype=float),
            rtol=1e-10, atol=1e-10, equal_nan=True,
        )

    def test_date_partitions_and_outcome_purging(self):
        """No training outcome can reach the next partition's forecast date."""
        train, val, test = pipeline.split_dataset(self.frame.copy())
        for name, part in (("train", train), ("validation", val), ("test", test)):
            with self.subTest(partition=name):
                self.assertGreater(len(part), 100)
                self.assertTrue(pd.to_datetime(part["Date"]).is_monotonic_increasing)
        self.assertTrue((pd.to_datetime(train["Date"]) <= pd.Timestamp("2021-12-31")).all())
        self.assertTrue((pd.to_datetime(val["Date"]) > pd.Timestamp("2021-12-31")).all())
        self.assertTrue((pd.to_datetime(val["Date"]) <= pd.Timestamp("2023-12-31")).all())
        self.assertTrue((pd.to_datetime(test["Date"]) > pd.Timestamp("2023-12-31")).all())
        self.assertLess(pd.to_datetime(train["TargetDate"]).max(),
                        pd.to_datetime(val["Date"]).min())
        self.assertLess(pd.to_datetime(val["TargetDate"]).max(),
                        pd.to_datetime(test["Date"]).min())
        date_sets = [set(pd.to_datetime(p["Date"])) for p in (train, val, test)]
        self.assertFalse(date_sets[0] & date_sets[1])
        self.assertFalse(date_sets[0] & date_sets[2])
        self.assertFalse(date_sets[1] & date_sets[2])

    def test_scaler_is_fitted_only_on_training_features(self):
        """Later distribution shifts must leave training scaler statistics intact."""
        # A compact independent feature matrix makes the expected fit transparent.
        n_features = len(self.features)
        self.assertGreater(n_features, 0)
        base = np.arange(1.0, 1.0 + 8 * n_features).reshape(8, n_features)
        train = pd.DataFrame(base, columns=self.features)
        val = pd.DataFrame(base[:3] + 10_000.0, columns=self.features)
        test = pd.DataFrame(base[:2] - 10_000.0, columns=self.features)
        for p in (train, val, test):
            p["target_return"] = np.arange(len(p), dtype=float) / 10.0
        arrays = pipeline.make_arrays(train, val, test)
        for key in ("X_train", "X_val", "X_test", "y_train", "y_val", "y_test", "scaler"):
            self.assertIn(key, arrays)
        np.testing.assert_allclose(arrays["scaler"].mean_, base.mean(axis=0))
        np.testing.assert_allclose(arrays["scaler"].scale_, base.std(axis=0, ddof=0))
        np.testing.assert_allclose(np.asarray(arrays["X_train"]).mean(axis=0),
                                   np.zeros(n_features), atol=1e-12)
        np.testing.assert_allclose(arrays["X_val"], arrays["scaler"].transform(val[self.features]))
        np.testing.assert_allclose(arrays["X_test"], arrays["scaler"].transform(test[self.features]))
        np.testing.assert_allclose(arrays["y_train"], train["target_return"].to_numpy())
        np.testing.assert_allclose(arrays["y_val"], val["target_return"].to_numpy())
        np.testing.assert_allclose(arrays["y_test"], test["target_return"].to_numpy())


class SavedArtifactTests(unittest.TestCase):
    """Recompute published scores from saved row-level predictions using NumPy."""

    @classmethod
    def setUpClass(cls):
        cls.results = PROJECT_ROOT / "results"
        needed = [cls.results / name for name in (
            "metrics.csv", "validation_predictions.csv", "test_predictions.csv")]
        if not all(p.exists() for p in needed):
            raise unittest.SkipTest("Run the training pipeline to create saved predictions and metrics")
        cls.scores = pd.read_csv(cls.results / "metrics.csv")
        cls.predictions = {
            split: pd.read_csv(cls.results / f"{split}_predictions.csv",
                               parse_dates=["Date", "TargetDate"])
            for split in ("validation", "test")
        }
        cls.models = ["zero_return", "training_mean", "ridge", "xgboost",
                      "keras", "fastai", "tabnet", "flash", "blend"]

    def test_saved_metrics_equal_independent_numpy_calculation(self):
        self.assertEqual(len(self.scores), 2 * len(self.models))
        self.assertFalse(self.scores.duplicated(["model", "split"]).any())
        for split, data in self.predictions.items():
            self.assertTrue(set(self.models).issubset(data.columns))
            y = data["target_return"].to_numpy(dtype=float)
            self.assertTrue(np.isfinite(y).all())
            for model in self.models:
                with self.subTest(split=split, model=model):
                    pred = data[model].to_numpy(dtype=float)
                    self.assertTrue(np.isfinite(pred).all())
                    residual = pred - y
                    expected = {
                        "RMSE": np.sqrt(np.mean(residual ** 2)),
                        "MAE": np.mean(np.abs(residual)),
                        "R2": 1.0 - np.sum(residual ** 2) / np.sum((y - y.mean()) ** 2),
                        "direction_accuracy": np.mean((y > 0) == (pred > 0)),
                        "bias": np.mean(residual),
                    }
                    rows = self.scores.loc[(self.scores.model == model)
                                           & (self.scores.split == split)]
                    self.assertEqual(len(rows), 1)
                    saved = rows.iloc[0]
                    self.assertEqual(int(saved["n"]), len(y))
                    for key, value in expected.items():
                        # The model API uses float32 targets, while CSV retains
                        # the original float64 target. Allow only rounding scale.
                        np.testing.assert_allclose(float(saved[key]), value,
                                                   rtol=2e-6, atol=2e-8,
                                                   err_msg=f"{split}/{model}/{key}")

    def test_prediction_dates_are_ordered_unique_and_disjoint(self):
        val, test = (self.predictions[s] for s in ("validation", "test"))
        for split, data in self.predictions.items():
            with self.subTest(split=split):
                self.assertTrue(data["Date"].is_unique)
                self.assertTrue(data["Date"].is_monotonic_increasing)
                self.assertTrue((data["TargetDate"] > data["Date"]).all())
                self.assertTrue(data["TargetDate"].is_unique)
                self.assertTrue((data["TargetDate"] <= pd.Timestamp("2026-11-10")).all())
        self.assertFalse(set(val["Date"]) & set(test["Date"]))
        self.assertFalse(set(val["TargetDate"]) & set(test["TargetDate"]))
        self.assertLess(val["TargetDate"].max(), test["Date"].min())

    def test_saved_targets_agree_with_source_prices(self):
        raw_path = PROJECT_ROOT / "data" / "raw" / "nifty_commodities_complete_ohlc.csv"
        if not raw_path.exists():
            self.skipTest("Raw source CSV not available")
        raw = pd.read_csv(raw_path).rename(columns=str.title)
        raw["Date"] = pd.to_datetime(raw["Date"])
        raw = raw.sort_values("Date")
        expected = pd.DataFrame({
            "Date": raw["Date"],
            "TargetDate": raw["Date"].shift(-1),
            "Close": raw["Close"],
            "target_return": 100.0 * (raw["Close"].shift(-1) / raw["Close"] - 1.0),
        }).set_index("Date")
        for split, data in self.predictions.items():
            with self.subTest(split=split):
                actual = data.set_index("Date")
                reference = expected.loc[actual.index]
                pd.testing.assert_series_equal(actual["TargetDate"], reference["TargetDate"],
                                               check_names=False)
                np.testing.assert_allclose(actual["Close"], reference["Close"], rtol=1e-10)
                np.testing.assert_allclose(actual["target_return"], reference["target_return"],
                                           rtol=1e-10, atol=1e-10)


if __name__ == "__main__":
    unittest.main()
