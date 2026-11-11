# Validation evidence

Verified on 11 November 2026.

## Experiment execution

All five required frameworks completed three expanding outer folds and a final development fit on the official historical snapshot. The outer score periods were separate from the inner periods used for early stopping. Framework metadata save actual epochs, parameters, package versions and model artifact paths. Final predictions cover 493 validation and 709 test observations for all nine candidates.

## Software and numeric checks

All 13 unittest checks passed. Five tests establish causal feature prefix invariance, future-shock isolation, independently aligned percentage-return targets, strict date-boundary purging, and train-only scaler statistics. Three saved-artifact tests independently recompute every validation/test metric with NumPy, compare labels to the official close series, and check ordered, unique, disjoint prediction dates. Five additional tests reload each actual trained framework checkpoint and compare predictions on 12 real held-out observations.

The maximum checkpoint reload difference was 2.6822e-7 percentage points for Keras. All five satisfied the 1e-5 tolerance. Exact results are in `results/model_reload_checks.json`. The CLI historical demo successfully reloaded all nine candidates and matched each frozen prediction. Dates outside the evaluated test snapshot are rejected.

Native XGBoost TreeSHAP contributions use the best stopping iteration. Summed contributions reproduce validation predictions with maximum error 7.4506e-9 percentage points. This checks additive explanation consistency, not economic causality.

The executed notebook contains 11 executed analysis code cells, five embedded figures and zero execution errors. Its checks verify the source response hashes, return alignment, scaler parameters and saved metrics.

## Artifact review

The report was rendered through LibreOffice and Poppler, then all 11 pages were visually inspected. The final report uses deliberate table widths, unclipped figures, consistent headers and page numbering. Its Word and PDF versions share the same content.

The 16-slide PowerPoint was finalized with the artifact-tool validation helpers, including package integrity, native tables/charts, font and layout geometry, embedded chart workbook data and successful reimport. All final slides were rendered and visually inspected. The deck contains nine native tables, three native charts and speaker notes on all slides. This is rendered-output verification; it is not a claim that interactive PowerPoint editing was tested.

## Remaining external action

GitHub CLI reports no authenticated account. A local committed repository, archive and publishing script are prepared. No GitHub remote URL is represented as existing. Authenticate and publish before sharing a repository link for viva.
