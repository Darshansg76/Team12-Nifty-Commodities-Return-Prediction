# Validation evidence

Verified on 12 November 2026 after the weekday correction and simplification.

## Experiment execution

All five required frameworks completed three expanding outer folds and a final development fit on the official historical snapshot. The outer score periods were separate from the inner periods used for early stopping. Framework metadata save actual epochs, parameters, package versions and model artifact paths. Final predictions cover 493 validation and 709 test observations for all nine candidates.

## Software and numeric checks

All 14 unittest checks passed. Six feature/split tests cover causal feature prefix invariance, future-shock isolation, aligned next-session returns, strict boundary purging, training-only scaling, and distinct encodings for all seven weekdays. Three saved-artifact tests independently recompute every validation/test metric with NumPy, compare labels to the official close series, and check ordered, unique, disjoint prediction dates. Five tests reload the trained framework checkpoints and compare predictions on 12 real held-out observations.

The maximum checkpoint reload difference was 1.1921e-7 percentage points for Keras. All five satisfied the 1e-5 tolerance. Exact results are in `results/model_reload_checks.json`. The historical demo reloaded all nine candidates and matched each frozen prediction. Dates outside the evaluated test snapshot are rejected.

The complete `run_all.ps1` workflow finished successfully, including fresh training of all 20 framework fits, tests, notebook, Word/PDF/PPT and ZIP generation. Prediction caching has been removed. The optional blend reduces to 100% fastai; fastai is selected by validation, while Keras has the lowest descriptive test RMSE.

Native XGBoost TreeSHAP contributions use the best stopping iteration. Summed contributions reproduce validation predictions with maximum error 7.4506e-9 percentage points. This checks additive explanation consistency, not economic causality.

The executed notebook contains 11 executed analysis code cells, five embedded figures and zero execution errors. Its checks verify the source response hashes, return alignment, scaler parameters and saved metrics.

## Artifact review

The report was rendered through LibreOffice and Poppler, then all 11 pages were visually inspected. The final report uses deliberate table widths, unclipped figures, consistent headers and page numbering. Its Word and PDF versions share the same content.

The 16-slide PowerPoint follows Introduction, What we did, and Our results. It was finalized with the artifact-tool helpers, including package integrity, native tables/charts, font and layout geometry, embedded chart workbook data and successful reimport. All slides were rendered and visually inspected. The deck contains seven native tables, five native charts and speaker notes on every slide. Each note starts with a natural explanation the team can present. Weekday handling, validation selection, updated metrics and the run commands remain covered. Detailed formulas and settings stay in the notes. The review uses rendered output.

## GitHub publication

The presentation guide was added on 13 November 2026. All 18 rendered pages were reviewed, including four editable Word equations. It contains a dedicated explanation, speaking script, chart/table cue, precision reminder and transition for every slide. The 6–5–5 presenter allocation is preserved, with a target of 300 seconds each and closely balanced script lengths. Its nine-row results table matches the saved metrics.

GitHub device authentication completed for Darshansg76. The project was uploaded to https://github.com/Darshansg76/Team12-Nifty-Commodities-Return-Prediction. GitHub CLI verified private visibility and the main default branch. The local main branch tracks origin/main. Because the repository is private, other people need repository access before they can open the viva link.
