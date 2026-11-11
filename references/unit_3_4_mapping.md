# Units 3 and 4: mapping to the Nifty Commodities project

All page references below are **1-based PDF page numbers**, not the slide number printed inside a slide. The mapping was verified by extracting the original supplied PDFs with `pypdf`, rather than relying only on the previously extracted reference files. The seven verified extractions are stored beside this file with `_verified.txt` suffixes.

## Source inventory

| Supplied source | PDF pages | Main content |
|---|---:|---|
| `Deep_Learning_with_Tabular_Business_Data/1.pdf` | 45 | Neural networks, training, Keras, comparison with XGBoost |
| `Deep_Learning_with_Tabular_Business_Data/3.pdf` | 36 | PyTorch stacks, TabNet, framework trade-offs |
| `Blending_XGBoost_and_Deep_Learning,_Interpretability/2.pdf` | 13 | LOWESS non-parametric regression |
| `Blending_XGBoost_and_Deep_Learning,_Interpretability/3.pdf` | 52 | XAI, interpretability, decision trees, LIME, local/global scope |
| `Blending_XGBoost_and_Deep_Learning,_Interpretability/4.pdf` | 28 | LIME principles, weighted local surrogates, limitations |
| `Blending_XGBoost_and_Deep_Learning,_Interpretability/5.pdf` | 27 | XGBoost recap and SHAP plots |
| `Blending_XGBoost_and_Deep_Learning,_Interpretability/6.pdf` | 22 | SHAP calculations and local/global explanation |

## Unit 3: Deep learning with tabular business data

| Course concept and location | Application in this project |
|---|---|
| Perceptron and multilayer networks: `1.pdf`, pp. 3-7. Page 6 describes a deep neural network as having two or more hidden layers. | Use a compact dense regression network with at least two hidden layers. State layer widths and activation functions explicitly. The output is one unrestricted continuous daily-return estimate. |
| Cost functions, squared error, gradients and Adam: `1.pdf`, pp. 11-13. | Train the dense network to minimize mean squared error with an explicit optimizer, learning rate and seed. Keep return units consistent during fitting and evaluation. |
| Framework and API levels: `1.pdf`, pp. 14-17; PyTorch definition and stacks: `3.pdf`, pp. 3, 6-7. | Implement five actual frameworks: XGBoost, Keras 3 with the PyTorch backend, fastai's tabular learner, pytorch-tabnet and a Lightning Flash core Task with a dense regression backbone. Record exact versions. Keras uses its Keras API even though the underlying tensor backend is PyTorch. |
| ML versus DL on the same problem: `1.pdf`, pp. 18-19. Fair common features: p. 25. | Give XGBoost and the dense network exactly the same eligible feature columns, target observations and chronological evaluation dates. Framework-specific scaling is acceptable when fitted only on training observations. |
| Organized cleanup/config/training/saving pipeline: `1.pdf`, pp. 23-27. | Store raw input, cleaned/engineered data, fixed configuration, model code, trained artifacts and results separately. Preserve source metadata. Exclude next-day target information from input columns. |
| Target leakage example: `1.pdf`, p. 26 excludes price because it defines the example target. | Define the Nifty target as the following trading day's close-to-close return. Feature row t may use prices known by close t; it must not use close t+1 or forward-looking rolling windows. |
| Validation, callbacks, early stopping and checkpointing: `1.pdf`, pp. 31-33. | Use a chronological validation block for neural-network epoch selection. Restore the best validation checkpoint. Keep the final test block unavailable to stopping, hyperparameter selection and blend-weight selection. |
| Simplicity, transparency and efficacy: `1.pdf`, pp. 34-42. | Compare error metrics alongside training time, model complexity, and interpretability. Do not assume DL must beat trees or that an ensemble must beat its components. Report the observed result. |
| XGBoost gain importance versus external NN explanations: `1.pdf`, p. 40. | Label gain importance accurately. Add out-of-sample permutation importance and/or SHAP to explain model behavior, with clear scope and correlation limitations. |
| TabNet's sequential attention and masks: `3.pdf`, pp. 8-16, 22-23. Framework trade-offs: pp. 32-35. | Train a real `TabNetRegressor` with decision width 8, attention width 8 and three decision steps. Save its native artifact and built-in feature importances. Compare its held-out errors and runtime with the dense models. |

## Unit 4: LOWESS, XGBoost and interpretation

