"""Build the editable report from frozen experiment artifacts, never typed scores."""
from pathlib import Path
import json
import csv
from statistics import mean, stdev
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'deliverables'; OUT.mkdir(exist_ok=True)
summary=json.loads((ROOT/'results/run_summary.json').read_text())
data=json.loads((ROOT/'results/data_summary.json').read_text())
blend=json.loads((ROOT/'results/blend_selection.json').read_text())
shap=json.loads((ROOT/'results/shap_check.json').read_text())
scores=list(csv.DictReader((ROOT/'results/metrics.csv').open()))
cv=list(csv.DictReader((ROOT/'results/cv_metrics.csv').open()))
imp=list(csv.DictReader((ROOT/'results/xgboost_shap_importance.csv').open()))
doc=Document(); sec=doc.sections[0]
sec.page_height=Inches(11.7);sec.page_width=Inches(8.3)
sec.top_margin=Inches(.68);sec.bottom_margin=Inches(.68)
sec.left_margin=Inches(.8);sec.right_margin=Inches(.8)
for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3']:
    style=doc.styles[name]; style.font.name='Arial';style.font.color.rgb=RGBColor(0,0,0)
for node in list(doc.styles.element.xpath('.//w:pBdr')):
    node.getparent().remove(node)
doc.styles['Normal'].font.size=Pt(10.5)
doc.styles['Normal'].paragraph_format.line_spacing=1.12
doc.styles['Normal'].paragraph_format.space_after=Pt(7)
doc.styles['Title'].font.size=Pt(26)
doc.styles['Heading 1'].font.size=Pt(18)
doc.styles['Heading 2'].font.size=Pt(12)
for hn in ['Heading 1','Heading 2']:
    doc.styles[hn].paragraph_format.space_before=Pt(9)
    doc.styles[hn].paragraph_format.space_after=Pt(7)
header=sec.header.paragraphs[0];header.text='TEAM 12   MACHINE LEARNING WITH BUSINESS DATA'
header.style=doc.styles['Normal'];header.runs[0].font.size=Pt(8)
footer=sec.footer.paragraphs[0];footer.alignment=2
footer.add_run('Nifty Commodities return prediction   |   ')
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
for run in footer.runs:run.font.size=Pt(8)
md=[]

def title(text,first=False):
    if not first:doc.add_page_break()
    doc.add_paragraph(text,'Title' if first else 'Heading 1');md.append('\n# '+text+'\n')
def h(text):
    doc.add_paragraph(text,'Heading 2');md.append('\n## '+text+'\n')
def p(text):
    doc.add_paragraph(text);md.append(text+'\n')
def table(headers,rows,widths=None):
    t=doc.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    for j,v in enumerate(headers):t.rows[0].cells[j].text=str(v)
    for row in rows:
        cells=t.add_row().cells
        for j,v in enumerate(row):cells[j].text=str(v)
    if widths:
        for j,width in enumerate(widths):t.columns[j].width=Inches(width)
        for row in t.rows:
            for j,c in enumerate(row.cells):c.width=Inches(widths[j])
    for i,row in enumerate(t.rows):
        trpr=row._tr.get_or_add_trPr()
        cant=OxmlElement('w:cantSplit');trpr.append(cant)
        if i==0:
            repeat=OxmlElement('w:tblHeader');trpr.append(repeat)
        for j,cell in enumerate(row.cells):
            cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcpr=cell._tc.get_or_add_tcPr()
            shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'173E52' if i==0 else ('F2F5F6' if i%2 else 'FFFFFF'));tcpr.append(shade)
            borders=OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right']:
                el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D9D9D9');borders.append(el)
            tcpr.append(borders)
            margins=OxmlElement('w:tcMar')
            for edge in ['top','left','bottom','right']:
                el=OxmlElement('w:'+edge);el.set(qn('w:w'),'80');el.set(qn('w:type'),'dxa');margins.append(el)
            tcpr.append(margins)
            for para in cell.paragraphs:
                para.paragraph_format.space_after=Pt(2);para.paragraph_format.line_spacing=1.0
                if j>0 and len(str(cell.text))<20:para.alignment=1
                for run in para.runs:
                    run.font.size=Pt(9)
                    if i==0:run.bold=True;run.font.color.rgb=RGBColor(255,255,255)
    doc.add_paragraph().paragraph_format.space_after=Pt(1)
    md.append('| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |')
    md.extend('| '+' | '.join(map(str,r))+' |' for r in rows);md.append('')
