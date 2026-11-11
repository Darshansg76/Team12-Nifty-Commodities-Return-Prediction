# Project requirement coverage

| Supplied brief requirement | Implemented evidence | Status |
|---|---|---|
| Predict Nifty Commodities benchmark return | Explicit next-session close return, causal 23-feature pipeline | Complete |
| EDA | Training distribution, volatility, correlations and historical context in notebook/report/results figures | Complete |
| XGBoost | Actual XGBRegressor, final and CV fits, native UBJ checkpoints | Complete |
| Keras | Actual Keras 3 dense model using official PyTorch backend, .keras artifact | Complete |
| PyTorch with fastai | Actual TabularPandas and tabular_learner with saved TabularModel weights | Complete |
| PyTorch with TabNet | Actual TabNetRegressor attentive architecture and ZIP model | Complete |
| PyTorch with Lightning Flash | Actual flash.core.model.Task and flash.Trainer using a custom dense regression backbone | Complete |
| Compare simplicity, transparency and efficacy | Report section and presentation comparison table, signed metrics, framework metadata | Complete |
| RMSE, R2 and MAE | Independently checked validation/test scores for all nine candidates, three outer CV folds | Complete |
| Introduction, methodology, EDA, results, conclusion | Editable 11-page Word report and PDF, plus Markdown source | Complete |
| PPT | 16-slide editable PowerPoint with speaker notes | Complete |
| Prepare for viva | Viva guide, historical checkpoint demo and executed notebook | Complete |
| Creativity and course references | Validation-selected convex blend, TreeSHAP with additivity check, nested chronological validation, four-unit mappings | Complete |
| Team details | Verified names/SRNs in report, README, slides and viva guide | Complete |
| Code in GitHub and share for viva | Published private repository: https://github.com/Darshansg76/Team12-Nifty-Commodities-Return-Prediction on main. Grant the instructor access for viva. | Published |

The brief permits regression/classification. This implementation performs regression and supplies direction as a derived secondary metric. It does not claim a separate trained classifier. Flash uses its general Task API, with the actual implementation and compatibility details disclosed. The framework requirement is satisfied by real Flash training, rather than a substitute mislabeled as Flash.

