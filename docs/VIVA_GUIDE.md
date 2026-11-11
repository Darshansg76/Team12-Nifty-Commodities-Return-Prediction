# Team 12 viva preparation

## Team identity

The supplied team allocation PDF, PDF page 2, lists Team 12 and Project ID 12. The names and SRNs are:

| Member | SRN |
|---|---|
| Darshan Govekar | PES1UG24AM355 |
| Dhanraj Rathod | PES1UG24AM359 |
| Shridhar Umesh Golipalle | PES1UG25AM814 |

Course: Machine Learning with Business Data, UE24AM342AA4.

Project: **Nifty Commodities Benchmark Return Prediction**.

## A 60-second opening

"Our project predicts the Nifty Commodities price index's next observed trading-session return from information available at the previous session's close. We convert daily OHLC data into lagged return, momentum, volatility, price-range and calendar features. We compare the five frameworks requested in the brief: XGBoost, Keras, fastai, TabNet and Lightning Flash. We also include zero-return, historical-mean and Ridge baselines, plus a validation-selected blend. We preserve time order, fit the scaler only on training data, purge boundary targets and keep a later test period out of training and selection. We compare regression error with implementation simplicity and transparency. Our conclusions follow the saved predictions, including cases where a simple baseline performs better than a complex model."

Before presenting, read the exact experiment values from `results/run_summary.json`, `results/metrics.csv` and `results/data_summary.json`. Do not substitute example accuracies or timings from the teaching slides.

## Questions everyone should be able to answer

### What exactly are you predicting?

The target at feature date t is:

`target_return[t] = 100 * (Close[next observed session] / Close[t] - 1)`

It is a numeric return in percentage points. If the index moves from 5,000 to 5,050, the target is 1.0, meaning a 1% return. `Date` is the date whose closing information forms the features. `TargetDate` is the later date at which the outcome becomes known. It is the next observed session, which can be several calendar days later after a holiday.

### Is Nifty Commodities the price of gold, crude oil or a commodity futures contract?

No. The project follows the assigned Nifty Commodities equity benchmark. The input prices are index points. We use the price index series, so the target excludes reinvested dividends. See the official index link in the brief and the downloaded provenance for the precise index definition.

### Why regression instead of classification?

The brief permits regression/classification and requests RMSE, R-squared and MAE. Predicting a continuous return directly supports those metrics. Directional accuracy is an additional diagnostic obtained by comparing the signs of predicted and realized returns. It is not the primary regression objective.

### Why forecast returns rather than tomorrow's price level?

Price levels trend and can make naive persistence look extremely accurate. Returns state the actual one-session change being forecast and allow meaningful comparison with a zero-return baseline. Returns can still change distribution over time; this transformation does not guarantee stationarity.

### At what time is the prediction available?

After the official close of feature date t. Today's close, high and low are then known. The predicted outcome is the next observed session's close-to-close return. A forecast computed with today's close does not by itself prove that a trader can execute at that same close.

### What prevents information leakage?

- All rolling features use the present or earlier sessions only.
- The following session's close is used only to construct the target.
- Train, validation and test partitions follow date order.
- Rows with target dates reaching the next partition's first feature date are removed at the boundary.
- The StandardScaler is fitted only on training features and reused on later data.
- Test labels are not passed to the framework training adapters.
- Blend weights and the selected model use validation scores only.

The tests check feature prefix invariance, robustness to changing future prices, target alignment, strict partition boundaries and training-only scaling. Saved-score tests independently recompute the reported metrics.

### What are the chronological periods?

The code assigns feature dates through 31 December 2021 to training, 2022-2023 to validation and dates after 31 December 2023 to test. Boundary purging makes the actual last eligible feature date slightly earlier. The data freeze is 10 November 2026. Read actual first/last dates and sample counts from `results/data_summary.json`; do not assume every calendar date is a trading day.

### Why not randomly shuffle the train/test split?

Random splitting would mix later market regimes into training and earlier observations into testing. A live forecaster only has the past. Unit 1 PDF page 81 requires respecting real-world event order, and Unit 2 PDF page 59 explicitly recommends TimeSeriesSplit for time-series data and a separate untouched test set.

