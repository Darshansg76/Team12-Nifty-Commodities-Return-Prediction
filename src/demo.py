"""Historical checkpoint inference for dates in the frozen evaluated test set.

Examples, from the project folder:
    python src/demo.py
    python src/demo.py --date 2024-02-01 --model xgboost
    python src/demo.py --all

This command never fits a scaler or model and does not produce a live forecast.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from model_adapters import load_predict
from pipeline import FEATURE_COLUMNS, build_features


ROOT = Path(__file__).resolve().parents[1]
MODEL_NAMES = ["zero_return", "training_mean", "ridge", "xgboost", "keras", "fastai", "tabnet", "flash", "blend"]
TOLERANCE = 1e-5


def historical_inputs(root: Path = ROOT):
    """Rebuild inputs from the frozen source and load, without fitting, its scaler."""
    root = Path(root)
    result_path = root / "results" / "test_predictions.csv"
    if not result_path.exists():
        raise FileNotFoundError("Run src/pipeline.py first; frozen test predictions are required.")
    predictions = pd.read_csv(result_path, parse_dates=["Date", "TargetDate"])
    summary = json.loads((root / "results" / "run_summary.json").read_text(encoding="utf-8"))
    data_summary = json.loads((root / "results" / "data_summary.json").read_text(encoding="utf-8"))
    source = root / "data" / "raw" / "nifty_commodities_complete_ohlc.csv"
    actual_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual_hash != data_summary["raw_sha256"]:
        raise ValueError("Raw data changed after evaluation; use the frozen project source for this demo.")
    # The downloaded CSV uses lowercase names; build_features expects title case.
    raw = pd.read_csv(source).rename(columns=str.title)
    raw["Date"] = pd.to_datetime(raw["Date"])
    raw = raw.loc[raw.Date <= pd.Timestamp(data_summary["raw_end"])]
    features = build_features(raw).set_index("Date", drop=False)
    saved_columns = json.loads((root / "models" / "features.json").read_text(encoding="utf-8"))
    if saved_columns != FEATURE_COLUMNS:
        raise ValueError("Saved feature order differs from the pipeline's feature order.")
    if predictions.Date.duplicated().any():
        raise ValueError("Frozen test predictions contain duplicate feature dates.")
    scaler = joblib.load(root / "models" / "scaler.joblib")
    return predictions, features, scaler, summary


def predict_saved(name: str, X: np.ndarray, root: Path = ROOT) -> np.ndarray:
    """Inference only, including saved development choices for the ensemble."""
    root = Path(root)
    x = np.asarray(X, dtype=np.float32)
    if name == "zero_return":
        return np.zeros(len(x), dtype=float)
    if name == "training_mean":
        train = pd.read_csv(root / "data" / "processed" / "train.csv", usecols=["target_return"])
        # This is the exact float32 mean used in pipeline.main, not a refit.
        constant = float(train.target_return.to_numpy(dtype=np.float32).mean())
        return np.full(len(x), constant, dtype=float)
    if name == "ridge":
        return np.asarray(joblib.load(root / "models" / "ridge.joblib").predict(x), dtype=float).reshape(-1)
    if name == "blend":
        choice = json.loads((root / "results" / "blend_selection.json").read_text(encoding="utf-8"))
        weight = float(choice["xgboost_weight"])
        deep = choice["deep_component"]
        # Apply precisely the validation-selected component and frozen weight.
        return weight * predict_saved("xgboost", x, root) + (1.0 - weight) * predict_saved(deep, x, root)
    if name not in MODEL_NAMES:
        raise ValueError(f"Unknown model: {name}")
    return load_predict(name, x, root / "models" / name)


def replay(feature_date: str | None = None, model: str | None = None, all_models: bool = False,
           root: Path = ROOT) -> dict:
    """Run a frozen historical date and verify checkpoint/save-file agreement."""
    saved, features, scaler, summary = historical_inputs(root)
    chosen_date = saved.Date.max() if feature_date is None else pd.Timestamp(date.fromisoformat(feature_date))
    selected_rows = saved.loc[saved.Date == chosen_date]
    if len(selected_rows) != 1:
        first = saved.Date.min().date().isoformat()
        last = saved.Date.max().date().isoformat()
        raise ValueError(f"Choose an evaluated test feature date between {first} and {last}; no saved result exists for {chosen_date.date()}.")
    saved_row = selected_rows.iloc[0]
    row = features.loc[[chosen_date]]
    if pd.Timestamp(row.TargetDate.iloc[0]) != saved_row.TargetDate:
        raise ValueError("Rebuilt target date differs from the frozen historical result.")
    if not np.isclose(float(row.target_return.iloc[0]), float(saved_row.target_return), rtol=0, atol=1e-7):
        raise ValueError("Rebuilt historical observation differs from the frozen result.")
    X = scaler.transform(row[FEATURE_COLUMNS]).astype(np.float32)
    names = MODEL_NAMES if all_models else [model or summary["selected_model"]]
    forecasts = []
    for name in names:
        prediction = float(predict_saved(name, X, root)[0])
        stored = float(saved_row[name])
        difference = abs(prediction - stored)
        if difference >= TOLERANCE:
            raise AssertionError(f"{name}: checkpoint differs from saved prediction by {difference:.8g} pp.")
        forecasts.append({"model": name, "forecast_percent": prediction,
                          "saved_prediction_percent": stored, "absolute_difference_pp": difference})
    return {"mode": "historical replay of frozen evaluated test date",
            "feature_date": chosen_date.date().isoformat(),
            "target_date": saved_row.TargetDate.date().isoformat(),
            "observed_return_percent": float(saved_row.target_return),
            "validation_selected_model": summary["selected_model"],
            "comparison_tolerance_pp": TOLERANCE, "forecasts": forecasts}


def main():
    parser = argparse.ArgumentParser(description="Historical inference from saved checkpoints on frozen test dates; no refitting.")
    parser.add_argument("--date", help="Evaluated feature date as YYYY-MM-DD; default: last test feature date.")
    parser.add_argument("--model", choices=MODEL_NAMES, help="Default: model selected using validation RMSE.")
    parser.add_argument("--all", action="store_true", help="Infer all nine models on the selected historical date.")
    args = parser.parse_args()
    try:
        result = replay(args.date, args.model, args.all)
    except (ValueError, FileNotFoundError, AssertionError) as exc:
        parser.error(str(exc))
    print("Historical replay from saved models (frozen evaluated test dates)")
    print(f"Feature date: {result['feature_date']} after the official close")
    print(f"Target date:  {result['target_date']}")
    print(f"Observed historical return: {result['observed_return_percent']:+.6f}%")
    print(f"Validation-selected model: {result['validation_selected_model']}")
    print()
    print(f"{'Model':<16} {'Forecast (%)':>14} {'Difference from saved (pp)':>28}")
    for row in result["forecasts"]:
        print(f"{row['model']:<16} {row['forecast_percent']:>+14.6f} {row['absolute_difference_pp']:>28.3g}")
    print(f"All displayed checkpoint predictions agree with the frozen results within {TOLERANCE:g} percentage points.")


if __name__ == "__main__":
    main()
