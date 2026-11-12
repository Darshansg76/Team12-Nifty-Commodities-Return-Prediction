"""Check the finished files, refresh the short README, and make a submission ZIP."""
from pathlib import Path
import csv
import hashlib
import json
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
original=ROOT.parent
sources=list(original.glob('*.pdf'))+list(original.glob('*.xlsx'))
for folder in ['Blending_XGBoost_and_Deep_Learning,_Interpretability','Deep_Learning_with_Tabular_Business_Data','Project Id 12- Nifty Commodities Benchmark return prediction']:
    sources+=list((original/folder).rglob('*'))
inventory=[{'relative_path':p.relative_to(original).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources if p.is_file()]
if inventory:
    (ROOT/'references/source_inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
else:
    inventory=json.loads((ROOT/'references/source_inventory.json').read_text(encoding='utf-8'))

summary=json.loads((ROOT/'results/run_summary.json').read_text(encoding='utf-8'))
data=json.loads((ROOT/'results/data_summary.json').read_text(encoding='utf-8'))
scores=list(csv.DictReader((ROOT/'results/metrics.csv').open()))
names={'zero_return':'Zero return','training_mean':'Training mean','ridge':'Ridge',
       'xgboost':'XGBoost','keras':'Keras','fastai':'fastai','tabnet':'TabNet',
       'flash':'Lightning Flash','blend':'Optional blend'}
selected=names[summary['selected_model']]
test_rows=[r for r in scores if r['split']=='test']
metric_table='\n'.join(f'| {names[r["model"]]} | {float(r["RMSE"]):.4f} | {float(r["MAE"]):.4f} | {float(r["R2"]):.4f} |' for r in test_rows)
readme=f'''# Nifty Commodities return prediction

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
.\\run_demo.ps1
```

This loads the selected saved model and shows one real historical forecast beside its observed outcome. It does not retrain or claim to predict a new live session. Use `.\\run_demo.ps1 -All` to compare every saved candidate.

## How the project works

1. **Prepare the data.** Official NSE Indices history has 4,182 sessions. The first 538 lack open/high/low, leaving {data['raw_rows']:,} complete sessions from 27 February 2012 to 9 November 2026. No prices are invented.
2. **Explore the data.** Inspect returns, changing volatility and feature correlations. Distribution statistics use training data.
3. **Create 23 clues.** Features describe recent returns, averages/risk, daily price structure and trend/calendar information. They use only the current or earlier session. The weekday uses a seven-day cycle because the source includes {data['calendar_encoding']['weekend_source_sessions']} special weekend sessions.
4. **Train the five required frameworks.** XGBoost uses decision trees. Keras, fastai and Lightning Flash use small neural networks. TabNet uses attention to select useful features. All receive the same inputs and dates.
5. **Choose on validation, then evaluate on test.** Training is before 2022; validation is 2022–2023; test is 2024 onward. Scaling learns from training only. Three earlier time periods provide additional checks. Early stopping ends training when validation error stops improving.
6. **Compare and explain.** RMSE/MAE measure error; R² measures fit. We also compare simplicity and transparency. Zero return, training mean and Ridge are baselines. An optional weighted blend checks whether combining models helps; TreeSHAP explains XGBoost forecasts.

## What the experiment found

Validation selected **{selected}**. The later test contains **709 observations**:

| Candidate | RMSE (pp) | MAE (pp) | R² |
|---|---:|---:|---:|
{metric_table}

Lower RMSE/MAE and higher R² are better. RMSE and MAE are in return percentage points. A negative R² is valid and means the model misses more variation than the retrospective evaluation-mean reference.

**The results show little reliable forecasting power.** {names[summary['best_test_model_descriptive_only']]} has the lowest test RMSE, but we retain the model chosen earlier on validation. The optional blend is 0% XGBoost and 100% fastai here, so it gives no extra gain. One index and one final test era limit the conclusion. No trading profit is established.

## Rebuild the complete project

```powershell
.\\run_all.ps1
```

This retrains all models, runs the checks, executes the notebook, rebuilds Word/PDF/PPT, refreshes this summary and checksums, and recreates `Team_12_Completed_Project.zip` beside the project folder. Every training run fits models again; old prediction caches are not reused. Normal runs use the included frozen data.

The prepared computer has the Python environment and Codex authoring runtime. On a new computer with Python 3.12, use `.\\setup.ps1`, then `.\\run_all.ps1 -ResultsOnly` for training, checks and the notebook. Full slide/report authoring also needs the runtime described in [reproduction details](docs/REPRODUCIBILITY.md). The finished Word, PDF and PPT open independently of that runtime.

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
'''
(ROOT/'README.md').write_text(readme,encoding='utf-8')
required=['deliverables/Team_12_Project_Report.docx','deliverables/Team_12_Project_Report.pdf',
          'deliverables/Team_12_Presentation.pptx','notebooks/Team_12_Analysis.ipynb',
          'src/pipeline.py','src/model_adapters.py','src/demo.py','src/download_data.py',
          'results/metrics.csv','results/cv_metrics.csv','results/model_reload_checks.json',
          'models/tabnet/tabnet.zip','models/keras/keras.keras','models/fastai/fastai.pth',
          'models/flash/flash.pth','models/xgboost/xgboost.ubj',
          'data/raw/provenance.json','run_all.ps1','run_demo.ps1',
          'scripts/build_deliverables.ps1','README.md']
for relative in required:
    path=ROOT/relative
    if not path.is_file() or not path.stat().st_size:raise RuntimeError('Missing deliverable: '+relative)
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
with ZipFile(ROOT/'deliverables/Team_12_Presentation.pptx') as deck:
    slides=[n for n in deck.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
    notes=[n for n in deck.namelist() if n.startswith('ppt/notesSlides/notesSlide') and n.endswith('.xml')]
    assert len(slides)==16 and len(notes)==16
    table_count=sum(len(ET.fromstring(deck.read(n)).findall('.//a:tbl',ns)) for n in slides)
    assert table_count>0
nb=json.loads((ROOT/'notebooks/Team_12_Analysis.ipynb').read_text(encoding='utf-8'))
code=[c for c in nb['cells'] if c['cell_type']=='code']
assert all(c['execution_count'] is not None for c in code)
assert not any(o.get('output_type')=='error' for c in code for o in c.get('outputs',[]))
checks=json.loads((ROOT/'results/model_reload_checks.json').read_text())
assert all(x['passed'] for x in checks['models'].values())
hashes={r:hashlib.sha256((ROOT/r).read_bytes()).hexdigest() for r in required}
(ROOT/'results/deliverable_checksums.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')

# Package the working files, including current edits, without local environments.
excluded={'.git','.venv','.cache','.build','tmp','__pycache__','.ipynb_checkpoints','node_modules'}
archive=ROOT.parent/'Team_12_Completed_Project.zip'
staged=ROOT/'.build'/'release.zip'; staged.parent.mkdir(exist_ok=True)
with ZipFile(staged,'w',compression=ZIP_DEFLATED) as bundle:
    for file in sorted(ROOT.rglob('*')):
        relative=file.relative_to(ROOT)
        if not file.is_file() or any(part in excluded for part in relative.parts):
            continue
        if relative.parts[0]=='references' and (file.suffix in {'.js','.html','.json'} or file.name.endswith(('_extracted.txt','_verified.txt'))):
            if file.name!='source_inventory.json':
                continue
        if file.suffix in {'.pyc','.zip'} and not (relative.parts[0]=='models' and file.name=='tabnet.zip'):
            continue
        bundle.write(file,arcname=f'{ROOT.name}/{relative.as_posix()}')
staged.replace(archive)
print(json.dumps({'original_sources':len(inventory),'required_files':len(required),'slides':len(slides),'speaker_notes':len(notes),'native_tables':table_count,'executed_notebook_cells':len(code),'missing_files':0,'submission_zip':str(archive)}))
