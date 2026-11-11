"""Inventory original inputs and verify the local submission before Git archiving."""
from pathlib import Path
import hashlib
import json
from zipfile import ZipFile
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
original=ROOT.parent
sources=list(original.glob('*.pdf'))+list(original.glob('*.xlsx'))
for folder in ['Blending_XGBoost_and_Deep_Learning,_Interpretability','Deep_Learning_with_Tabular_Business_Data','Project Id 12- Nifty Commodities Benchmark return prediction']:
    sources+=list((original/folder).rglob('*'))
inventory=[{'relative_path':p.relative_to(original).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources if p.is_file()]
(ROOT/'references/source_inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
required=['deliverables/Team_12_Project_Report.docx','deliverables/Team_12_Project_Report.pdf',
          'deliverables/Team_12_Presentation.pptx','notebooks/Team_12_Analysis.ipynb',
          'src/pipeline.py','src/model_adapters.py','src/demo.py','src/download_data.py',
          'results/metrics.csv','results/cv_metrics.csv','results/model_reload_checks.json',
          'models/tabnet/tabnet.zip','models/keras/keras.keras','models/fastai/fastai.pth',
          'models/flash/flash.pth','models/xgboost/xgboost.ubj',
          'data/raw/provenance.json','docs/VIVA_GUIDE.md','README.md']
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
    assert table_count==9
nb=json.loads((ROOT/'notebooks/Team_12_Analysis.ipynb').read_text(encoding='utf-8'))
code=[c for c in nb['cells'] if c['cell_type']=='code']
assert all(c['execution_count'] is not None for c in code)
assert not any(o.get('output_type')=='error' for c in code for o in c.get('outputs',[]))
checks=json.loads((ROOT/'results/model_reload_checks.json').read_text())
assert all(x['passed'] for x in checks['models'].values())
hashes={r:hashlib.sha256((ROOT/r).read_bytes()).hexdigest() for r in required}
(ROOT/'results/deliverable_checksums.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
print(json.dumps({'original_sources':len(inventory),'required_files':len(required),'slides':len(slides),'speaker_notes':len(notes),'native_tables':table_count,'executed_notebook_cells':len(code),'missing_files':0}))