| Course concept and location | Application in this project |
|---|---|
| LOWESS local weighted regression: `2.pdf`, pp. 1-4. Span controls bias/variance: p. 9. Weak extrapolation and high-dimensional limitations: p. 11. | LOWESS can support an exploratory one-variable relationship plot. If used on time-series plots, label it retrospective visualization; fitting a two-sided smoother on the full series and then treating it as a predictive feature would leak future observations. It need not be a primary multivariate forecasting model. |
| Intrinsic versus post-hoc interpretability: `3.pdf`, pp. 12-21. | Use a linear baseline or shallow tree as an interpretable comparison. Explain that XGBoost/dense-network post-hoc analysis describes learned associations and does not prove economic causation. |
| CART and impurity-based feature importance: `3.pdf`, pp. 23-28. | Document how tree splits and gain/impurity importance differ from permutation and SHAP importance. Do not interpret a tree-ensemble importance score as the signed effect of a feature. |
| Global versus local scope: `3.pdf`, pp. 50-51; `6.pdf`, pp. 19-20. | Provide a global ranking across a stated sample and at least one dated local prediction explanation. State which model and split are being explained. A single example cannot establish global model behavior. |
| LIME local surrogate: `4.pdf`, pp. 2, 5. Weighted approximation example: pp. 16-20. Tabular implementation: pp. 26-27. | For a selected test date, initialize a regression-mode tabular explainer with training data and a fixed random seed. Report local surrogate fit and important contributions if LIME is included. |
| LIME limitations: `4.pdf`, pp. 24-25. | Disclose that random perturbations, feature correlation, locality and a linear surrogate can affect explanation stability. Perturbations may represent economically implausible feature combinations. |
| Sequential boosting, residual correction and learning rate: `5.pdf`, pp. 5-10. | Use XGBoost regression with an explicit squared-error objective and regularization. Tune modest tree depth, learning rate and number of estimators using only training/validation data. |
| SHAP's game-theoretic feature contributions: `5.pdf`, pp. 2, 11-14; `6.pdf`, pp. 7-10. Additivity example: `6.pdf`, pp. 12-14. | Use a tree-compatible explainer for XGBoost. Numerically check that expected value plus contributions reconstructs the model prediction within a declared tolerance. Keep baseline, output and SHAP values in the same units. |
| SHAP force plots: `5.pdf`, pp. 20-21. Global mean absolute importance: p. 22. Beeswarm: pp. 23-24. Dependence: p. 25. | Supply a local contribution chart and global mean absolute SHAP ranking. Where useful, add a beeswarm or dependence plot. Explain that mean absolute SHAP measures magnitude, while signed individual SHAP values indicate direction relative to the explainer baseline. |

## Project design decisions beyond the lecture examples

The following are project-specific adaptations to financial time series. They should be justified in the methods section, rather than presented as direct requirements from the slides:

1. Split observations in time order and keep a final untouched test period. Use expanding-window validation when performing cross-validation. Randomly shuffled train/test splits in tabular teaching examples do not fit the forecasting use case.
2. Purge the training row whose next-day target would cross a split boundary. Fit imputers, scalers and selection steps only on the relevant training window.
3. Define a convex blend as `prediction = w * XGBoost_prediction + (1 - w) * dense_network_prediction`. Select `w` on validation errors only, then freeze it before test evaluation. Include `w=0` and `w=1` when searching weights so that the blend can select a component alone.
4. Compare against zero-return and historical-mean-return baselines, plus a simple linear model where feasible. Report MAE, RMSE, R-squared and directional accuracy. Directional accuracy is supplementary to regression error, not a substitute for it.
5. If presenting an illustrative trading calculation, shift forecasts to the correct realizable return, state the execution assumption and transaction cost, and distinguish index forecasting from an executable investable strategy.
6. Report weak or negative results honestly. A negative out-of-sample R-squared is possible and is evidence about predictability, not a reason to alter the test split or fabricate improved results.

The supplied folder name mentions blending, but its five PDFs primarily cover LOWESS and XAI. A convex blend is a reasonable project implementation; no detailed blending algorithm was identified in these five lecture files.

## Reference accuracy note

`Blending_XGBoost_and_Deep_Learning,_Interpretability/5.pdf`, p. 26, and `6.pdf`, p. 21, label `https://arxiv.org/abs/1602.04938` as the original SHAP paper. That link is associated with LIME. Do not copy the label without correction. Use the verified SHAP paper by Lundberg and Lee, *A Unified Approach to Interpreting Model Predictions* (arXiv:1705.07874), and the LIME paper by Ribeiro, Singh and Guestrin, *"Why Should I Trust You?": Explaining the Predictions of Any Classifier* (arXiv:1602.04938), when assembling the final bibliography; verify external bibliographic details against their primary pages.

Teaching slides include illustrative model accuracies, prices and runtime comparisons from unrelated examples. These numbers are not Nifty Commodities experimental results and must not be transferred to this project's results section.
