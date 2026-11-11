"""Build and execute the saved-results analysis notebook without retraining.

Run with the project virtual environment. A local kernelspec is created under
.build/kernels; no Jupyter configuration is installed into the user's account.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import nbformat as nbf
from nbclient import NotebookClient
from jupyter_client import AsyncKernelManager
from jupyter_client.kernelspec import KernelSpecManager


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "Team_12_Analysis.ipynb"


def readiness_files():
    return [ROOT / name for name in (
        "results/metrics.csv", "results/run_summary.json",
        "results/cv_metrics.csv", "results/blend_selection.json",
        "results/validation_predictions.csv", "results/test_predictions.csv",
        "results/annual_test_metrics.csv", "results/data_summary.json",
        "data/raw/provenance.json", "data/raw/nifty_commodities_complete_ohlc.csv",
        "data/processed/train.csv", "data/processed/validation.csv", "data/processed/test.csv",
        "results/figures/02_eda.png", "results/figures/03_correlation.png",
        "results/figures/04_model_comparison.png", "results/figures/05_diagnostics.png",
    )]


def wait_for_artifacts(seconds):
    deadline = time.monotonic() + seconds
    while True:
        missing = [str(p.relative_to(ROOT)) for p in readiness_files() if not p.exists()]
        if not missing:
            # SHAP is optional only when the pipeline recorded its actual error.
            if not any((ROOT / "results" / p).exists() for p in
                       ("xgboost_shap_importance.csv", "shap_error.json")):
                missing = ["results/xgboost_shap_importance.csv or results/shap_error.json"]
        if not missing:
            return
        if time.monotonic() >= deadline:
            raise FileNotFoundError("Training outputs are not ready: " + ", ".join(missing))
        print(f"Waiting for {len(missing)} training artifacts; no retraining is started.", flush=True)
        time.sleep(min(10, max(0.1, deadline - time.monotonic())))


def make_notebook():
    md = nbf.v4.new_markdown_cell
    code = nbf.v4.new_code_cell
    cells = [
        md("""# Nifty Commodities benchmark return prediction

**Team 12 · Project ID 12 · Machine Learning with Business Data (UE24AM342AA4)**

| Member | SRN |
|---|---|
| Darshan Govekar | PES1UG24AM355 |
| Dhanraj Rathod | PES1UG24AM359 |
| Shridhar Umesh Golipalle | PES1UG25AM814 |

This executed notebook examines the actual saved dataset, trained-model metadata,
predictions and measurements. It performs no model fitting and makes no network
requests. The experiment predicts a continuous **next observed session return**
using information available after the previous session's close. All reported
numbers below are loaded or independently calculated from the saved artifacts.
"""),
        code("""from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd
from IPython.display import display, Markdown, Image

ROOT = Path.cwd()
if not (ROOT / 'results' / 'metrics.csv').exists() and (ROOT.parent / 'results' / 'metrics.csv').exists():
    ROOT = ROOT.parent
assert (ROOT / 'src' / 'pipeline.py').exists(), 'Run this notebook from the project folder or notebooks folder.'
sys.path.insert(0, str(ROOT))
from src.pipeline import FEATURE_COLUMNS, build_features, split_dataset

def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))

pd.set_option('display.max_columns', 16)
pd.set_option('display.max_colwidth', 95)
pd.set_option('display.float_format', lambda x: f'{x:.6f}')
provenance = read_json('data/raw/provenance.json')
summary = read_json('results/run_summary.json')
data_summary = read_json('results/data_summary.json')
scores = pd.read_csv(ROOT / 'results/metrics.csv')
raw_all = pd.read_csv(ROOT / 'data/raw/nifty_commodities_daily.csv')
raw = pd.read_csv(ROOT / 'data/raw/nifty_commodities_complete_ohlc.csv').rename(columns=str.title)
raw['Date'] = pd.to_datetime(raw['Date'])
parts = {name: pd.read_csv(ROOT / f'data/processed/{name}.csv', parse_dates=['Date', 'TargetDate'])
         for name in ['train', 'validation', 'test']}
