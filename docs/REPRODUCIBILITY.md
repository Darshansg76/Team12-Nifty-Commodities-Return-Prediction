# Reproducing the project

The validated training environment is Python 3.12.14 on Windows, CPU, with seed 42 and two Torch threads. `results/run_summary.json` records the exact Python version and fitted-framework package versions. `requirements.txt` pins the primary dependencies. `requirements-local-lock.txt` records the additional locally installed packages. `environment-lock.txt` includes the full installed package set inherited by this session.

## Training and analysis

```powershell
.\setup.ps1
.\.venv\Scripts\python.exe src\pipeline.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe src\demo.py --all
.\.venv\Scripts\python.exe scripts\build_notebook.py
.\.venv\Scripts\python.exe scripts\build_report.py
```

The pipeline does not download data automatically. Run `src/download_data.py` explicitly to repeat the official endpoint requests. Refreshing can reflect provider revisions. Source responses and CSV checksums make that detectable. Keep the original snapshot for reproducing this submission.

The cache signature includes the input CSV and both training modules. Each final and fold directory saves its framework checkpoint and metadata. Cached predictions are reused only for the matching signature. A full recomputation can vary slightly across operating systems or library builds. The reported results use one seed rather than a claim of initialization invariance.

The notebook reads saved outputs and executes all analysis cells through nbclient with a project-local temporary kernelspec. It does not install a user kernel or rerun the entire training pipeline. The CLI demo restricts itself to evaluated test feature dates and compares loaded checkpoint predictions with the frozen CSV.

## Framework compatibility

Keras 3 officially supports PyTorch, and this project sets `KERAS_BACKEND=torch` before import. No TensorFlow model is implied.

Lightning Flash 0.8.2 uses PyTorch Lightning 1.9.5 and TorchMetrics 0.10.3. The real Flash Task/Trainer wraps a custom dense regression model. Setuptools 80.9.0 provides the legacy pkg_resources import. A localized `np.Inf = np.inf` compatibility alias supports the old checkpoint callback under NumPy 2. The adapter preserves all other library behavior. Its training call uses Flash's singular `train_dataloader` argument.

## Reports and slides

The Word builder uses python-docx and the actual JSON/CSV outputs. Rendering uses LibreOffice and Poppler through the installed Documents skill's `render_docx.py`, with `--emit_pdf`. The PDF and editable Word report contain the same final content. This environment has LibreOffice in `C:/Program Files/LibreOffice/program` and Poppler in the Codex runtime native dependency directory.

The PowerPoint builder uses the installed `@oai/artifact-tool` runtime and the Presentations skill finalizer. It reads the same experiment files, builds editable native tables/charts, adds speaker notes, renders every slide and validates the exported PPTX. `scripts/build_slides.mjs` accepts `CODEX_PRIMARY_RUNTIME_DEPENDENCIES` and `PRESENTATIONS_SKILL_DIR` to override this machine's dependency locations. The artifact package is provided by the Codex runtime rather than public npm. The exported PPTX is independently usable in PowerPoint without that authoring package.

Rendered PNGs, dependency checks, synthetic smoke diagnostics and build logs are local verification files, excluded from the submission ZIP and Git. Visual review used rendered output, not a claim that PowerPoint was opened interactively.

## GitHub publishing

`publish_github.ps1` checks authentication before creating anything online. Default visibility is private. After signing in, create and push a new repository with `./publish_github.ps1`, or set an existing remote with `./publish_github.ps1 -ExistingRepositoryUrl https://github.com/OWNER/REPOSITORY.git`. The script prints the repository URL for viva sharing. A private repository requires granting the instructor access through GitHub.


