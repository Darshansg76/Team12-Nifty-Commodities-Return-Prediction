# Nifty Commodities Benchmark Return Prediction

Team 12 mini project for Machine Learning with Business Data, UE24AM342AA4.

| Member | SRN |
|---|---|
| Darshan Govekar | PES1UG24AM355 |
| Dhanraj Rathod | PES1UG24AM359 |
| Shridhar Umesh Golipalle | PES1UG25AM814 |

## Start here

- [Project report PDF](deliverables/Team_12_Project_Report.pdf) and [editable Word report](deliverables/Team_12_Project_Report.docx).
- [PowerPoint presentation](deliverables/Team_12_Presentation.pptx), including speaker notes and editable tables/charts.
- [Executed analysis notebook](notebooks/Team_12_Analysis.ipynb), including real data checks, EDA and comparison outputs.
- [Viva preparation](docs/VIVA_GUIDE.md) and [requirement coverage](docs/REQUIREMENTS_COVERAGE.md).

All five required frameworks were trained on real official index observations: XGBoost, Keras 3, fastai, PyTorch TabNet and Lightning Flash. Three baselines and a validation-selected blend complete the comparison. Synthetic fixtures occur only in software tests.

## What the experiment found

The validation rule selects a blend of **10% XGBoost and 90% TabNet**. On 709 frozen test observations from 2024 onward, its RMSE is **1.179378 percentage points**, MAE **0.846268**, R2 **0.002145**, and derived direction accuracy **51.48%**. This represents very weak return predictability. The zero-return RMSE is 1.181296 pp, so the blend improves RMSE by just 0.001918 pp. The training-mean direction benchmark scores 55.71%, above the blend.

Keras has the lowest retrospective test RMSE, 1.172971 pp. The project keeps the earlier validation selection and reports this distinction. No trading profit or reliable investment signal is claimed. Every model's signed scores appear in [metrics.csv](results/metrics.csv).

## Data and forecast definition

The source is NSE Indices Limited's Nifty Commodities **equity price index**, not commodity spot prices or a total return index. The downloader retains 4,182 observations from 2010 through 9 November 2026. The first 538 sessions lack official open/high/low, so modeling uses the continuous complete era of 3,644 sessions beginning 27 February 2012. The request freeze is 10 November 2026, which was a trading holiday. All raw responses and hashes are retained in [provenance.json](data/raw/provenance.json).

After the official close of session t, predict `100 * (Close[next observed session] / Close[t] - 1)`. Features contain only current or past OHLC and known calendar information. Twenty-three features produce 3,584 labeled rows after warm-up. The purged partitions contain 2,380 training rows, 493 validation rows and 709 test rows, with two boundary rows excluded.

Training ends in 2021. Validation covers 2022-2023. The final test starts in 2024. All frameworks share three expanding pre-2022 outer folds, with 252 scoring sessions and a separate 126-session inner stopping period per fold. Scaling fits only the corresponding fitting block. Final test labels never enter framework adapters or blend selection.

## Run the prepared project

In PowerShell from this folder:

```powershell
.\.venv\Scripts\python.exe src\demo.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The historical demo loads actual saved checkpoints, reconstructs features and checks the predictions against saved results. Its default is the final evaluated feature date. It is a frozen historical replay.

To reproduce the full experiment:

```powershell
.\run_all.ps1
```

On another computer, install Python 3.12, then run `./setup.ps1` first, or create a virtual environment and `pip install -r requirements.txt`. The prepared environment is local and excluded from Git and the ZIP. Default training uses the included frozen data. `./run_all.ps1 -RefreshData` explicitly repeats the source requests through the same cutoff.

See [reproducibility instructions](docs/REPRODUCIBILITY.md) for the document, presentation and environment details. All **13 tests pass**, including actual checkpoint reload checks for the five frameworks. See [validation evidence](docs/VALIDATION.md).

## Folder contents

| Folder | Contents |
|---|---|
| `src` | Downloader, causal training pipeline, actual framework adapters, saved-model demo |
| `data/raw` | Official JSON responses, two CSV snapshots and provenance hashes |
| `data/processed` | Engineered features and purged chronological partitions |
| `models` | Final and fold checkpoints, train-only scaler, metadata and signed prediction caches |
| `results` | Per-row predictions, validation/test metrics, CV scores, annual diagnostics and figures |
| `notebooks` | Executed analysis notebook |
| `deliverables` | Report and presentation |
| `references` | Source inventory, course mappings and official factsheet |
| `tests` | Causality, independent saved-score checks and model reload checks |
| `scripts` | Reusable notebook, report and slide builders |

## Assignment and GitHub

The supplied specific Nifty Commodities brief controls the topic despite a conflicting ID 12 title in the generic list. [Source decisions](docs/SOURCE_DECISIONS.md) record this and the user's clarification permitting AI assistance.

The completed project is published at [Darshansg76/Team12-Nifty-Commodities-Return-Prediction](https://github.com/Darshansg76/Team12-Nifty-Commodities-Return-Prediction). The repository is **private**, and `main` is the default branch. The local repository tracks `origin/main`. To share it for viva, grant the instructor or teammates repository access through GitHub. After future local commits, `./publish_github.ps1` pushes updates to the existing origin.

Official data and teaching materials retain their respective owners' rights. Course PDFs are referenced by filename and physical page number; original lecture files are not bundled in this repository.