predictions = {name: pd.read_csv(ROOT / f'results/{name}_predictions.csv', parse_dates=['Date', 'TargetDate'])
               for name in ['validation', 'test']}
display(Markdown('Artifacts loaded. This notebook reads the saved experiment without retraining.'))
"""),
        md("""## 1. Source, provenance and data quality

The provider is NSE Indices Limited. Nifty Commodities is the assigned equity
benchmark; the values below are **price index points**, not spot commodity
prices. Price returns exclude reinvested dividends. The requested data freeze
and the actual final available session can differ. Weekends, holidays and
unreturned sessions are not fabricated.

The full official response is retained. The experiment uses the complete-OHLC
subset because the initial history lacks Open/High/Low. The excluded era and
its size are shown explicitly, and genuine market shocks remain in the data.
"""),
        code("""source_overview = {
    'Provider': provenance['provider'],
    'Series': provenance['dataset'],
    'Requested start': provenance['requested_start'],
    'Requested freeze': provenance['requested_end'],
    'Actual full-source start': provenance['actual_start'],
    'Actual full-source end': provenance['actual_end'],
    'Full-source rows': len(raw_all),
    'Complete-OHLC rows': len(raw),
    'Complete-OHLC first session': raw['Date'].min().date().isoformat(),
    'Complete-OHLC last session': raw['Date'].max().date().isoformat(),
    'Excluded rows lacking OHLC': len(raw_all) - len(raw),
    'Identical duplicate dates removed at download': provenance['identical_duplicates_removed'],
}
display(pd.Series(source_overview, name='Saved source evidence').to_frame())
display(raw_all.isna().sum().rename('Full-source missing cells').to_frame())
assert raw['Date'].is_unique and raw['Date'].is_monotonic_increasing
assert np.isfinite(raw[['Open', 'High', 'Low', 'Close']]).all().all()
assert (raw[['Open', 'High', 'Low', 'Close']] > 0).all().all()
assert hashlib.sha256((ROOT / 'data/raw/nifty_commodities_complete_ohlc.csv').read_bytes()).hexdigest() == provenance['complete_ohlc_sha256']
request_hashes_verified = 0
for request in provenance['requests']:
    response_path = ROOT / 'data/raw' / request['response_file']
    assert hashlib.sha256(response_path.read_bytes()).hexdigest() == request['response_sha256']
    request_hashes_verified += 1
display(Markdown(f'CSV checksum and **{request_hashes_verified}** downloaded-response checksums verified.'))
display(Markdown(f"[Official index]({provenance['index_page']}) · [Historical data]({provenance['historical_data_page']})"))
display(raw.head())
"""),
        md("""## 2. Target, causal features and chronological partitions

At the close of feature date `t`, the target is
`100 × (Close[next observed session] / Close[t] − 1)`.
It is measured in **percentage points**: 1.0 means a 1% return. `TargetDate`
keeps the realization date attached to each prediction. The 23 input columns
exclude both `target_return` and `TargetDate`.

