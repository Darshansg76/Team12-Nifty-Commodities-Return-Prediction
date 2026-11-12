# Nifty Commodities return prediction

Team 12 · Machine Learning with Business Data

| Member | SRN |
|---|---|
| Darshan Govekar | PES1UG24AM355 |
| Dhanraj Rathod | PES1UG24AM359 |
| Shridhar Umesh Golipalle | PES1UG25AM814 |

We ask whether the Nifty Commodities index price history can predict its **next trading-session percentage return**. For example, a close moving from 5,000 to 5,050 is a 1% return. This is regression because the answer is a number. The index tracks listed companies in commodity-related industries.

## Start here

Open [the presentation](deliverables/Team_12_Presentation.pptx) for the complete explanation in 16 slides. The [PDF report](deliverables/Team_12_Project_Report.pdf) gives the detailed methodology and results; [the executed notebook](notebooks/Team_12_Analysis.ipynb) shows calculations and graphs.

From this project folder in PowerShell, run:

```powershell
.\run_demo.ps1
```

This loads the selected saved model and shows one real historical forecast beside its observed outcome. It does not retrain or claim to predict a new live session. Use `.\run_demo.ps1 -All` to compare every saved candidate.

## How the project works

1. **Prepare the data.** Official NSE Indices history has 4,182 sessions. The first 538 lack open/high/low, leaving 3,644 complete sessions from 27 February 2012 to 9 November 2026. No prices are invented.
2. **Explore the data.** Inspect returns, changing volatility and feature correlations. Distribution statistics use training data.
3. **Create 23 clues.** Features describe recent returns, averages/risk, daily price structure and trend/calendar information. They use only the current or earlier session. The weekday uses a seven-day cycle because the source includes 18 special weekend sessions.
4. **Train the five required frameworks.** XGBoost uses decision trees. Keras, fastai and Lightning Flash use small neural networks. TabNet uses attention to select useful features. All receive the same inputs and dates.
5. **Choose on validation, then evaluate on test.** Training is before 2022; validation is 2022–2023; test is 2024 onward. Scaling learns from training only. Three earlier time periods provide additional checks. Early stopping ends training when validation error stops improving.
6. **Compare and explain.** RMSE/MAE measure error; R² measures fit. We also compare simplicity and transparency. Zero return, training mean and Ridge are baselines. An optional weighted blend checks whether combining models helps; TreeSHAP explains XGBoost forecasts.

## What the experiment found

Validation selected **fastai**. The later test contains **709 observations**:

| Candidate | RMSE (pp) | MAE (pp) | R² |
|---|---:|---:|---:|
| Zero return | 1.1813 | 0.8428 | -0.0011 |
| Training mean | 1.1807 | 0.8385 | -0.0001 |
| Ridge | 1.1887 | 0.8482 | -0.0137 |
| XGBoost | 1.1786 | 0.8379 | 0.0034 |
| Keras | 1.1667 | 0.8485 | 0.0235 |
| fastai | 1.1821 | 0.8329 | -0.0025 |
| TabNet | 1.2013 | 0.8306 | -0.0354 |
| Lightning Flash | 1.1741 | 0.8329 | 0.0110 |
| Optional blend | 1.1821 | 0.8329 | -0.0025 |

Lower RMSE/MAE and higher R² are better. RMSE and MAE are in return percentage points. A negative R² is valid and means the model misses more variation than the retrospective evaluation-mean reference.

**The results show little reliable forecasting power.** Keras has the lowest test RMSE, but we retain the model chosen earlier on validation. The optional blend is 0% XGBoost and 100% fastai here, so it gives no extra gain. One index and one final test era limit the conclusion. No trading profit is established.

## Rebuild the complete project

```powershell
.\run_all.ps1
```

This retrains all models, runs the checks, executes the notebook, rebuilds Word/PDF/PPT, refreshes this summary and checksums, and recreates `Team_12_Completed_Project.zip` beside the project folder. Every training run fits models again; old prediction caches are not reused. Normal runs use the included frozen data.

The prepared computer has the Python environment and Codex authoring runtime. On a new computer with Python 3.12, use `.\setup.ps1`, then `.\run_all.ps1 -ResultsOnly` for training, checks and the notebook. Full slide/report authoring also needs the runtime described in [reproduction details](docs/REPRODUCIBILITY.md). The finished Word, PDF and PPT open independently of that runtime.

## Where the code is

| File or folder | Purpose |
|---|---|
| `src/pipeline.py` | Six commented steps: load, features, historical checks, train, select, evaluate |
| `src/model_adapters.py` | Training and saved-model loading for each framework |
| `src/demo.py` | Replay a saved prediction without training |
| `src/download_data.py` | Optional official-data download |
| `data` | Original data, source hashes and prepared partitions |
| `models` | Trained checkpoints and the saved feature scaler |
| `results` | Predictions, metrics and figures |
| `scripts` | Builders for the notebook, report, PPT and ZIP |

The [private GitHub repository](https://github.com/Darshansg76/Team12-Nifty-Commodities-Return-Prediction) contains the code and deliverables. Other people need repository access to open it. Course mappings and the original-source inventory are in `references`; assignment coverage and technical details are in `docs`.