### Can training batches be shuffled in a neural network?

Yes, within a fixed historical training partition for these tabular models. Each feature vector already contains its historical information, and the networks do not maintain hidden state across rows. Shuffling those training examples does not move validation/test observations into training. This differs from randomly assigning rows to partitions.

### Why purge a boundary observation?

A feature row's target belongs to a later session. A split made only on feature dates can therefore let a training outcome reach the next partition. The explicit `TargetDate < next_partition_first_Date` rule enforces a conservative chronological separation.

### Why are the model inputs scaled?

The dense neural networks and the Ridge baseline benefit from comparable feature magnitudes. Scaling is fitted on training data only. Trees generally do not require scaling, but using the same fixed numeric representation here preserves a common input contract. Scaling does not create additional predictive information.

### What are the 23 features?

Use `FEATURE_COLUMNS` in `src/pipeline.py` as the authoritative list. The groups are current and lagged returns; 5/10/20-session momentum; 5/20-session volatility, mean return and close-to-moving-average distance; intraday return, range and overnight gap; 14-session RSI; 60-session drawdown; and cyclical weekday/month encodings. Their construction is causal. These are engineered OHLC features rather than external macroeconomic or constituent-level inputs.

### Did you remove outliers?

Genuine extreme market observations should remain. The ingestion and feature pipeline check invalid, missing and inconsistent price fields, while EDA describes the return distribution and volatility. Distinguish a bad record from a real market shock. Use the saved provenance to explain any rows excluded because the official source lacked required OHLC values.

### How do the five requested frameworks differ?

| Framework | Implementation to explain |
|---|---|
| XGBoost | Regularized boosted regression trees with squared-error objective, histogram tree construction and validation monitoring. Each new tree corrects remaining error. |
| Keras | Keras 3 Sequential dense network with the PyTorch backend, hidden layers of 64 and 32 ReLU units, dropout, L2 regularization and MSE training. Keras is the API used; TensorFlow is not required by this implementation. |
| fastai | A real fastai `TabularPandas`/`tabular_learner` regression pipeline on PyTorch, with numerical inputs and a 64/32 dense network. No categorical embeddings are needed because the engineered inputs are numeric. |
| TabNet | A real `pytorch-tabnet` `TabNetRegressor`, using sequential attention and sparse feature-selection masks rather than an ordinary dense architecture. |
| Lightning Flash | A real `flash.core.model.Task` subclass trained with `flash.Trainer`, using a custom dense regression backbone. This is the framework's generic Task API, not its optional tabular-classification backbone. |

Read each model's metadata before the viva for actual versions, hyperparameters, epoch counts, best checkpoint and elapsed training time. If code or configurations change, the saved metadata takes precedence over this explanatory guide.

### Are the neural models identical, and is the comparison fair?

The frameworks share the same feature columns, target, chronological observations and primary metric. The dense models use comparable compact networks; TabNet has a different architecture by design. Optimizers, regularization and framework overhead also differ. The experiment compares explicit configured workflows under a common dataset and evaluation protocol, not every possible configuration or an absolute ranking of frameworks.

### Why use early stopping?

Additional training can improve training loss while hurting generalization. Validation monitoring selects a useful stopping point and restores the best checkpoint. The main validation period has therefore influenced the model; its score is a development score. The later untouched test period gives the final evaluation. In the three expanding training-period cross-validation folds, the last 126 sessions of each training window form an inner stopping block, separated by a one-row gap. The following 252-session outer fold is scored without being used for stopping. The code checks the outcome-date separation at both boundaries.

### Why include zero-return, training-mean and Ridge baselines?

They make the forecasting task measurable. Zero return corresponds to no expected one-day movement. The training-mean baseline uses a constant estimated only from historical training targets. Ridge supplies a regularized linear relationship. A complex model must justify its added cost against those alternatives. A baseline can be the correct validation-selected model.

### What do RMSE, MAE and R-squared mean?