All rolling windows end at the feature date. The initial rolling-window warm-up
and the final unobserved target are excluded. Chronological boundaries use
feature dates through 2021, 2022–2023, and 2024 onward. A boundary row is purged
when its outcome date reaches the next partition's first feature date.
"""),
        code("""feature_groups = [
    ('Current and lagged returns', 'return_1; return_lag_1/2/3/5', '100 × close-to-close percentage change, with stated backward lags'),
    ('Momentum', 'momentum_5/10/20', '100 × (Close[t]/Close[t-window] - 1)'),
    ('Volatility', 'volatility_5/20', 'Trailing sample standard deviation of daily percentage returns'),
    ('Mean return', 'mean_return_5/20', 'Trailing mean of daily percentage returns'),
    ('Moving-average distance', 'close_to_sma_5/20', '100 × (Close[t]/trailing mean Close - 1)'),
    ('Intraday and range', 'intraday_return; range_pct; overnight_gap', 'Close/Open return; (High-Low)/Close; Open/previous Close gap'),
    ('Oscillator', 'rsi_14', 'RSI from trailing 14-session mean upward/downward price changes'),
    ('Drawdown', 'drawdown_60', '100 × (Close[t]/trailing 60-session maximum Close - 1)'),
    ('Calendar', 'weekday_sin/cos; month_sin/cos', 'Cyclical encodings computed from feature date only'),
]
display(pd.DataFrame(feature_groups, columns=['Group', 'Columns', 'Definition']))
assert len(FEATURE_COLUMNS) == 23
assert 'target_return' not in FEATURE_COLUMNS and 'TargetDate' not in FEATURE_COLUMNS
partition_table = pd.DataFrame([
    {'partition': name, 'rows': len(part), 'feature_start': part.Date.min().date(),
     'feature_end': part.Date.max().date(), 'target_end': part.TargetDate.max().date()}
    for name, part in parts.items()
])
display(partition_table)
assert parts['train'].TargetDate.max() < parts['validation'].Date.min()
assert parts['validation'].TargetDate.max() < parts['test'].Date.min()
assert parts['test'].TargetDate.max() <= pd.Timestamp('2026-11-10')
# Independently verify targets against the official close series.
reference = raw.assign(expected_target=100*(raw.Close.shift(-1)/raw.Close-1),
                       expected_date=raw.Date.shift(-1)).set_index('Date')
for part in parts.values():
    expected = reference.loc[part.Date]
    np.testing.assert_allclose(part.target_return, expected.expected_target, rtol=1e-10, atol=1e-10)
    assert np.array_equal(part.TargetDate.to_numpy(), expected.expected_date.to_numpy())
# Appending future data must not change historical feature values.
prefix = build_features(raw.iloc[:1000].copy()).set_index('Date')
complete = build_features(raw.copy()).set_index('Date')
common = prefix.index.intersection(complete.index)
np.testing.assert_allclose(prefix.loc[common, FEATURE_COLUMNS], complete.loc[common, FEATURE_COLUMNS], rtol=1e-10, atol=1e-10)
display(Markdown('Target alignment, strict boundary separation, data freeze and causal prefix invariance verified.'))
display(parts['test'][['Date', 'TargetDate', 'Close', 'return_1', 'momentum_5', 'target_return']].head())
"""),
        md("""## 3. Exploratory analysis of training observations

The distribution, volatility and correlation figures in this section use only
the training partition. Large genuine return observations are retained. Feature
correlation can make attribution unstable and motivates a regularized linear
baseline alongside nonlinear models.
"""),
        code("""training = parts['train']
eda = training.target_return.describe().to_frame('Training target return (%)')
eda.loc['skew'] = training.target_return.skew()
eda.loc['excess_kurtosis'] = training.target_return.kurt()
display(eda)
display(Markdown(f'Training sessions with a positive target return: **{(training.target_return > 0).mean():.2%}**.'))
display(Image(filename=str(ROOT / 'results/figures/02_eda.png'), width=1000))
display(Image(filename=str(ROOT / 'results/figures/03_correlation.png'), width=950))
"""),
        md("""## 4. Expanding-window validation and training-only scaling

Three expanding training-period folds each reserve a 252-session outer
evaluation block. A separate final 126-session block inside the earlier
training window monitors stopping. One-row gaps and outcome-date assertions
separate those blocks. The outer evaluation labels do not select epochs.
Scalers are fitted anew on each inner training window. The following mean and
sample standard deviation summarize the actual recorded outer-fold scores.
"""),
        code("""cv = pd.read_csv(ROOT / 'results/cv_metrics.csv')
assert not summary['cv_skipped'], 'The final notebook requires the completed cross-validation experiment.'
display(cv[['fold', 'model', 'train_n', 'early_stopping_n', 'validation_n', 'train_end', 'validation_start', 'RMSE', 'MAE', 'R2']])
cv_summary = cv.groupby('model')[['RMSE', 'MAE', 'R2', 'direction_accuracy']].agg(['mean', 'std'])
display(cv_summary)
import joblib
scaler = joblib.load(ROOT / 'models/scaler.joblib')
np.testing.assert_allclose(scaler.mean_, training[FEATURE_COLUMNS].mean().to_numpy(), rtol=1e-10, atol=1e-10)
np.testing.assert_allclose(scaler.scale_, training[FEATURE_COLUMNS].std(ddof=0).to_numpy(), rtol=1e-10, atol=1e-10)
display(Markdown('The saved final StandardScaler mean and scale match training observations only.'))
"""),
        md("""## 5. The five trained frameworks

