/** Build an editable, results-driven PowerPoint deck. Requires completed pipeline. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const DEP=process.env.CODEX_PRIMARY_RUNTIME_DEPENDENCIES || 'C:/Users/darsh/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const SKILL=process.env.PRESENTATIONS_SKILL_DIR || 'C:/Users/darsh/.codex/plugins/cache/openai-primary-runtime/presentations/26.1105.12137/skills/presentations';
process.env.RUNTIME_NODE_MODULES ||= path.join(DEP,'node/node_modules');
const {Presentation,PresentationFile,FileBlob}=await import(pathToFileURL(path.join(DEP,'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')));
const {finalizePresentation,resolvePresentationFont,applyPresentationChartFont}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')));
const TMP=path.join(ROOT,'.build/slides');
await fs.mkdir(TMP,{recursive:true});await fs.mkdir(path.join(ROOT,'deliverables'),{recursive:true});
const readJSON=async p=>JSON.parse(await fs.readFile(path.join(ROOT,p),'utf8'));
function parseCSV(text){
  const lines=text.replace(/^\uFEFF/,'').trim().split(/\r?\n/);
  const parse=l=>{let a=[],s='',q=false;for(let i=0;i<l.length;i++){let c=l[i];if(c==='"'){if(q&&l[i+1]==='"'){s+='"';i++;}else q=!q;}else if(c===','&&!q){a.push(s);s='';}else s+=c;}a.push(s);return a;};
  const keys=parse(lines.shift());return lines.map(l=>Object.fromEntries(parse(l).map((v,i)=>[keys[i],v])));
}
const readCSV=async p=>parseCSV(await fs.readFile(path.join(ROOT,p),'utf8'));
const [summary,data,provenance,blend,scores,cv,shap,shapCheck,raw]=await Promise.all([
  readJSON('results/run_summary.json'),readJSON('results/data_summary.json'),readJSON('data/raw/provenance.json'),
  readJSON('results/blend_selection.json'),readCSV('results/metrics.csv'),readCSV('results/cv_metrics.csv'),
  readCSV('results/xgboost_shap_importance.csv'),readJSON('results/shap_check.json'),readCSV('data/raw/nifty_commodities_complete_ohlc.csv'),
]);
const names={zero_return:'Zero return',training_mean:'Training mean',ridge:'Ridge',xgboost:'XGBoost',keras:'Keras MLP',fastai:'fastai MLP',tabnet:'TabNet',flash:'Flash MLP',blend:'Blend'};
const order=['zero_return','training_mean','ridge','xgboost','keras','fastai','tabnet','flash','blend'];
const modelOrder=['xgboost','keras','fastai','tabnet','flash'];
const n=x=>Number(x); const fmt=(x,d=3)=>Number(x).toFixed(d); const pct=x=>(100*Number(x)).toFixed(1)+'%';
const ds=x=>String(x).slice(0,10); const score=(name,split='test')=>scores.find(r=>r.model===name&&r.split===split);
const FONT=resolvePresentationFont();const C={paper:'#FAF9F6',ink:'#112D40',muted:'#516474',teal:'#168C83',line:'#D5DEE1',pale:'#EEF3F3',white:'#FFFFFF',orange:'#C66538'};
const p=Presentation.create({slideSize:{width:1280,height:720}});
const tableOwners=[],chartOwners=[];
function txt(s,text,x,y,w,h,size=28,bold=false,color=C.ink){
  const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  sh.text=text;sh.text.style={typeface:FONT,fontSize:size,bold,color,wrap:'square',verticalAlignment:'top',insets:0};return sh;
}
function slide(title,notes=''){
  const s=p.slides.add();s.background.fill=C.paper;
  txt(s,title,72,48,1136,95,44,true);
  txt(s,String(p.slides.items.length).padStart(2,'0'),1160,660,48,24,16,false,C.muted);
  s.speakerNotes.text=notes;return s;
}
function table(s,values,widths,{top=164,height=420,size=24,pad=10}={}){
  const t=s.tables.add({rows:values.length,columns:values[0].length,left:72,top,width:1136,height,values,columnWidths:widths});
  t.borders.assign({style:'solid',fill:C.line,width:1});
  t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({
    textStyle:{typeface:FONT,fontSize:size,color:C.ink},margins:{left:14,right:12,top:pad,bottom:pad},anchor:'center',
  });
  for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
    t.getCell(r,c).fill=r===0?C.ink:(r%2===1?C.white:C.pale);
    t.getCell(r,c).text.style={typeface:FONT,fontSize:size,color:r===0?C.white:C.ink,bold:r===0};
  }
  tableOwners.push(p.slides.items.length);return t;
}
function chart(s,type,cfg){
  // Excel stores at most 15 significant digits. Preserve 12 for portable
  // embedded chart workbooks while the source CSV/JSON keeps full precision.
  if(cfg.series)cfg.series=cfg.series.map(ser=>({...ser,...(type==='line'?{smooth:false}:{}),values:ser.values?.map(v=>v==null?v:Number(Number(v).toPrecision(12)))}));
  const ch=s.charts.add(type,{chartFill:C.paper,plotAreaFill:C.paper,
    chartLine:{fill:'none',width:0},plotAreaLine:{fill:'none',width:0},
    title:cfg.series?.[0]?.name,titleTextStyle:{typeface:FONT,fontSize:24},lineOptions:{smooth:false},
    ...cfg});
  applyPresentationChartFont(ch,{fontFamily:FONT});chartOwners.push(p.slides.items.length);return ch;
}
const noteSource='Data source: NSE Indices Limited, https://www.niftyindices.com/reports/historical-data . Frozen request through 2026-11-10. Raw requests, SHA256 hashes and exact coverage: data/raw/provenance.json.';
// 1
{
 const s=p.slides.add();s.background.fill=C.ink;
 txt(s,'Nifty Commodities\nbenchmark return prediction',72,105,1100,190,58,true,C.white);
 txt(s,'Machine Learning with Business Data\nTeam 12',76,340,900,80,28,false,'#C2D7DB');
 txt(s,'Darshan Govekar   PES1UG24AM355\nDhanraj Rathod   PES1UG24AM359\nShridhar Umesh Golipalle   PES1UG25AM814',76,480,1090,120,27,false,C.white);
 s.speakerNotes.text='Introduce the three team members. The specific supplied project brief defines the topic as Nifty Commodities benchmark return prediction. The generic project list maps ID 12 to another topic, so this project follows the explicit brief and the user instruction. Team names and SRNs verified against the supplied team PDF. Presentation date: November 11, 2026.';
}
// 2
{
 const s=slide('Forecasting an equity index return',
 'The Nifty Commodities Index tracks shares of companies in commodity-related sectors. It is not a spot-commodity basket. The October 30, 2026 official factsheet reports 30 constituents, launch September 7, 2011 and base January 1, 2004. The experiment forecasts the price return, which excludes dividend reinvestment. Source: https://www.niftyindices.com/Factsheet/ind_nifty_commodities.pdf . Target definition: src/pipeline.py build_features.');
 txt(s,'Nifty Commodities tracks listed companies in commodity-related sectors.',72,170,1110,90,34,true);
 txt(s,'At the close of session t, estimate the percentage change by the next observed trading close.',72,300,1100,100,32);
 txt(s,'Target = 100 × (Close at t+1 / Close at t − 1)',72,450,1100,70,36,true,C.teal);
 txt(s,'Regression is the primary task. Return direction is a secondary diagnostic.',72,560,1100,55,25,false,C.muted);
}
// 3
{
 const s=slide('Official data and the analysis sample',noteSource+'\nThe initial 538 rows have valid close but missing official open, high and low. They form a contiguous initial block ending February 24, 2012. The complete era begins February 27, 2012 with no interior missing OHLC. No imputation or row-level removal inside the modeling era. November 10, 2026 is an official trading holiday: https://www.nseindia.com/resources/exchange-communication-holidays .');
 table(s,[['Dataset','Sessions','Coverage'],['Downloaded close history',String(provenance.rows),`${provenance.actual_start} to ${provenance.actual_end}`],['Initial rows with missing OHL',String(provenance.rows-provenance.complete_ohlc_rows),'2010-01-04 to 2012-02-24'],['Complete OHLC modeling era',String(provenance.complete_ohlc_rows),`${provenance.complete_ohlc_start} to ${provenance.complete_ohlc_end}`],['Engineered feature rows',String(data.feature_rows),'Warm-up and last unknown target removed']],[400,140,596],{height:350,size:24});
 txt(s,'Raw responses and hashes preserve the source snapshot. No synthetic observations.',72,565,1120,65,26,false,C.muted);
}
// 4
{
 const tr=data.partitions.train;
 const s=slide('Price history and return variability',noteSource+'\nChart shows actual annual last observed closes within the training era only, joined for a compact view. It does not show intra-year price variation. Statistics below are next-session target returns on the training partition. They are descriptive, not evidence of predictive skill. Training statistics from results/data_summary.json.');
 const monthly=new Map();for(const r of raw){const date=r.date??r.Date;if(date<=ds(tr.feature_end))monthly.set(date.slice(0,4),r);}
 const rows=[...monthly.values()];
 chart(s,'line',{position:{left:60,top:155,width:770,height:410},categories:rows.map(r=>(r.date??r.Date).slice(0,4)),series:[{name:'Annual last observed close',values:rows.map(r=>n(r.close??r.Close)),line:{fill:C.teal,width:3},marker:{symbol:'circle',size:6,fill:C.teal}}],hasLegend:false,xAxis:{textStyle:{fontSize:18},title:'Training era annual last observed close'},yAxis:{numberFormatCode:'#,##0',textStyle:{fontSize:18},title:'Index points',majorGridlines:{fill:C.line,width:1}}});
 const st=data.training_target_statistics;
 txt(s,`Mean return\n${fmt(st.mean)}%`,875,180,310,95,28,true);
 txt(s,`Daily standard deviation\n${fmt(st.std)} pp`,875,305,310,100,28,true);
 txt(s,`Excess kurtosis\n${fmt(data.training_target_excess_kurtosis,2)}`,875,435,310,100,28,true);
 txt(s,`Training observations: ${tr.rows}. Large moves require RMSE and MAE to be reported together.`,72,595,1110,48,25,false,C.muted);
}
// 5
{
 const s=slide('Features available at the forecast time',
 'All 23 features use information available after the official close on feature date t. return_1 is the realized return ending at t. return_lag_1 through selected lag_5 use earlier observations. Technical indicators are backward rolling windows. StandardScaler fits only on the applicable training block, including separately within each CV fold. Source: src/pipeline.py FEATURE_COLUMNS, build_features and make_arrays.');
 table(s,[['Feature group','Examples'],['Past returns and momentum','Current return, selected lags, 5/10/20-session momentum'],['Volatility and averages','5/20-session volatility, mean return, distance to SMA'],['Daily price structure','Intraday return, high-low range, overnight gap'],['Trend and calendar','RSI 14, drawdown 60, weekday/month sine and cosine']],[365,771],{height:360,size:25});
 txt(s,`${data.feature_count} numeric features. The target is shifted forward by one observed session.`,72,565,1120,60,28,true,C.teal);
}
// 6
{
 const s=slide('Chronological evaluation',
 'All partitions are chronological. Rows with labels crossing a partition boundary are purged, so the final training target date precedes validation feature dates and validation target dates precede test feature dates. Three TimeSeriesSplit folds use an expanding training block, gap=1 and 252 outer-validation observations. The last 126 sessions inside each fold monitor early stopping. The outer fold never monitors stopping. Source: src/pipeline.py split_dataset and run.');
 const ps=data.partitions;
 table(s,[['Partition','Feature dates','Rows'],...['train','validation','test'].map(k=>[k==='train'?'Training':k==='validation'?'Development validation':'Held-out test',`${ds(ps[k].feature_start)} to ${ds(ps[k].feature_end)}`,String(ps[k].rows)])],[390,566,180],{height:280,size:25});
 txt(s,'Three expanding folds inside training',72,485,1100,48,32,true);
 txt(s,'252 sessions per outer fold. One-row gaps protect label boundaries.\nValidation supports stopping and blend selection. Test supports final evaluation.',72,545,1100,88,25,false,C.muted);
}
// 7
{
 const s=slide('The five requested frameworks',
 'All adapters actually train and persist fitted models. Keras uses the PyTorch backend, which is officially supported in Keras 3. Flash is the legacy lightning-flash Task/Trainer API with a custom continuous-feature MLP and regression loss. This is an explicit compatibility adaptation, not the built-in Flash TabularRegressor. Source: src/model_adapters.py and saved metadata in models/<name>/metadata.json. Official Keras backend guide: https://keras.io/getting_started/ . Flash Task documentation: https://lightning-flash.readthedocs.io/en/stable/api/generated/flash.core.model.Task.html .');
 table(s,[['Framework','Model in this experiment'],['XGBoost','Shallow boosted trees, depth 2, up to 160 rounds'],['Keras on PyTorch','Dense layers 64 / 32, ReLU, dropout and L2'],['PyTorch with fastai','tabular_learner, layers 64 / 32, no categorical features'],['PyTorch TabNet','Decision/attention width 8, three decision steps'],['Lightning Flash','Custom Flash Task with a 64 / 32 MLP']],[365,771],{height:410,size:24});
 txt(s,'Baselines: zero return, training mean and Ridge. All models use the same features.',72,605,1115,40,24,false,C.muted);
}
// 8
{
 const s=slide('Variation across three training folds',
 'Results from results/cv_metrics.csv. Means and sample standard deviations across three chronological outer folds. These folds precede the development-validation and test eras. Each outer fold has 252 observations and its own training-only scaler. No test tuning. Source: src/pipeline.py TimeSeriesSplit loop.');
 const stats=(name,key)=>{let a=cv.filter(r=>r.model===name).map(r=>n(r[key]));if(a.length!==3)throw new Error('Expected 3 CV folds');let mean=a.reduce((a,b)=>a+b)/3;return [mean,Math.sqrt(a.reduce((s,v)=>s+(v-mean)**2,0)/2)];};
 table(s,[['Framework','RMSE mean ± SD','MAE mean ± SD','R² mean'],...modelOrder.map(k=>{let r=stats(k,'RMSE'),a=stats(k,'MAE');return[names[k],`${fmt(r[0])} ± ${fmt(r[1])}`,`${fmt(a[0])} ± ${fmt(a[1])}`,fmt(stats(k,'R2')[0])];})],[290,300,300,246],{height:380,size:24});
 txt(s,'RMSE and MAE are in percentage points of daily return. Fold dispersion matters.',72,585,1120,65,26,false,C.muted);
}
// 9
{
 const s=slide('Development validation results',
 'All figures read directly from results/metrics.csv, validation split. Models monitor this period for early stopping, and the blend weight also uses it. Therefore these are development scores and are optimistic. Model selection uses the lowest validation RMSE, including baselines. The next slide contains untouched test results.');
 table(s,[['Model','RMSE pp','MAE pp','R²','Direction'],...order.map(k=>{let r=score(k,'validation');return[names[k],fmt(r.RMSE,4),fmt(r.MAE),fmt(r.R2,4),pct(r.direction_accuracy)];})],[340,190,190,190,226],{height:440,size:23,pad:6});
 txt(s,`Validation selects ${names[summary.selected_model]} by minimum RMSE, including the baselines.`,72,622,1110,38,24,true,C.teal);
}
// 10
{
 const s=slide('Held-out test results',
 'All figures read directly from results/metrics.csv, test split. The prediction models and blend weight are fixed before this period is evaluated. A row winning on this test table is descriptive and does not replace the validation-selected recommendation. Direction accuracy uses the sign of the regression output, with positive defined as return > 0. A zero prediction is classified as nonpositive, so its accuracy is the nonpositive class frequency.');
 table(s,[['Model','RMSE pp','MAE pp','R²','Direction'],...order.map(k=>{let r=score(k);return[names[k],fmt(r.RMSE,4),fmt(r.MAE),fmt(r.R2,4),pct(r.direction_accuracy)];})],[340,190,190,190,226],{height:440,size:23,pad:6});
 txt(s,'Negative R² means worse squared error than the test-period mean reference.',72,622,1120,38,24,false,C.muted);
}
// 11
{
 const selected=summary.selected_model;const r=score(selected);const base=score('zero_return');
 const improvement=100*(n(base.RMSE)-n(r.RMSE))/n(base.RMSE);
 const s=slide('The selected model and baseline comparison',
 `Recommendation selected on validation only: ${selected}. Test RMSE improvement versus zero return is ${improvement.toFixed(3)}%. A positive value is an error reduction and a negative value is an increase. This comparison does not establish an executable trading edge or statistical significance. Model score source: results/metrics.csv and selection source: results/run_summary.json.`);
 txt(s,names[selected],72,165,1100,80,54,true,C.teal);
 txt(s,`Test RMSE  ${fmt(r.RMSE)} pp`,72,270,1100,65,42,true);
 table(s,[['Comparison on held-out test','RMSE pp','R²'],[names[selected],fmt(r.RMSE),fmt(r.R2)],['Zero return baseline',fmt(base.RMSE),fmt(base.R2)]],[620,258,258],{top:375,height:185,size:26});
 txt(s,`Relative RMSE change versus zero return: ${improvement>=0?'reduction':'increase'} of ${fmt(Math.abs(improvement),2)}%.`,72,594,1130,55,27,false,C.muted);
}
// 12
{
 const s=slide('Validation-selected model blending',
 `The best deep component on validation is ${blend.deep_component}. The pipeline evaluates XGBoost weights 0.0, 0.1, ..., 1.0 and chooses the minimum validation RMSE. The selected XGBoost weight is ${blend.xgboost_weight}. Prediction = w*XGBoost + (1-w)*deep model. Test data never chooses the component or weight. This is a blend using a dedicated development-validation block, not out-of-fold stacking. Source: results/blend_selection.json and src/pipeline.py.`);
 chart(s,'line',{position:{left:68,top:165,width:780,height:390},categories:blend.grid.map(r=>fmt(r.xgboost_weight,1)),series:[{name:'Validation RMSE',values:blend.grid.map(r=>r.RMSE),line:{fill:C.teal,width:3},marker:{symbol:'circle',size:7,fill:C.teal}}],hasLegend:false,xAxis:{title:'XGBoost weight',textStyle:{fontSize:20}},yAxis:{title:'RMSE in percentage points',numberFormatCode:'0.000',textStyle:{fontSize:19},majorGridlines:{fill:C.line,width:1}}});
 txt(s,`Deep component\n${names[blend.deep_component]}`,880,185,310,100,28,true);
 txt(s,`XGBoost weight\n${fmt(blend.xgboost_weight,1)}`,880,325,310,95,28,true);
 txt(s,`Test RMSE\n${fmt(score('blend').RMSE)} pp`,880,460,310,95,28,true);
 txt(s,'A blend only helps if its errors complement each other in future data.',72,595,1120,50,27,false,C.muted);
}
// 13
{
 const top=shap.slice(0,7).reverse();
 const s=slide('What the XGBoost model uses',
 `Native XGBoost TreeSHAP contributions, pred_contribs=True, explain the validation partition. The chart ranks mean absolute contributions in return percentage points. Maximum prediction-additivity error: ${shapCheck.max_additivity_error}. These importances describe this fitted model and data period. They do not establish economic causation. Correlated features may share attribution. Source: results/xgboost_shap_importance.csv and results/shap_check.json. XGBoost prediction documentation: https://xgboost.readthedocs.io/en/stable/prediction.html .`);
 chart(s,'bar',{position:{left:60,top:160,width:1140,height:410},categories:top.map(r=>r.feature.replaceAll('_',' ')),series:[{name:'Mean absolute TreeSHAP',values:top.map(r=>n(r.mean_abs_shap)),fill:C.teal}],barOptions:{direction:'bar',grouping:'clustered'},hasLegend:false,xAxis:{textStyle:{fontSize:21}},yAxis:{title:'Mean absolute contribution in percentage points',numberFormatCode:'0.000',textStyle:{fontSize:18},majorGridlines:{fill:C.line,width:1}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.0000',textStyle:{fontSize:18}}});
 txt(s,'Attribution explains predictions. It does not prove a causal market relationship.',72,600,1120,52,27,false,C.muted);
}
// 14
{
 const s=slide('Simplicity transparency and efficacy',
 'Qualitative comparisons concern the implementations in this project, not universal framework rankings. Efficacy uses held-out test RMSE, reported in the final column. Simplicity considers setup and code burden. Transparency concerns tools for inspecting the model, not whether its predictions are causal. Flash requires a custom compatibility adapter for this legacy library. No arbitrary numerical transparency score is invented.');
 table(s,[['Framework','Simplicity','Transparency','Test RMSE pp'],['XGBoost','Compact tree API','TreeSHAP and tree structure',fmt(score('xgboost').RMSE)],['Keras MLP','Compact network API','Weights and post hoc tools',fmt(score('keras').RMSE)],['fastai MLP','High-level learner','Training callbacks, post hoc tools',fmt(score('fastai').RMSE)],['TabNet','More tuning choices','Feature masks, limited causality',fmt(score('tabnet').RMSE)],['Flash MLP','Legacy adapter required','Explicit loop, post hoc tools',fmt(score('flash').RMSE)]],[235,260,410,231],{height:410,size:22});
 txt(s,`Baseline efficacy remains the reference: zero-return RMSE ${fmt(score('zero_return').RMSE)} pp.`,72,600,1130,52,26,false,C.muted);
}
// 15
{
 const chosen=score(summary.selected_model);const mean=score('training_mean');const zero=score('zero_return');
 const reduction=100*(n(zero.RMSE)-n(chosen.RMSE))/n(zero.RMSE);
 const s=slide('Conclusions and limits',
 `The conclusion follows the minimum-validation-RMSE selection and held-out scores. Validation selects ${summary.selected_model}, but predictive skill is very weak: held-out R2 ${chosen.R2}, direction accuracy ${100*n(chosen.direction_accuracy)}%, versus ${100*n(mean.direction_accuracy)}% for the training-mean baseline. Relative RMSE reduction versus zero return is ${reduction}%. These results do not establish a reliable or executable trading edge. Validation scores are optimistic because that partition supports stopping and blending. One index, one test era and a single seed limit generalization. Future work needs a new untouched time window, repeated seeds, true publication lags for macroeconomic features and realistic costs. Source: results/metrics.csv and results/run_summary.json.`);
 txt(s,`Validation selects ${names[summary.selected_model]}. Test R² is ${fmt(chosen.R2,4)}.`,72,165,1110,88,36,true,C.teal);
 txt(s,`Direction accuracy is ${fmt(100*n(chosen.direction_accuracy),2)}%, below the training-mean baseline at ${fmt(100*n(mean.direction_accuracy),2)}%.\nRMSE improves by ${fmt(reduction,2)}% versus zero return.`,72,285,1110,105,28);
 txt(s,'This experiment finds very weak predictive skill. One index, one test era and a single seed limit generalization.',72,410,1110,85,29);
 txt(s,'Validation supports stopping and blending. New observations and trading costs need evaluation before practical use.',72,535,1110,90,29);
}
// 16
{
 const s=slide('Demonstration and viva discussion',
 'Demo sequence: open README.md; activate the documented environment; run the tests; open notebooks/Team_12_Analysis.ipynb; run python src/demo.py --all for a quick prepared prediction; inspect results/metrics.csv and the report; optionally reproduce python src/pipeline.py, which takes longer. Explain the selected-model rule before showing test results. Viva prompts: Why forecast returns? Why chronological splits? How does the target shift work? Why can R² be negative? What does a baseline tell us? What does SHAP explain? Which part of Flash is customized? GitHub publication is a separate user account action and must not be presented as completed without an actual repository URL.');
 txt(s,'1  Inspect the frozen source data and provenance.',72,175,1110,58,31);
 txt(s,'2  Explain the target shift and the chronological partitions.',72,265,1110,68,31);
 txt(s,'3  Compare results with the simple baselines.',72,365,1110,58,31);
 txt(s,'4  Show saved models, the notebook and TreeSHAP output.',72,455,1110,68,31);
 txt(s,'Viva focus: leakage, negative R², blending and the limits of a daily forecast.',72,575,1110,64,28,true,C.teal);
}
const stamp=Date.now();const candidate=path.join(TMP,`candidate-${stamp}.pptx`);
await (await PresentationFile.exportPptx(p)).save(candidate);
await fs.mkdir(path.join(TMP,'validated'),{recursive:true});
const finalValidated=path.join(TMP,'validated',`validated-${stamp}.pptx`);
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:finalValidated,
  pythonExecutable:path.join(DEP,'python/python.exe'),
  integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...tableOwners.flatMap(n=>['--require-native-table-slide',String(n)])],
  requiredNativeTableOwnerSlides:tableOwners,requiredNativeChartOwnerSlides:chartOwners,
  materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[FONT]},verifyArtifactToolImport:true,
  receiptPath:path.join(TMP,`validation-${stamp}.json`),
});
const out=path.join(ROOT,'deliverables/Team_12_Presentation.pptx');await fs.copyFile(finalValidated,out);
const checked=await PresentationFile.importPptx(await FileBlob.load(out));
for(const [i,s] of checked.slides.items.entries()){
  const blob=await checked.export({slide:s,format:'png',scale:1});
  await fs.writeFile(path.join(TMP,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));
}
await fs.writeFile(path.join(TMP,'build_result.json'),JSON.stringify({slides:p.slides.items.length,out,tableOwners,chartOwners,result},null,2));
console.log(`Saved ${out} with ${p.slides.items.length} slides and rendered all final slides.`);
