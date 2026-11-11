# Units 1 and 2: course-to-project mapping

Project: Nifty Commodities Benchmark Return Prediction, Team 12.

Page numbers below are **1-based PDF page positions** in the supplied merged files, not the smaller slide numbers printed within individual decks. These are course references and proposed implementation applications. They do not claim that a particular model has already been trained or has achieved a result.

## Unit 1 - problem framing, data quality and regression

| Supplied course content | Exact PDF pages | Application to this project |
|---|---:|---|
| Commodity forecasting is a tabular business use case | `unit 1 merged.pdf`, p. 13 | Define a concrete forecasting decision and the predicted numeric quantity before selecting a model. A benchmark return is not a commodity futures price. |
| Feature engineering, correlated inputs and nonlinear interactions | pp. 21-22 | Derive historical return, momentum, range and volatility features using only observations available when the forecast is made. Document units and availability of every input. |
| Missing values and the need to diagnose their origin | p. 40 | Separate non-trading dates, missing observations and rolling-window warm-up values. Report missing counts and the chosen handling policy. Avoid inventing observations. |
| Distributions and outliers | p. 41 | Inspect return distributions and extreme observations. Preserve genuine market shocks. Investigate errors before removal and record any exclusions. |
| Row identity, independence and granularity | pp. 43-45 | Use one row per observed trading session, date as a unique key, and explicitly acknowledge serial dependence. Check duplicates, ordering and alignment. |
| Row and column audit | p. 50 | Save the input row count, date coverage, dtypes, missingness, duplicates and target distribution as an auditable data-quality summary. |
| Time order as a leakage remedy | p. 81 | Split chronologically. All training outcomes must be known before the next validation/test forecast. Do not shuffle time-series rows. |
| Comparing classical ML and deep learning; interpretability | pp. 93, 96-99 | Include a simple baseline and tree model before assuming deep learning will help. If a neural network or ensemble is used, compare it on exactly the same forecast dates and explain its actual contribution. |
| Eight-step regression workflow | p. 146 | Present data collection, preparation, split design, exploration, estimation, diagnostics, validation and business implications as a complete pipeline. |
| Hold-out evaluation and reproducibility | p. 154 | Fix random seeds, preserve a final hold-out period and report results only from data excluded from model fitting and model selection. Adapt the illustrated random split to time order. |
| Regression evaluation and uncertainty | pp. 156, 163 | Report RMSE in return units, signed test R-squared, and clearly describe any estimated prediction interval and its empirical coverage. |
| Multicollinearity | p. 170 | Inspect highly correlated momentum/return features. Use regularization or a smaller interpretable set for a linear baseline. Do not treat an unstable coefficient as a causal market explanation. |
| Common mistakes | p. 175 | Avoid calling R-squared classification accuracy, causal claims from observational features, selecting features by test performance, and deleting observations merely to improve fit. |
| Diagnostics and deployment decisions | p. 188 | Inspect residual patterns and train/validation/test gaps. State when the forecast is produced and when its target becomes observable. |

## Unit 2 - pipelines, model comparison and tuning

| Supplied course content | Exact PDF pages | Application to this project |
|---|---:|---|
| fit/predict/transform and preprocessing leakage | `unit 2 merged.pdf`, pp. 7-8 | Use fitted pipelines so imputation and scaling statistics come only from each training fold. Apply their fitted transforms to later validation/test rows. |
| Reusable preprocessing blocks | p. 14 | Reuse the same feature definitions and missing-data policy across model comparisons. Use separate appropriate preprocessing for linear/neural and tree models. |
| StandardScaler fitted on training data only | pp. 16-18, 25 | Standardize linear/neural inputs inside the training pipeline. Never standardize the entire dataset before cross-validation. |
| EDA and outlier interpretation | pp. 32-45 | Include descriptive statistics and distribution/box plots. Inspect extreme market events rather than automatically deleting them under an IQR rule. |
| Fair metrics and stability | p. 47 | Choose regression RMSE as a primary comparison metric, retain MAE and signed R-squared as supporting metrics, and report mean and standard deviation across identical validation folds. |
| Limits of ordinary KFold | p. 59 | Use expanding or rolling chronological folds such as TimeSeriesSplit. Keep an independent final test period. Account for the forecasting horizon at split boundaries. |
| Bagging, Random Forest and Extra Trees | pp. 65, 70-73, 83, 105-109 | A regularized Random Forest or Extra Trees model is a useful nonlinear comparison. Restrict complexity with leaf size/depth and evaluate on chronological folds. |
| Regression trees, overfitting and pruning | pp. 94-98 | Use regression objectives for a continuous return target. Explain why shallow trees and minimum leaf samples are appropriate for noisy financial data. |
| Gradient boosting mechanics and learning-rate trade-off | pp. 117-126, 130 | Compare boosting to a simple baseline. Tune learning rate, tree count and depth together using only development-period validation. |
| Early stopping | pp. 136-138 | Monitor a later internal validation segment drawn from training data. Do not use final test outcomes for early stopping. |
| XGBoost regularization and hyperparameters | pp. 173, 181, 183 | Specify the return-regression objective, reproducible seed and bounded search space. If early stopping is used, record the selected number of iterations. |
| Missing data | pp. 191-200, 205, 208 | Diagnose missingness first. Median imputation can serve linear/neural models; XGBoost may use native NaN routing. Record any model-specific handling. |
| Hyperparameter optimization | pp. 213-218, 221-225 | Define a search space and chronological validation scheme. A small grid suits a linear baseline; randomized/Bayesian search can serve larger spaces. Log attempted settings and avoid test-driven tuning. |

## Evaluation details that need explicit care

1. **Feature timestamp:** if features include the close of session t, the honest forecast origin is after that close. The next-session close-to-close return is `close[t+1] / close[t] - 1`. The outcome date must stay attached to every prediction.
2. **Boundary availability:** for an h-session target, exclude training rows whose outcome is not yet observable at the next forecast origin. A `gap` or explicit outcome-date check can enforce this. A gap alone does not repair forward-looking feature calculations.
3. **Baselines:** include zero return and a training-period historical mean, because noisy returns can make complex models worse than simple forecasts. Compare all models on identical rows.
4. **Target units:** store fractional returns consistently and state the conversion to percent or basis points. Avoid MAPE as a headline metric when the target frequently lies near or crosses zero.
5. **Signed R-squared:** the Unit 1 illustration on p. 156 states a 0-to-1 range and the example on p. 163 prints `abs(r2_score(...))`. For out-of-sample evaluation retain the signed value: a negative score is meaningful evidence that the model is worse than the evaluation-set mean predictor. Do not take its absolute value or clip it to zero.
6. **Honest conclusions:** improvement must be established by the actual saved predictions and measurements. Report a weak or negative result directly; completing the project does not require a profitable forecast.
7. **Association:** feature importance or SHAP explains model dependence on inputs; it does not establish a causal economic effect.

## Source inventory

- Supplied `unit 1 merged.pdf`: 234 PDF pages.
- Supplied `unit 2 merged.pdf`: 226 PDF pages.
- Full extracted text is saved in `unit_1_extracted.txt` and `unit_2_extracted.txt` beside this mapping for search and traceability. The original PDFs remain authoritative for layout and diagrams.