Every framework receives the same feature definitions, training observations,
development validation observations and held-out test dates. Dense networks
and TabNet have different architectures. The comparison concerns these saved
configurations, rather than every possible configuration of each library.

Keras uses its PyTorch backend. Lightning Flash uses an actual Flash `Task` and
`Trainer` with a custom dense regression backbone, not the optional built-in
tabular-classification backbone. The runtime below concerns the saved final
development fit; it does not include all cross-validation fits or installation.
"""),
        code("""architecture_rows = []
for name in ['xgboost', 'keras', 'fastai', 'tabnet', 'flash']:
    meta = summary['models'][name]
    cfg = meta['hyperparameters']
    if name == 'xgboost':
        architecture = f\"Boosted regression trees; depth={cfg['max_depth']}; maximum trees={cfg['n_estimators']}\"
    elif name == 'tabnet':
        architecture = f\"TabNet: n_d={cfg['n_d']}, n_a={cfg['n_a']}, n_steps={cfg['n_steps']}\"
    else:
        architecture = f\"Dense hidden layers {cfg['hidden_layers']}; output=1; {cfg['activation']}\"
    architecture_rows.append({
        'model': name, 'implementation': meta['framework'], 'architecture': architecture,
        'training_rows': meta['n_train'], 'epochs_or_rounds': meta['epochs_run'],
        'best_epoch_or_round': meta['best_epoch'], 'fit_seconds': meta['elapsed_seconds'],
        'versions': ', '.join(f'{k} {v}' for k,v in meta['versions'].items()),
    })
display(pd.DataFrame(architecture_rows))
display(Markdown('Exact optimizer, learning rate, regularization and history are retained in `results/run_summary.json` and model metadata files.'))
"""),
        md("""## 6. Validation and held-out test results

The nine rows per split include the five requested frameworks, zero-return and
training-mean constants, Ridge regression and a validation-selected blend.
RMSE and MAE are in **return percentage points**. R-squared retains its sign.
Directional accuracy uses `return > 0` versus `prediction > 0`, so zero is
classified as non-positive. Bias is mean prediction minus observed return.

Validation has influenced early stopping and blend selection. Test results
describe the frozen experiment. The model recommendation was selected using
validation RMSE, before test scores were calculated.
"""),
        code("""validation_scores = scores[scores.split == 'validation'].sort_values('RMSE').reset_index(drop=True)
test_scores = scores[scores.split == 'test'].sort_values('RMSE').reset_index(drop=True)
display(Markdown('### Development validation'))
display(validation_scores)
display(Markdown('### Frozen test period'))
display(test_scores)
# Independent NumPy recomputation of all published metrics from row predictions.
for split, p in predictions.items():
    y = p.target_return.to_numpy(dtype=float)
    for name in validation_scores.model:
        prediction = p[name].to_numpy(dtype=float)
        error = prediction-y
        independent = {
            'RMSE': np.sqrt(np.mean(error**2)), 'MAE': np.mean(np.abs(error)),
            'R2': 1-np.sum(error**2)/np.sum((y-y.mean())**2),
            'direction_accuracy': np.mean((y>0)==(prediction>0)), 'bias': np.mean(error),
        }
        saved = scores[(scores.split == split) & (scores.model == name)].iloc[0]
        assert int(saved.n) == len(y)
        for metric, value in independent.items():
            np.testing.assert_allclose(saved[metric], value, rtol=2e-6, atol=2e-8)
display(Markdown('All 18 saved model/split rows agree with independent row-level metric calculations within float32 rounding.'))
display(Image(filename=str(ROOT / 'results/figures/04_model_comparison.png'), width=950))
"""),
        md("""## 7. Blend selection and the frozen recommendation