- `RMSE = sqrt(mean((prediction - observed)^2))`: error in return percentage points, with larger misses penalized more strongly.
- `MAE = mean(abs(prediction - observed))`: average absolute error in the same units.
- `R2 = 1 - sum((observed - prediction)^2) / sum((observed - mean(observed))^2)`: improvement over the evaluation-set mean reference used in this statistic. It can be negative on held-out data.
- `bias = mean(prediction - observed)`: average signed overprediction or underprediction.
- Directional accuracy compares `observed > 0` with `prediction > 0`; zero counts as non-positive under the saved implementation.

Do not take the absolute value of R-squared. A test R-squared below zero is a legitimate result. R-squared is not classification accuracy. Report the actual zero-return baseline separately; it is not mathematically identical to the evaluation-mean reference inside R-squared.

### Why not use MAPE?

Daily returns often approach or cross zero. Dividing by a near-zero observed return makes percentage-error measures unstable or undefined. RMSE and MAE in percentage points have a clearer interpretation here.

### How is the blend constructed?

`blend = w * XGBoost + (1 - w) * selected_deep_model`

The deep component and the convex weight are selected using validation data. The weight grid includes 0 and 1, so the procedure can choose one component alone. Read the actual component and weight from `results/blend_selection.json`. The test outcomes do not set the weight. A blend is useful only if it improves the observed comparison; averaging is not a guarantee of better forecasts.

### How do you compare simplicity, transparency and efficacy?

Simplicity concerns code, setup, dependencies and training cost. Transparency concerns how readily the fitted model can be understood and explained. Efficacy concerns the measured errors, stability and ability to beat baselines. These are separate dimensions. Do not invent a numerical score for simplicity or transparency unless it has an explicitly defined and justified rubric.

### What does SHAP establish?

TreeSHAP decomposes an XGBoost prediction into a baseline and feature contributions in the model's output units. Mean absolute contributions summarize the magnitude of feature influence across the stated explanation sample. A local signed contribution says how a feature changes one model prediction relative to that baseline. Correlated engineered inputs complicate attribution. SHAP is a model explanation, not evidence that a feature causes market returns. Check additivity against the same boosting iteration range used for prediction.

### Why can a daily-return model perform poorly even when the code is correct?

The available price history may contain little usable signal about the next session, unexpected events can dominate, and feature/return relationships can change across periods. A small dataset, one seed, limited search and one benchmark also constrain conclusions. A measured weak result is a finding. Do not change the test split to obtain a more attractive number.

### What would you improve next?

Use rolling retraining, more outer chronological folds, multiple random seeds, and carefully time-aligned external features. The current cross-validation already separates its inner stopping block from its outer evaluation fold. Consider a separate total-return target or longer horizons as explicitly different experiments. Any added source must have known historical availability. Cost-aware trading simulation is a separate task requiring an investable instrument and defensible execution assumptions.

### Is the work reproducible after copying the folder?

The package includes source data/provenance, processed partitions, feature definitions, scripts, saved models, row-level predictions, metrics and environment specifications. Use the README for the exact supported commands. The offline artifacts permit examination without downloading again. A complete retraining requires the recorded dependencies. Before showing a GitHub repository, verify its real URL and upload status; a local folder or prepared Git command is not a published repository.

## Suggested rehearsal sequence

This is a preparation allocation, not a claim about who originally performed each task.

1. Darshan: frame the target, explain the index/data and walk through one target-alignment example.
2. Dhanraj: explain features, chronological partitions, leakage checks and the five framework implementations.
3. Shridhar: explain actual results, baselines, simplicity/transparency/efficacy and limitations.
4. All three: answer the target, leakage, negative-R-squared and baseline questions without referring to notes.

## Live demonstration checklist

1. Open the final report and presentation.
2. Show `results/data_summary.json` and one row from `data/processed/test.csv` to identify `Date`, `TargetDate`, inputs and target.
3. Show `results/metrics.csv` and explain the validation selection before looking at the descriptive test ranking.
4. Show the row-level saved test predictions and an explanation figure.
5. Run `python -m unittest discover -s tests -v` in the recorded environment.
6. Explain the actual repository URL and any submission action still remaining. Avoid starting a full download or retraining during a short viva unless requested.