def image(file,caption,width=6.3):
    doc.add_picture(str(ROOT/'results/figures'/file),width=Inches(width))
    cap=doc.add_paragraph(caption);cap.paragraph_format.space_after=Pt(5)
    for run in cap.runs:run.font.size=Pt(8.5);run.italic=True
    md.append(f'![{caption}](../results/figures/{file})\n')
def f(v,n=4):return f'{float(v):.{n}f}'
def metric_rows(split):
    return [[r['model'],f(r['RMSE']),f(r['MAE']),f(r['R2']),f(float(r['direction_accuracy'])*100,2)+'%'] for r in scores if r['split']==split]

selected=summary['selected_model']; sv=summary['selected_validation']; st=summary['selected_test']
title('Nifty Commodities Benchmark Return Prediction',True)
p('Machine Learning with Business Data mini project')
p('Team 12   |   Prepared 11 November 2026')
table(['Member','SRN'],[['Darshan Govekar','PES1UG24AM355'],['Dhanraj Rathod','PES1UG24AM359'],['Shridhar Umesh Golipalle','PES1UG25AM814']],[3.6,2.6])
h('Abstract')
p(f'This project predicts the next observed trading session return of the Nifty Commodities price index from information available after the current close. We compare XGBoost, Keras, fastai, PyTorch TabNet and Lightning Flash using the same 23 numeric features and chronological partitions. Official NSE Indices data provide {data["raw_rows"]:,} complete OHLC observations from 27 February 2012 to 9 November 2026. Three expanding folds within the training era use separate inner stopping periods, followed by a 2022 to 2023 development validation period and a frozen test period beginning in 2024.')
p(f'The lowest validation RMSE selects {selected}. Its test RMSE is {st["RMSE"]:.4f} percentage points, MAE is {st["MAE"]:.4f}, and R2 is {st["R2"]:.4f}. These figures come directly from saved predictions. The comparison retains simple baselines, negative R2 values and unsuccessful complex models. A validation-selected convex blend and TreeSHAP explanations extend the course methods. The study evaluates forecast accuracy and does not claim executable trading profits.')
h('Project scope')
p('The supplied Nifty Commodities brief controls this implementation. It asks for EDA, framework comparison, a report, a PowerPoint and viva preparation. The generic project list assigns a different title to ID 12. That inconsistency is recorded in the source notes and does not change the supplied topic.')

title('Introduction and Data')
h('Forecasting objective')
p('The Nifty Commodities index represents listed Indian companies in commodity-related industries. The official October 2026 factsheet describes 30 companies. It is an equity price index, rather than a basket of physical commodity spot prices. The index launched on 7 September 2011 and has a base date of 1 January 2004. The modeling sample starts after launch. [1]')
p('At the official close of session t, the model estimates the percentage return from that close to the close of the next observed session. The target is y(t) = 100 x [C(t+1) / C(t) - 1]. A prediction of 0.4 means a 0.4% index return. RMSE and MAE therefore use percentage points. The price series excludes reinvested dividends and must not be described as a total return benchmark.')
h('Official source and audit trail')
p('The downloader submits calendar-year requests to the historical endpoint linked by NSE Indices. All 17 JSON responses are retained with request payloads, retrieval times and SHA256 checksums in data/raw/provenance.json. The frozen request ends on 10 November 2026. The latest returned session is 9 November because 10 November is an exchange trading holiday. [2]')
table(['Quality item','Observed treatment'],[
['Downloaded sessions',f'{data["full_source_rows"]:,} from 4 Jan 2010 to 9 Nov 2026'],
['Missing initial OHL',f'{data["initial_rows_excluded_missing_ohlc"]} sessions through 24 Feb 2012 excluded'],
['Complete modeling era',f'{data["raw_rows"]:,} sessions from 27 Feb 2012'],
['Interior OHLC omissions','None in the retained continuous era'],
['Duplicates and invalid prices','No duplicates, nonpositive prices or inconsistent OHLC retained'],
['Market extremes','Preserved without winsorizing or clipping'],
['Holidays and weekends','No rows fabricated and no prices filled'],
],[1.8,4.5])
p('Excluding a contiguous initial period avoids creating invented intraday ranges. Returns still use adjacent observed market sessions. The downloader also retains the longer close series, so the exclusion is inspectable rather than hidden.')