The convex blend is `w × XGBoost + (1 − w) × deep_component`. The deep component
and the weight are chosen using development validation only. The 0.0–1.0 grid
includes both component endpoints. A blend need not outperform a baseline.
The final recommendation is the minimum-validation-RMSE model across all nine
candidates. The lowest test-RMSE model is descriptive and does not replace that
selection rule.
"""),
        code("""blend = read_json('results/blend_selection.json')
display(pd.DataFrame(blend['grid']))
display(pd.Series({
    'deep_component': blend['deep_component'],
    'xgboost_weight': blend['xgboost_weight'],
    'selection_data': blend['selection_data'],
    'validation_selected_model': summary['selected_model'],
    'selection_rule': summary['selection_rule'],
    'lowest_test_RMSE_descriptive_only': summary['best_test_model_descriptive_only'],
}).to_frame('Saved decision'))
selected = summary['selected_model']
selected_val = validation_scores.set_index('model').loc[selected]
assert selected_val.RMSE <= validation_scores.RMSE.min() + 1e-10
w = blend['xgboost_weight']
for p in predictions.values():
    np.testing.assert_allclose(p['blend'], w*p['xgboost']+(1-w)*p[blend['deep_component']], rtol=1e-6, atol=1e-8)
display(Markdown(f'The frozen validation-selected recommendation is **{selected}**. Saved blend predictions reconstruct from the recorded components and weight.'))
"""),
        md("""## 8. Native XGBoost TreeSHAP explanations

The ranking below reports mean absolute TreeSHAP contributions across the
development validation sample in model-output percentage points. Additivity is
checked using the same boosting iteration range as prediction. These explain
the fitted XGBoost model, even if a different model is the final recommendation.
Correlated features share predictive information; attribution is not causation.
"""),
        code("""shap_path = ROOT / 'results/xgboost_shap_importance.csv'
if shap_path.exists():
    shap_importance = pd.read_csv(shap_path)
    display(shap_importance)
    shap_check = read_json('results/shap_check.json')
    display(pd.Series(shap_check).to_frame('Native TreeSHAP check'))
    assert float(shap_check['max_additivity_error']) < 1e-4
    figure = ROOT / 'results/figures/06_explanations.png'
    if figure.exists():
        display(Image(filename=str(figure), width=950))
else:
    display(Markdown('Native TreeSHAP was unavailable in this run. The recorded error is shown rather than an invented explanation.'))
    display(read_json('results/shap_error.json'))
"""),
        md("""## 9. Residuals and stability across test years

The diagnostic plot concerns the model selected by validation. Annual scores
are descriptive slices of the same frozen test period. They are not separate
model-selection exercises. A narrow set of near-zero predictions can still
obtain a reasonable RMSE on noisy returns, so inspect the baselines, scatter,
residual distribution and signed R-squared together.
"""),
        code("""test_predictions = predictions['test']
residual = test_predictions.target_return - test_predictions[selected]
display(residual.describe().to_frame('Observed minus predicted return (pp)'))
annual = pd.read_csv(ROOT / 'results/annual_test_metrics.csv')
display(annual)
display(Image(filename=str(ROOT / 'results/figures/05_diagnostics.png'), width=1000))
"""),
        md("""## 10. Conclusion from the saved experiment

The paragraph below is generated from the actual saved selection and test
measurements. The test-best model is not retroactively declared the selected
model. A weak or negative forecasting result remains a valid project finding.
"""),
        code("""selected_test = test_scores.set_index('model').loc[selected]
