# Reproducing the project

The validated training environment is Python 3.12.14 on Windows, CPU, with seed 42 and two Torch threads. `results/run_summary.json` records the exact Python version and fitted-framework package versions. `requirements.txt` pins the primary dependencies. `requirements-local-lock.txt` records the additional locally installed packages. `environment-lock.txt` includes the full installed package set inherited by this session.

## Two commands for normal use

```powershell
.\run_demo.ps1
.\run_all.ps1
```

The demo loads the selected saved model and checks one historical prediction. Add `-All` to compare all candidates, or `-Date 2024-02-01` to choose an evaluated test date. It does not make a new live forecast.

The full command runs the pipeline, all tests, the executed notebook, Word report, PDF rendering, PowerPoint builder, checksums and submission ZIP in that order. It **fits every model again**, with no prediction-cache shortcut. Models and prediction files are saved together. Cross validation adds fifteen fits to the five final framework fits. The ZIP is recreated from the current working files, excluding environments and private build files; it does not depend on an older Git commit.

## Reproduce the experiment on another computer

Install Python 3.12, open PowerShell in this folder, and run `./setup.ps1`. Then run `./run_all.ps1 -ResultsOnly` for training, checks and the executed notebook. The finished reports and PowerPoint are already included and can be opened without the authoring runtime.

All normal runs use the included frozen official data. `./run_all.ps1 -RefreshData` explicitly repeats the requests through the same cutoff. Provider revisions can change the source; provenance hashes expose this. A recomputation can vary slightly across operating systems or library builds. We use one seed and do not claim initialization invariance.

Weekday features use `sin/cos(2*pi*dayofweek/7)`, where Monday is zero. This keeps all seven days distinct, including the 18 official weekend sessions. Month features use a twelve-month cycle. The weekend regression test checks all seven encodings independently.

The notebook reads saved outputs and executes all analysis cells through nbclient with a project-local temporary kernelspec. It does not install a user kernel or rerun the entire training pipeline. The CLI demo restricts itself to evaluated test feature dates and compares loaded checkpoint predictions with the frozen CSV.

## Framework compatibility

Keras 3 officially supports PyTorch, and this project sets `KERAS_BACKEND=torch` before import. No TensorFlow model is implied.

Lightning Flash 0.8.2 uses PyTorch Lightning 1.9.5 and TorchMetrics 0.10.3. The real Flash Task/Trainer wraps a custom dense regression model. Setuptools 80.9.0 provides the legacy pkg_resources import. A localized `np.Inf = np.inf` compatibility alias supports the old checkpoint callback under NumPy 2. The adapter preserves all other library behavior. Its training call uses Flash's singular `train_dataloader` argument.

## Reports and slides

`scripts/build_deliverables.ps1` rebuilds Word/PDF/PPT and the package without retraining; it uses the existing experiment results. The Word builder reads the actual JSON/CSV outputs. The Documents skill's `render_docx.py --emit_pdf` renders the Word report and page PNGs. On Windows its renderer uses native LibreOffice, here in `C:/Program Files/LibreOffice/program`, and bundled Poppler. The PDF and editable Word report contain the same content.

The PowerPoint builder reads the same experiment files, builds native editable tables/charts, adds explanation notes and renders every slide. The installed `@oai/artifact-tool` runtime and Presentations finalizer handle export. This authoring package is supplied by Codex rather than public npm. Defaults point to this computer's prepared runtime. Environment variables `CODEX_PRIMARY_RUNTIME_DEPENDENCIES`, `PRESENTATIONS_SKILL_DIR`, `DOCUMENTS_SKILL_DIR` and `PDF_SKILL_DIR` override locations. Without this runtime, use `-ResultsOnly`; this limitation affects rebuilding slides, not opening the provided PPT.

Rendered PNGs, dependency checks, synthetic smoke diagnostics and build logs are local verification files, excluded from the submission ZIP and Git. Visual review used rendered output, not a claim that PowerPoint was opened interactively.

## GitHub publishing

The project is published at https://github.com/Darshansg76/Team12-Nifty-Commodities-Return-Prediction as a private repository on main. Grant the instructor or teammates repository access before sharing the link. For future committed changes, `./publish_github.ps1` checks authentication, pushes to the existing origin and prints its URL. In a fresh local repository with no origin, it creates a private repository by default. An explicit existing remote can be supplied with `-ExistingRepositoryUrl https://github.com/OWNER/REPOSITORY.git`.