title('Exploratory Data Analysis')
p('Training data drive exploratory interpretation. Full-history plots show context and partition boundaries, while feature correlations and distribution summaries use training observations only. The final test labels do not determine features, model settings, blend weights or model selection.')
stats=data['training_target_statistics']
table(['Training target statistic','Value'],[
['Mean daily return',f(stats['mean'])+'%'],['Standard deviation',f(stats['std'])+' pp'],
['Minimum and maximum',f(stats['min'])+'% to '+f(stats['max'])+'%'],
['Skewness',f(data['training_target_skew'])],['Excess kurtosis',f(data['training_target_excess_kurtosis'])],
['Positive return share',f(data['training_up_fraction']*100,2)+'%'],
],[3.3,3.0])
image('02_eda.png','Figure 1 Training returns and rolling volatility')
p('The distribution and rolling volatility expose the scale of daily forecasting error and changes in risk. Large observed returns remain in evaluation. The rolling estimates are trailing calculations, so a future shock cannot change a past feature. A large excess kurtosis indicates tail behavior that a Gaussian error assumption would miss.')

title('History and Causal Features')
image('01_history.png','Figure 2 Historical context with development and test boundaries')
table(['Feature group','Definitions available at close t'],[
['Short returns','Current close return and lagged returns at 1, 2, 3 and 5 sessions'],
['Momentum','Close changes over 5, 10 and 20 observed sessions'],
['Rolling statistics','Return mean and sample volatility over trailing 5 and 20 sessions'],
['Price position','Close relative to trailing 5 and 20 session means'],
['Intraday conditions','Close/open return, high-low range/close, open/previous close gap'],
['Oscillator and drawdown','14-session simple-average RSI and close relative to 60-session maximum'],
['Known calendar','Sine and cosine encodings for weekday and month'],
],[1.5,4.8])
p('There are 23 input columns. The 60-session drawdown creates a 59-row warm-up and the final unlabeled row is removed. Features use neither centered windows nor backward filling. The exact feature order is saved in models/features.json. Correlated features can share explanatory credit, so a large attribution is not evidence of an independent economic cause.')

title('Methodology and Validation')
parts=data['partitions']
table(['Partition','Feature dates','Rows'],[[n,parts[n]['feature_start'][:10]+' to '+parts[n]['feature_end'][:10],parts[n]['rows']] for n in ['train','validation','test']],[1.3,4,1])
p('The training cutoff is 31 December 2021 and the development validation cutoff is 31 December 2023. Boundary purging removes a row whenever its outcome reaches the next partition first forecast date. The test starts in 2024 and remains untouched during fitting, stopping and selection. StandardScaler learns the mean and population standard deviation from training features only. Each later partition uses that same transformation. XGBoost receives the same transformed inputs for a consistent comparison, although trees do not require scaling.')
h('Expanding cross validation')
p('Three expanding outer folds lie entirely inside the pre-2022 training era. Each outer score covers 252 sessions with a one-row gap. Within each fold training block, the last 126 sessions monitor early stopping and one additional row separates them from fitting. Scaling uses only the inner fitting block. The outer fold outcomes never monitor training. This follows the time-based validation requirements in Unit 1 page 81 and Unit 2 page 59. [3, 4, 5]')
p('All five frameworks use the same fold indices, features, target, CPU setting and seed 42. Architecture settings are intentionally compact. The project does not claim an exhaustive search or identical parameter counts across different model families. Final fitting uses the full pre-2022 training block and monitors the 2022 to 2023 validation block. No post-selection refit changes the frozen test predictions.')
h('Metrics and selection')
p('RMSE = sqrt(mean((y - prediction)^2)) emphasizes large errors. MAE = mean(abs(y - prediction)) measures typical absolute error. R2 = 1 - sum((y - prediction)^2) / sum((y - test mean)^2) can be negative. Direction accuracy compares whether y > 0 and prediction > 0. An exact zero prediction counts as nonpositive. This is a derived directional diagnostic, not a separately trained classifier.')
p('The lowest development validation RMSE selects the recommendation from all models and baselines. The report displays every frozen test score for comparison. A model that happens to score best on the test is descriptive and does not replace the validation-selected recommendation.')