zero_test = test_scores.set_index('model').loc['zero_return']
delta = float(zero_test.RMSE-selected_test.RMSE)
comparison = ('lower' if delta > 0 else 'higher' if delta < 0 else 'equal')
display(Markdown(
    f\"Validation selected **{selected}**. On **{int(selected_test.n):,}** held-out observations, \"
    f\"its RMSE was **{selected_test.RMSE:.6f} pp**, MAE **{selected_test.MAE:.6f} pp**, \"
    f\"R² **{selected_test.R2:.6f}**, and directional accuracy **{selected_test.direction_accuracy:.2%}**. \"
    f\"Its RMSE was {comparison} than the zero-return baseline by **{abs(delta):.6f} pp**. \"
    f\"The lowest test RMSE belonged to **{summary['best_test_model_descriptive_only']}**, \"
    f\"which is a descriptive comparison rather than a new model-selection decision.\"
))
display(Markdown('### Practical interpretation'))
display(Markdown(
    'Simplicity concerns setup, code and runtime; transparency concerns how predictions can be explained; '
    'efficacy concerns the actual errors and stability. These dimensions should be discussed separately. '
    'The experiment covers one index, one feature design and one seed. Main development validation is used for '
    'stopping and blend selection. No executable trading profits or investment performance are established. '
    'Useful next experiments include rolling retraining, more time folds, multiple seeds and external features '
    'whose historical availability is known.'
))
display(pd.Series(summary['limits'], name='Recorded experiment limitations').to_frame())
"""),
        md("""## Reproduce or extend

This notebook's executed cells only inspect saved data and results. To rerun
the full experiment, activate the project environment and run the following
from the project root in a terminal:

```powershell
.\\.venv\\Scripts\\python.exe src\\pipeline.py
```

That command trains models and cross-validation folds and can take several
minutes. It was deliberately not launched by this notebook. Rebuild the
executed analysis afterward with:

```powershell
.\\.venv\\Scripts\\python.exe scripts\\build_notebook.py
```

Run checks with `python -m unittest discover -s tests -v`. See the README for
environment setup, the full report for interpretation, `docs/VIVA_GUIDE.md`
for rehearsal and the two course mapping files under `references` for the
unit-by-unit links. A GitHub upload must have a real published repository URL;
the local project folder alone does not establish that submission step.
"""),
    ]
    return nbf.v4.new_notebook(cells=cells, metadata={
        "kernelspec": {"display_name": "Python (Team 12 project environment)",
                       "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": sys.version.split()[0]},
        "team_12": {"execution": "Saved-artifact analysis only; no model retraining", "project_id": 12},
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait-seconds", type=int, default=0,
                        help="Bounded wait for the separately running training pipeline")
    args = parser.parse_args()
    wait_for_artifacts(args.wait_seconds)
    kernel_parent = ROOT / ".build" / "kernels"
    kernel_folder = kernel_parent / "team12"
    kernel_folder.mkdir(parents=True, exist_ok=True)
    (kernel_folder / "kernel.json").write_text(json.dumps({
        "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "Team 12 project build kernel", "language": "python",
        "env": {"MPLCONFIGDIR": str(ROOT / ".cache" / "matplotlib"),
                "KERAS_BACKEND": "torch", "IPYTHONDIR": str(ROOT / ".build" / "ipython")},
    }, indent=2), encoding="utf-8")
    nb = make_notebook()
    manager = AsyncKernelManager(
        kernel_name="team12",
        kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel_parent)]),
    )
    client = NotebookClient(nb, km=manager, timeout=180, allow_errors=False,
                            resources={"metadata": {"path": str(ROOT)}})
    print("Executing saved-results notebook with the project Python kernel...", flush=True)
    client.execute(cleanup_kc=True, cwd=str(ROOT))
    errors = [o for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", [])
              if o.get("output_type") == "error"]
    if errors:
        raise RuntimeError("Notebook contains execution errors")
    code_cells = [c for c in nb.cells if c.cell_type == "code"]
    if not all(c.get("execution_count") is not None for c in code_cells):
        raise RuntimeError("Notebook has an unexecuted analysis cell")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, OUTPUT)
    nbf.validate(nbf.read(OUTPUT, as_version=4))
    image_count = sum("image/png" in o.get("data", {}) for c in code_cells for o in c.get("outputs", []))
    print(f"Saved {OUTPUT.name}: {len(code_cells)} executed analysis cells, {image_count} embedded PNG outputs, no errors.", flush=True)


if __name__ == "__main__":
    main()