title('Framework Implementations')
table(['Framework','Actual fitted model and settings'],[
['XGBoost','Squared-error boosted trees, depth 2, up to 160 trees, learning rate 0.03, subsample 0.9, column sample 0.9, L2 5, stopping patience 20.'],
['Keras','Keras 3 with PyTorch backend. Dense 64 and 32 ReLU layers, dropout 0.1, L2 0.001, linear output and Adam at 0.001.'],
['fastai','TabularPandas and tabular_learner. Dense 64 and 32 layers, dropout 0.1, no batch normalization, Adam at 0.001 and weight decay 0.001.'],
['PyTorch TabNet','TabNetRegressor with n_d = n_a = 8, three attentive steps, gamma 1.3, sparse penalty 0.001 and Adam at 0.01.'],
['Lightning Flash','A real Flash Task and Flash Trainer around a PyTorch 64 and 32 ReLU MLP, dropout 0.1 and Adam at 0.001 with weight decay 0.001.'],
],[1.4,4.9])
p('Deep models use at most 40 epochs and stopping patience 5. The dense models use batches of 64. TabNet uses batches of 256 with virtual batches of 64. MSE is the regression objective. Best monitored weights are restored before predictions. Model metadata save the actual stopping epoch, package versions, histories and elapsed training-plus-prediction time. [6, 7, 8, 9]')
p('The Flash implementation uses its general Task API rather than claiming the legacy Flash TabularRegressor convenience wrapper. Flash 0.8.2 runs with PyTorch Lightning 1.9.5 and TorchMetrics 0.10.3. Its legacy checkpoint callback refers to np.Inf, so the adapter supplies a documented compatibility alias to np.inf with NumPy 2. Setuptools 80.9.0 supplies pkg_resources. These details are captured in the environment lock and code.')
h('Baselines and project extension')
p(f'The zero-return and fixed training-mean predictors make no use of test outcomes. Ridge regression with alpha 100 provides a simple linear comparison. For the extension, validation selects {blend["deep_component"]} among the four deep models. Eleven candidate weights from 0 to 1 combine that prediction with XGBoost. The selected XGBoost weight is {blend["xgboost_weight"]:.1f}. A boundary weight is retained if that is what validation selects. This project blend is not presented as a method taught in the supplied interpretability folder.')

title('Development Results')
h('Outer fold cross validation')
cvtable=[]
for name in ['xgboost','keras','fastai','tabnet','flash']:
    rr=[float(r['RMSE']) for r in cv if r['model']==name]
    aa=[float(r['MAE']) for r in cv if r['model']==name]
    cvtable.append([name,f(mean(rr))+' +/- '+f(stdev(rr)),f(mean(aa))+' +/- '+f(stdev(aa))])
table(['Model','RMSE mean and sample SD','MAE mean and sample SD'],cvtable,[1.3,2.5,2.5])
p('These three outer-fold scores measure sensitivity to historical eras. Their sample standard deviation describes variation across three periods and is not a confidence interval. The same stopping protocol precedes every outer score. Complete per-fold dates, row counts and signed R2 values are saved in results/cv_metrics.csv.')
h('Development validation scores')
table(['Model','RMSE pp','MAE pp','R2','Direction'],metric_rows('validation'),[1.7,1.15,1.15,1.1,1.2])
p(f'The selection rule chooses {selected}, with validation RMSE {sv["RMSE"]:.4f} pp. Validation also monitors early stopping and selects the blend component and weight. Its scores therefore contain selection optimism. Only the later frozen test estimates performance after those choices. The blend is a candidate in this rule and receives no guaranteed preference.')

title('Frozen Test Results')
table(['Model','RMSE pp','MAE pp','R2','Direction'],metric_rows('test'),[1.7,1.15,1.15,1.1,1.2])
p(f'The validation-selected {selected} records test RMSE {st["RMSE"]:.4f} pp, MAE {st["MAE"]:.4f} pp, R2 {st["R2"]:.4f} and direction accuracy {st["direction_accuracy"]*100:.2f}%. The lowest observed test RMSE belongs to {summary["best_test_model_descriptive_only"]}. That retrospective comparison does not change the earlier selection.')
image('05_diagnostics.png','Figure 3 Observed versus predicted return and residuals of the selected model')
p('A negative R2 means that the model performs worse than predicting the mean of the evaluation outcomes in the R2 denominator. That denominator is a retrospective reference, not a deployable baseline. Compare the actual zero-return and training-mean predictors separately. Good level prediction does not imply good return prediction, so every metric here evaluates the return target.')

title('Interpretability and Practical Comparison')
image('06_explanations.png','Figure 4 Validation TreeSHAP attributions for the stopped XGBoost model')
p(f'Native XGBoost TreeSHAP decomposes each prediction into a bias term and feature contributions. The computation uses only trees through the best stopping iteration. The maximum numerical additivity error is {shap["max_additivity_error"]:.2e} pp. On validation data, the three largest mean absolute attributions are {", ".join(r["feature"] for r in imp[:3])}. These describe the fitted forecast, not causal drivers or investment value. [10]')
table(['Framework','Simplicity','Transparency and practical efficacy'],[
['XGBoost','Short tabular workflow','TreeSHAP and tree structure aid inspection. Compare measured errors to simple baselines.'],
['Keras','Compact fit and callback API','Dense weights need attribution or sensitivity analysis. Torch backend shares the common runtime.'],
['fastai','High-level tabular learner','Convenient callbacks and transforms. Dense networks remain difficult to interpret directly.'],
['TabNet','More architecture settings','Attentive masks and aggregate importances add model explanations. Masks are not causal evidence.'],
['Flash','Most legacy setup work here','Task and Trainer expose training steps. Compatibility pins add maintenance cost.'],
],[1.2,1.5,3.6])
p('Simplicity and transparency are reasoned qualitative comparisons, not invented numeric ratings. Efficacy is the observed RMSE, MAE, R2 and direction accuracy on identical dates. The simple baseline remains preferable when added complexity fails to improve the chosen validation criterion.')

title('Conclusion and Reproducibility')
p(f'The completed comparison selects {selected} under the stated validation rule. Its frozen test RMSE is {st["RMSE"]:.4f} pp and R2 is {st["R2"]:.4f}, indicating very weak predictive skill. The blend improves RMSE over zero return by only 0.001918 pp. Its direction accuracy of 51.48% falls below the training-mean benchmark at 55.71%. These results do not establish a reliable forecasting advantage. The blend and model explanations extend the analysis without using final test labels to optimize the system.')
h('Limitations')
p('One index and one final test era limit generalization. Inputs contain only the index own OHLC history and known calendar values. They omit macroeconomic releases, exchange rates, commodity futures, news and fundamentals. The experiment uses one seed, so it does not estimate neural initialization uncertainty. Historical data can be revised by the provider.')
p('The final model remains frozen at its original training cutoff, which makes evaluation auditable but can become stale. Rolling retraining and additional independent eras would be the next experiment. They must be specified before looking at new outcomes. A signal computed after the official close cannot assume execution at that same closing price. No trading return, Sharpe ratio or profit claim is made.')
h('Files and commands')
p('The project includes the raw source responses and provenance, processed partitions, actual framework checkpoints, predictions, metrics, figures, an executed analysis notebook, editable presentation, report and viva guide. From a Python 3.12 environment, install requirements.txt, then run python src/pipeline.py. Run python -m unittest discover -s tests -v to verify causality, split isolation and the saved metrics. The local Windows launcher uses the prepared .venv environment.')
p('Model caches carry a signature of the source CSV and training code. Code or data changes force new prediction caches. Downloading is a separate explicit command, so reproduction uses the frozen snapshot by default. The project is published in a private GitHub repository at https://github.com/Darshansg76/Team12-Nifty-Commodities-Return-Prediction on the main branch. Grant the instructor repository access before sharing the viva link.')
h('Connection to the four units')
table(['Course material','Application'],[
['Unit 1 pp 81 and 145 to 163','Time-based forecasting and regression evaluation with signed R2'],
['Unit 2 pp 7 to 8 and 47 to 59','Train-only preprocessing, common folds and untouched final test'],
['Deep Learning 1.pdf pp 6 and 25 to 33','Two hidden layers, fair features, stopping and best checkpoints'],
['Interpretability 3.pdf to 6.pdf','Local explanations, SHAP and limits of feature attribution'],
],[2.8,3.5])

title('References and Source Notes')
refs=[
'[1] NSE Indices Limited. Nifty Commodities factsheet, 30 October 2026. https://www.niftyindices.com/Factsheet/ind_nifty_commodities.pdf. Local copy retained in references.',
'[2] NSE Indices. Historical data and index page. https://www.niftyindices.com/reports/historical-data and https://www.niftyindices.com/indices/equity/thematic-indices/nifty-commodities. Official trading holiday calendar: https://www.nseindia.com/resources/exchange-communication-holidays. Retrieved 11 November 2026. Requests and checksums are in data/raw/provenance.json.',
'[3] Supplied unit 1 merged.pdf. Time-based split p 81. Regression metrics pp 145 to 163. Page references use physical PDF positions.',
'[4] Supplied unit 2 merged.pdf. Leakage pp 7 to 8 and 25. Common evaluation and time-series validation pp 47 and 59. Detailed mapping is in references/unit_1_2_mapping.md.',
'[5] Scikit-learn. TimeSeriesSplit API. https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html.',
'[6] Chen, T. and Guestrin, C. 2016. XGBoost A Scalable Tree Boosting System. https://arxiv.org/abs/1603.02754.',
'[7] Keras. EarlyStopping and multi-backend configuration. https://keras.io/api/callbacks/early_stopping/ and https://keras.io/getting_started/. fastai. Tabular learner. https://docs.fast.ai/tabular.learner.html.',
'[8] Arik, S. O. and Pfister, T. TabNet Attentive Interpretable Tabular Learning. https://arxiv.org/abs/1908.07442. Implementation: https://github.com/dreamquark-ai/tabnet.',
'[9] Lightning Flash. Task API. https://lightning-flash.readthedocs.io/en/stable/api/generated/flash.core.model.Task.html. Supplied Deep_Learning_with_Tabular_Business_Data/1.pdf and 3.pdf. Page mapping in references/unit_3_4_mapping.md.',
'[10] Lundberg, S. and Lee, S. I. 2017. A Unified Approach to Interpreting Model Predictions. https://arxiv.org/abs/1705.07874. Native contributions: https://xgboost.readthedocs.io/en/stable/python/python_api.html.',
]
for ref in refs:p(ref)
h('Resolution of source inconsistencies')
p('The specific project brief names Nifty Commodities, while the generic list assigns investor risk tolerance to Project ID 12. This submission follows the specific brief and the user topic. The team PDF supplies the full names and SRNs. The user clarified that the old prohibition on AI assistance no longer applies. No claim of unaided authorship is made.')
p('Unit 1 examples constrain or take the absolute value of R2, which is unsuitable for held-out evaluation. This implementation preserves signed R2. The supplied SHAP lecture cites arXiv 1602.04938, which is the LIME paper. This report cites the original SHAP paper instead. The interpretability folder name mentions blending, but its PDFs do not develop the blend used here.')

doc.core_properties.title='Nifty Commodities Benchmark Return Prediction'
doc.core_properties.author='Team 12'
doc.core_properties.subject='Machine Learning with Business Data mini project'
doc.save(OUT/'Team_12_Project_Report.docx')
(ROOT/'docs/PROJECT_REPORT.md').write_text('\n'.join(md),encoding='utf-8')
print(OUT/'Team_12_Project_Report.docx')
