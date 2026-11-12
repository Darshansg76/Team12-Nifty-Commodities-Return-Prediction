/** Build the professor-facing presentation from frozen experiment outputs. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DEP = process.env.CODEX_PRIMARY_RUNTIME_DEPENDENCIES || 'C:/Users/darsh/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const SKILL = process.env.PRESENTATIONS_SKILL_DIR || 'C:/Users/darsh/.codex/plugins/cache/openai-primary-runtime/presentations/26.1111.10930/skills/presentations';
process.env.RUNTIME_NODE_MODULES ||= path.join(DEP, 'node/node_modules');
const {Presentation, PresentationFile, FileBlob} = await import(pathToFileURL(path.join(DEP, 'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')));
const {finalizePresentation, resolvePresentationFont, applyPresentationChartFont} = await import(pathToFileURL(path.join(SKILL, 'container_tools/artifact_tool_utils.mjs')));
const BUILD = path.join(ROOT, '.build/slides_story');
const FINAL_PPTX = process.env.TEAM12_PRESENTATION_OUTPUT || path.join(ROOT, 'deliverables/Team_12_Presentation.pptx');
await fs.mkdir(BUILD, {recursive: true});
await fs.mkdir(path.join(BUILD, 'validated'), {recursive: true});

async function readJSON(relativePath) {
  return JSON.parse(await fs.readFile(path.join(ROOT, relativePath), 'utf8'));
}

function parseCSV(text) {
  const lines = text.replace(/^\uFEFF/, '').trim().split(/\r?\n/);
  function fields(line) {
    const result = [];
    let value = '';
    let quoted = false;
    for (let index = 0; index < line.length; index++) {
      const character = line[index];
      if (character === '"') {
        if (quoted && line[index + 1] === '"') {
          value += '"';
          index++;
        } else {
          quoted = !quoted;
        }
      } else if (character === ',' && !quoted) {
        result.push(value);
        value = '';
      } else {
        value += character;
      }
    }
    result.push(value);
    return result;
  }
  const headers = fields(lines.shift());
  return lines.map(line => Object.fromEntries(fields(line).map((value, index) => [headers[index], value])));
}

async function readCSV(relativePath) {
  return parseCSV(await fs.readFile(path.join(ROOT, relativePath), 'utf8'));
}

const [summary, data, provenance, blend, scores, folds, shap, shapCheck, raw, training, test] = await Promise.all([
  readJSON('results/run_summary.json'), readJSON('results/data_summary.json'), readJSON('data/raw/provenance.json'),
  readJSON('results/blend_selection.json'), readCSV('results/metrics.csv'), readCSV('results/cv_metrics.csv'),
  readCSV('results/xgboost_shap_importance.csv'), readJSON('results/shap_check.json'),
  readCSV('data/raw/nifty_commodities_complete_ohlc.csv'), readCSV('data/processed/train.csv'), readCSV('results/test_predictions.csv'),
]);
const FONT = resolvePresentationFont({fontFamily: 'Arial'});
const C = {paper: '#FBFCFA', ink: '#143342', teal: '#087F78', muted: '#536B75', line: '#DCE5E5', pale: '#EDF5F2', white: '#FFFFFF', copper: '#A44E36'};
const NAMES = {zero_return: 'Zero return', training_mean: 'Training mean', ridge: 'Ridge', xgboost: 'XGBoost', keras: 'Keras', fastai: 'fastai', tabnet: 'TabNet', flash: 'Lightning Flash', blend: 'Blend'};
const ORDER = ['zero_return', 'training_mean', 'ridge', 'xgboost', 'keras', 'fastai', 'tabnet', 'flash', 'blend'];
const FRAMEWORKS = ['xgboost', 'keras', 'fastai', 'tabnet', 'flash'];
const p = Presentation.create({slideSize: {width: 1280, height: 720}});
const tableSlides = [];
const chartSlides = [];
const coverage = [];
const fmt = (value, digits = 4) => Number(value).toFixed(digits);
const pct = value => `${(100 * Number(value)).toFixed(2)}%`;
const ds = value => String(value).slice(0, 10);
const score = (name, split = 'test') => scores.find(row => row.model === name && row.split === split);
const mean = values => values.reduce((total, value) => total + Number(value), 0) / values.length;
function std(values) {
  const average = mean(values);
  return Math.sqrt(values.reduce((total, value) => total + (Number(value) - average) ** 2, 0) / (values.length - 1));
}
const selected = score(summary.selected_model);
const historical = test.at(-1);
const rmseDifference = Number(selected.RMSE) - Number(score('zero_return').RMSE);
const bestTestRMSE = [...FRAMEWORKS].sort((a, b) => Number(score(a).RMSE) - Number(score(b).RMSE))[0];
const bestTestMAE = [...FRAMEWORKS].sort((a, b) => Number(score(a).MAE) - Number(score(b).MAE))[0];
const bestDeepValidation = blend.deep_component;
const SOURCE = {
  data: 'NSE Indices historical data https://www.niftyindices.com/reports/historical-data . Frozen official responses, retrieval times and SHA256 hashes are in data/raw/provenance.json.',
  index: 'NSE Indices Nifty Commodities factsheet dated 30 October 2026 https://www.niftyindices.com/Factsheet/ind_nifty_commodities.pdf . The index contains listed commodity-related companies. The modeled series is a price index.',
  metrics: 'Measurements are from results/metrics.csv, results/run_summary.json and saved actual predictions on common dates for every candidate.',
  protocol: 'Implementation is src/pipeline.py. Supplied Unit 1 PDF page 81 and Unit 2 PDF pages 7-8, 25, 47 and 59 describe chronological validation and train-only preprocessing. Detailed mappings are in references/unit_1_2_mapping.md.',
  deep: 'Supplied Deep_Learning_with_Tabular_Business_Data/1.pdf pages 6 and 25-33 cover hidden layers, common features, validation and best checkpoints. Actual architectures and stopping epochs are saved in models/<framework>/*_metadata.json.',
};

function text(slide, value, x, y, width, height, options = {}) {
  const shape = slide.shapes.add({geometry: 'textbox', position: {left: x, top: y, width, height}, fill: 'none', line: {fill: 'none', width: 0}});
  shape.text = value;
  shape.text.style = {typeface: FONT, fontSize: 28, color: C.ink, wrap: 'square', verticalAlignment: 'top', insets: 0, ...options};
  return shape;
}

function slide(title, explains, notes, dark = false) {
  const item = p.slides.add();
  item.background.fill = dark ? C.ink : C.paper;
  const number = p.slides.items.length;
  const section = number === 2 ? 'Introduction' : number <= 9 ? 'What we did' : number <= 15 ? 'Our results' : 'References';
  if (section.toLowerCase() !== title.toLowerCase()) {
    text(item, section, 72, 24, 1080, 27, {fontSize: 21, color: dark ? '#86D2C2' : C.teal});
  }
  text(item, title, 72, 65, 1136, 76, {fontSize: 44, bold: true, color: dark ? C.white : C.ink});
  text(item, String(p.slides.items.length).padStart(2, '0'), 1168, 666, 40, 22, {fontSize: 16, color: dark ? '#BED6D7' : C.muted});
  item.speakerNotes.text = notes;
  coverage.push({slide: p.slides.items.length, title, explains});
  return item;
}

function table(item, values, widths, options = {}) {
  const {top = 166, height = 390, size = 25, pad = 9, highlightRows = []} = options;
  const object = item.tables.add({rows: values.length, columns: values[0].length, left: 72, top, width: 1136, height, values, columnWidths: widths});
  object.borders.assign({style: 'solid', fill: C.line, width: 0.8});
  object.cells.block({row: 0, column: 0, rowCount: values.length, columnCount: values[0].length}).assign({
    margins: {left: 14, right: 14, top: pad, bottom: pad}, anchor: 'center', textStyle: {typeface: FONT, fontSize: size, color: C.ink},
  });
  for (let row = 0; row < values.length; row++) {
    for (let column = 0; column < values[0].length; column++) {
      const cell = object.getCell(row, column);
      const highlighted = highlightRows.includes(row);
      cell.fill = row === 0 ? C.ink : (highlighted ? '#DDEFE8' : C.white);
      cell.text.style = {typeface: FONT, fontSize: size, color: row === 0 ? C.white : C.ink, bold: row === 0 || highlighted};
    }
  }
  tableSlides.push(p.slides.items.length);
  return object;
}

function chart(item, type, config) {
  // Embedded Excel chart data retain twelve significant digits of observations.
  const series = config.series.map(series => ({
    ...series, smooth: false,
    values: series.values.map(value => Number(Number(value).toPrecision(12))),
    ...(series.xValues ? {xValues: series.xValues.map(value => Number(Number(value).toPrecision(12)))} : {}),
  }));
  const object = item.charts.add(type, {
    chartFill: C.paper, plotAreaFill: C.paper, chartLine: {fill: 'none', width: 0}, plotAreaLine: {fill: 'none', width: 0},
    titleTextStyle: {typeface: FONT, fontSize: 23, color: C.ink}, hasLegend: false, ...config, series,
  });
  applyPresentationChartFont(object, {fontFamily: FONT});
  chartSlides.push(p.slides.items.length);
  return object;
}

// Cover. The small native chart is the actual monthly price-index history.
{
  const item = p.slides.add();
  item.background.fill = C.ink;
  text(item, 'Nifty Commodities', 72, 76, 1136, 82, {fontSize: 64, bold: true, color: C.white});
  text(item, 'Benchmark return prediction', 72, 170, 1136, 68, {fontSize: 47, color: '#86D2C2'});
  text(item, 'Machine Learning with Business Data\nTeam 12', 76, 298, 620, 85, {fontSize: 29, color: '#D4E2E3'});
  const members = [['Darshan Govekar', 'PES1UG24AM355'], ['Dhanraj Rathod', 'PES1UG24AM359'], ['Shridhar Umesh Golipalle', 'PES1UG25AM814']];
  members.forEach(([name, srn], index) => {
    text(item, name, 76, 467 + index * 45, 390, 34, {fontSize: 25, color: C.white});
    text(item, srn, 470, 467 + index * 45, 300, 34, {fontSize: 25, color: '#D4E2E3'});
  });
  const monthly = new Map();
  for (const row of raw) monthly.set(row.date.slice(0, 7), row);
  const history = [...monthly.values()];
  chart(item, 'line', {
    position: {left: 800, top: 325, width: 390, height: 295}, chartFill: C.ink, plotAreaFill: C.ink,
    title: 'Price index history, 2012–2026', titleTextStyle: {typeface: FONT, fontSize: 21, color: '#BED6D7'},
    categories: history.map(row => row.date), series: [{name: 'Monthly last observed close', values: history.map(row => Number(row.close)), line: {fill: '#86D2C2', width: 3}}],
    xAxis: {visible: false}, yAxis: {visible: false},
  });
  item.speakerNotes.text = `Introduce the three members and the research question. Can the index OHLC history predict its next trading-session return? The study compares the five frameworks in the brief using a common evaluation. Names and SRNs match the supplied team allocation PDF. The cover chart shows actual monthly last observed closes. ${SOURCE.data}`;
  coverage.push({slide: 1, title: 'Nifty Commodities benchmark return prediction', explains: 'Title, course and verified team identity'});
}

{
  const example = 100 * (Number(raw[1].close) / Number(raw[0].close) - 1);
  const item = slide('Introduction to our project', 'Introduction, index meaning, forecast timing and target calculation',
    `${SOURCE.index} At the official close of session t, today OHLC is available. The outcome becomes known at the next observed close. Regression estimates the return magnitude. Direction accuracy later compares signs. The numeric example uses real source closes on 27 and 28 February 2012 and gives ${example}%. ${SOURCE.data}`);
  text(item, 'We predict the next trading-session return of the Nifty Commodities index.', 72, 170, 1136, 101, {fontSize: 36, bold: true, color: C.teal});
  text(item, 'The index tracks listed companies in commodity-related sectors.', 72, 294, 1136, 68, {fontSize: 29});
  text(item, 'We compare five machine learning\nframeworks using the same data.', 72, 405, 570, 94, {fontSize: 29});
  text(item, 'Regression predicts a number:\nthe percentage return.', 72, 545, 570, 85, {fontSize: 28, color: C.muted});
  text(item, 'Example of a one-session return', 725, 405, 483, 44, {fontSize: 27, bold: true});
  text(item, '27 Feb 2012      2,517.75\n28 Feb 2012      2,574.20', 725, 467, 483, 80, {fontSize: 27});
  text(item, `Return   +${fmt(example, 2)}%`, 725, 579, 483, 48, {fontSize: 34, bold: true, color: C.teal});
}

{
  const item = slide('What we did', 'End-to-end project workflow, source preparation and outputs',
    `${SOURCE.data} There are 4,182 downloaded sessions. The first 538 have missing official open, high and low and form one initial block through 24 February 2012. Complete OHLC runs continuously from 27 February 2012 through 9 November 2026. The source checks reject duplicate dates, nonpositive prices and inconsistent OHLC. Genuine extremes remain. The request cutoff is 10 November, a trading holiday. A 60-session window removes 59 initial rows, and the final unknown target removes one row. This gives 3,584 labeled rows. Two boundary outcomes are additionally purged when partitioning.`);
  const stages = [
    ['01', `Prepared ${Number(data.raw_rows).toLocaleString('en-US')} complete price sessions`, `Downloaded ${Number(provenance.rows).toLocaleString('en-US')} sessions; excluded 538 with incomplete prices.`],
    ['02', 'Explored the data and created inputs', 'Studied returns and volatility, then built 23 features from available prices.'],
    ['03', 'Trained and compared five frameworks', 'Used the same time periods and measured RMSE, MAE and R².'],
    ['04', 'Explained and reported the results', 'Compared simplicity and transparency; prepared the report, PPT and GitHub code.'],
  ];
  stages.forEach(([count, label, detail], index) => {
    const top = 170 + index * 115;
    text(item, count, 72, top, 160, 70, {fontSize: 49, bold: true, color: C.teal});
    text(item, label, 267, top + 2, 941, 40, {fontSize: 29, bold: true});
    text(item, detail, 267, top + 48, 941, 60, {fontSize: 25, color: C.muted});
  });
}

{
  const counts = Array(11).fill(0);
  const yearly = new Map();
  for (const row of training) {
    const bin = Math.min(10, Math.max(0, Math.floor((Number(row.target_return) + 14) / 2)));
    counts[bin]++;
    const year = row.Date.slice(0, 4);
    yearly.set(year, Math.max(yearly.get(year) || 0, Number(row.volatility_20)));
  }
  const years = [...yearly.keys()];
  const item = slide('We explored the data', 'Training return distribution, tail behavior and changing volatility',
    `Both charts use only the 2,380 training rows. Histogram bins are two percentage points wide, centered from -13 to 7. The right chart shows each year maximum of the trailing 20-session sample standard deviation. Training mean ${data.training_target_statistics.mean}%, standard deviation ${data.training_target_statistics.std} pp, skewness ${data.training_target_skew} and excess kurtosis ${data.training_target_excess_kurtosis}. Explain how changing volatility affects error scale. The notebook also contains the training correlation matrix. Sources are data/processed/train.csv and results/data_summary.json.`);
  chart(item, 'bar', {
    position: {left: 62, top: 158, width: 548, height: 370}, title: 'Training return distribution',
    categories: counts.map((_, index) => String(-13 + 2 * index).replace('-', '−')), series: [{name: 'Training sessions', values: counts, fill: C.teal}],
    barOptions: {direction: 'column', grouping: 'clustered', gapWidth: 22},
    xAxis: {title: 'Next-session return (%)', textStyle: {fontSize: 19}}, yAxis: {title: 'Sessions', textStyle: {fontSize: 19}, majorGridlines: {fill: C.line, width: 0.8}},
  });
  chart(item, 'line', {
    position: {left: 665, top: 158, width: 548, height: 370}, title: 'Annual peak of trailing volatility',
    categories: years, series: [{name: 'Annual maximum 20-session volatility', values: years.map(year => yearly.get(year)), line: {fill: C.teal, width: 3}, marker: {symbol: 'circle', size: 5, fill: C.teal}}],
    xAxis: {title: 'Training year', textStyle: {fontSize: 19}}, yAxis: {title: 'Volatility (pp)', min: 0, textStyle: {fontSize: 19}, majorGridlines: {fill: C.line, width: 0.8}},
  });
  text(item, `Mean daily return\n${fmt(data.training_target_statistics.mean)}%`, 72, 565, 340, 76, {fontSize: 27, bold: true});
  text(item, `Daily standard deviation\n${fmt(data.training_target_statistics.std)} pp`, 473, 565, 360, 76, {fontSize: 27, bold: true});
  text(item, `Training range\n${fmt(data.training_target_statistics.min, 2)}% to +${fmt(data.training_target_statistics.max, 2)}%`, 911, 565, 300, 76, {fontSize: 26, bold: true});
}

{
  const item = slide('We created 23 model inputs', 'All 23 features, their meaning and seven-day weekday encoding',
    `A feature is a numeric clue given to a model. Returns and momentum describe recent price changes: current return, lags 1/2/3/5 and 5/10/20-session momentum total eight columns. Six rolling statistics describe recent averages and volatility. Three daily structure features describe intraday return, range and overnight gap. RSI compares recent up and down moves, and drawdown measures distance below a recent high. With four calendar columns, this final group has six features. Weekday sine/cosine use 2*pi*dayofweek/7, and month uses 2*pi*(month-1)/12. The official complete-OHLC sample has ${data.calendar_encoding.weekend_source_sessions} weekend sessions. Seven days keep Saturday distinct from Monday and Sunday distinct from Tuesday. Every feature uses the current or earlier session only. Full definitions are in src/pipeline.py. ${SOURCE.protocol}`);
  table(item, [
    ['Feature group', 'Count', 'Inputs'],
    ['Recent price changes', '8', 'Today’s return, earlier returns and recent price trends'],
    ['Recent averages and risk', '6', 'Average return, volatility and distance from moving averages'],
    ['Daily price structure', '3', 'Open-to-close change, daily range and overnight gap'],
    ['Trend and calendar', '6', 'RSI, distance from a recent high, weekday and month'],
  ], [280, 120, 736], {height: 360});
  text(item, '23 features use information available by the current close.', 72, 557, 1120, 45, {fontSize: 28, bold: true, color: C.teal});
  text(item, `Weekday uses all 7 days; ${data.calendar_encoding.weekend_source_sessions} special weekend sessions are retained.`, 72, 615, 1120, 42, {fontSize: 26, color: C.muted});
}

{
  const part = data.partitions;
  const foldNotes = FRAMEWORKS.map(name => {
    const rows = folds.filter(row => row.model === name);
    return `${NAMES[name]} outer-fold RMSE mean ${fmt(mean(rows.map(row => row.RMSE)))} and sample SD ${fmt(std(rows.map(row => row.RMSE)))} pp.`;
  }).join('\n');
  const item = slide('We split the data by time', 'Date partitions, scaling, purging and expanding cross validation',
    `${SOURCE.protocol} StandardScaler fits each training block and transforms its later blocks. TargetDate must be earlier than the next partition first feature date. Within training, three expanding outer folds use 252 scoring sessions and a one-row gap. Each outer training block holds back 126 sessions to monitor early stopping and purges one additional boundary row. The final fit uses training through 2021 and validation in 2022-2023. Validation guides stopping, blend selection and final candidate selection. Final test outcomes score the selected approach.\n${foldNotes}\nComplete fold scores and dates are in results/cv_metrics.csv.`);
  table(item, [
    ['Phase', 'Training', 'Validation', 'Final test'],
    ['Feature dates', `${ds(part.train.feature_start)}\nto ${ds(part.train.feature_end)}`, `${ds(part.validation.feature_start)}\nto ${ds(part.validation.feature_end)}`, `${ds(part.test.feature_start)}\nto ${ds(part.test.feature_end)}`],
    ['Rows', String(part.train.rows), String(part.validation.rows), String(part.test.rows)],
    ['Purpose', 'Learn patterns\nand scaling', 'Stop training\nand choose a model', 'Check later\nforecast errors'],
  ], [180, 318, 319, 319], {height: 305, size: 25});
  text(item, 'Always learn from earlier dates and evaluate on later dates.', 72, 512, 1136, 45, {fontSize: 30, bold: true, color: C.teal});
  text(item, 'Three earlier periods provide extra historical checks.\nScaling learns from training only; boundary rows are removed\nwhen their next-session outcome reaches the following period.', 72, 568, 1136, 95, {fontSize: 25});
}

{
  const item = slide('We trained five frameworks', 'All required frameworks and actual model architectures',
    `${SOURCE.deep} XGBoost adds shallow trees to reduce residual errors, using depth 2, maximum 160 trees, learning rate 0.03, subsample/column sample 0.9 and L2 5. Keras 3 uses its official PyTorch backend. fastai uses actual TabularPandas and tabular_learner. Lightning Flash uses a real flash.core.model.Task and flash.Trainer with a custom numeric regression backbone. All three dense networks have 64/32 ReLU hidden layers and a linear output. TabNet uses n_d=n_a=8, three attentive steps, gamma 1.3 and sparse penalty 0.001. Sources https://keras.io/getting_started/ , https://docs.fast.ai/tabular.learner.html , https://github.com/dreamquark-ai/tabnet , https://lightning-flash.readthedocs.io/en/stable/api/generated/flash.core.model.Task.html . Implementations are in src/model_adapters.py. Flash compatibility details are in docs/REPRODUCIBILITY.md.`);
  table(item, [
    ['Framework', 'Model and role'],
    ['XGBoost', 'Adds small decision trees to correct earlier errors.'],
    ['Keras on PyTorch', 'Builds a neural network from simple layers.'],
    ['PyTorch with fastai', 'Trains a neural network with a high-level learner.'],
    ['PyTorch TabNet', 'Learns which features to attend to at each step.'],
    ['Lightning Flash', 'Organizes a neural network with a Task and Trainer.'],
  ], [330, 806], {height: 420, size: 25});
  text(item, 'All use the same inputs. Dense networks have 64 and 32 hidden units.', 72, 619, 1125, 40, {fontSize: 25, color: C.muted});
}

{
  const item = slide('How we measured performance', 'Early stopping, baselines, RMSE, MAE and signed R2',
    `Training minimizes mean squared error. Keras, fastai and Flash use Adam at 0.001 with batches of 64. TabNet uses Adam at 0.01, batch 256 and virtual batch 64. Deep models run at most 40 epochs with patience 5 and restore the best monitored weights. XGBoost uses stopping patience 20. The seed is 42 and Torch has two CPU threads. RMSE and MAE use percentage points. R2 is 1-SSE/SST, where SST measures variation around the evaluation outcome mean. Negative R2 means error exceeds that reference. Fixed zero return, fixed training mean and Ridge with alpha 100 provide simple baselines. Direction accuracy compares actual>0 with forecast>0. ${SOURCE.metrics}`);
  table(item, [
    ['Metric', 'What it tells us', 'Better result'],
    ['RMSE', 'Emphasizes large forecasting errors.', 'Lower'],
    ['MAE', 'Average absolute forecasting error.', 'Lower'],
    ['R²', 'Fit relative to the outcome variation.', 'Higher'],
    ['Direction', 'Correctly predicted up/down moves.', 'Higher'],
  ], [210, 700, 226], {height: 330, size: 27});
  text(item, 'We also compared against simple baselines:', 72, 549, 1136, 44, {fontSize: 30, bold: true, color: C.teal});
  text(item, 'Zero return, training mean and Ridge regression.', 72, 611, 1136, 44, {fontSize: 28});
}

{
  const item = slide('We chose the model on validation', 'Validation-only model choice and the optional blend outcome',
    `Choose the candidate with the lowest 2022-2023 validation RMSE, including simple baselines. That selects ${NAMES[summary.selected_model]} at ${selected ? score(summary.selected_model, 'validation').RMSE : ''} pp. The five required framework validation scores appear here; the report has all nine candidates. As an optional extension, eleven weights combine XGBoost and the best validation deep model, ${NAMES[blend.deep_component]}. Validation chooses ${100*blend.xgboost_weight}% XGBoost and ${100*(1-blend.xgboost_weight)}% ${NAMES[blend.deep_component]}. Here the zero XGBoost weight reduces the blend to fastai and adds no gain. Validation also controls stopping, so its scores may be optimistic. Test outcomes do not choose this model. Sources: results/metrics.csv and results/blend_selection.json.`);
  const ranked = [...FRAMEWORKS].sort((a, b) => Number(score(a, 'validation').RMSE) - Number(score(b, 'validation').RMSE));
  table(item, [
    ['Required framework', 'Validation RMSE (pp)'],
    ...ranked.map(name => [NAMES[name], fmt(score(name, 'validation').RMSE)]),
  ], [650, 486], {height: 310, size: 28, highlightRows: [ranked.indexOf(summary.selected_model)+1]});
  text(item, `Validation selects ${NAMES[summary.selected_model]}; the test comes afterward.`, 72, 515, 1136, 46, {fontSize: 31, bold: true, color: C.teal});
  text(item, `Optional blend: ${fmt(blend.xgboost_weight*100, 0)}% XGBoost + ${fmt((1-blend.xgboost_weight)*100, 0)}% ${NAMES[blend.deep_component]}.\nIt matches fastai here and provides no extra gain.`, 72, 583, 1136, 76, {fontSize: 27, color: C.muted});
}

{
  const item = slide(`Our results on ${test.length} test sessions`, 'Full comparison of all five frameworks, baselines and optional blend',
    `${SOURCE.metrics} The test covers feature dates 1 January 2024 through 8 November 2026 and outcomes through 9 November. Validation selected ${NAMES[summary.selected_model]} before these outcomes were scored. ${NAMES[bestTestRMSE]} has the lowest retrospective test RMSE and ${NAMES[bestTestMAE]} the lowest test MAE among the five frameworks. The validation choice is retained. Direction accuracy is ${pct(selected.direction_accuracy)} for the selected model and ${pct(score('training_mean').direction_accuracy)} for the training-mean baseline. The blend duplicates fastai here. Signed R2 values remain in the table. The green row identifies the model selected on validation.`);
  table(item, [
    ['Model', 'RMSE (pp)', 'MAE (pp)', 'R²', 'Direction'],
    ...ORDER.map(name => {
      const result = score(name);
      return [NAMES[name], fmt(result.RMSE), fmt(result.MAE), fmt(result.R2), pct(result.direction_accuracy)];
    }),
  ], [282, 211, 211, 205, 227], {top: 155, height: 425, size: 24, pad: 6, highlightRows: [ORDER.indexOf(summary.selected_model)+1]});
  text(item, `Validation selected ${NAMES[summary.selected_model]}. ${NAMES[bestTestRMSE]} has the lowest test RMSE.`, 72, 612, 1136, 49, {fontSize: 26, color: C.muted});
}

{
  const actual = test.map(row => Number(row.target_return));
  const prediction = test.map(row => Number(row[summary.selected_model]));
  const item = slide('What our forecasts show', 'Observed-versus-predicted diagnostics and interpretation',
    `The plot contains all ${test.length} test outcomes. Both axes use -12 to 8 percentage points. The dashed diagonal represents perfect predictions. Observed sample standard deviation is ${std(actual)} pp, compared with predicted standard deviation ${std(prediction)} pp. Forecasts cluster near zero and capture little observed variation, consistent with R2 ${selected.R2}. Large realized moves receive much smaller forecasts. Source is results/test_predictions.csv.`);
  chart(item, 'scatter', {
    position: {left: 55, top: 159, width: 770, height: 459}, title: 'Observed and predicted returns', scatterOptions: {style: 'lineWithMarkers'},
    series: [
      {name: `${NAMES[summary.selected_model]} forecast`, xValues: actual, values: prediction, marker: {symbol: 'circle', size: 3, fill: C.teal}, line: {fill: 'none', width: 0}},
      {name: 'Perfect prediction', xValues: [-12, 8], values: [-12, 8], marker: {symbol: 'none', size: 2}, line: {fill: C.copper, width: 1.5, style: 'dashed'}},
    ],
    xAxis: {title: 'Observed return (%)', min: -12, max: 8, majorUnit: 4, textStyle: {fontSize: 20}, majorGridlines: {fill: C.line, width: 0.8}},
    yAxis: {title: 'Predicted return (%)', min: -12, max: 8, majorUnit: 4, textStyle: {fontSize: 20}, majorGridlines: {fill: C.line, width: 0.8}},
  });
  text(item, 'Forecasts cluster\nnear zero', 886, 188, 315, 90, {fontSize: 32, bold: true, color: C.teal});
  text(item, `Observed variation\n${fmt(std(actual), 3)} pp`, 886, 326, 315, 95, {fontSize: 29});
  text(item, `Predicted variation\n${fmt(std(prediction), 3)} pp`, 886, 465, 315, 95, {fontSize: 29});
  text(item, 'Variation is the sample standard deviation. The dashed diagonal represents a perfect forecast.', 72, 627, 1136, 38, {fontSize: 23, color: C.muted});
}

{
  const labels = {return_1: 'Current return', return_lag_5: 'Return lag 5', return_lag_1: 'Return lag 1', drawdown_60: '60-session drawdown', rsi_14: '14-session RSI', momentum_20: '20-session momentum'};
  const important = shap.filter(row => Number(row.mean_abs_shap) > 0).slice(0, 6).reverse();
  const item = slide('What influenced the XGBoost forecasts', 'TreeSHAP contributions and feature interpretation',
    `Native XGBoost TreeSHAP explains validation forecasts using only trees through the best stopping iteration. The chart contains six nonzero features ranked by mean absolute contribution. Current return has the largest attribution. Contributions describe output changes relative to the model bias, and correlated features can share credit. Maximum additivity error is ${shapCheck.max_additivity_error} pp. Sources are results/xgboost_shap_importance.csv and results/shap_check.json. Method https://arxiv.org/abs/1705.07874 and https://xgboost.readthedocs.io/en/stable/prediction.html . The supplied interpretability PDFs are mapped in references/unit_3_4_mapping.md.`);
  chart(item, 'bar', {
    position: {left: 52, top: 163, width: 795, height: 433}, title: 'Validation feature contributions', categories: important.map(row => labels[row.feature] || row.feature),
    series: [{name: 'Mean absolute SHAP contribution', values: important.map(row => Number(row.mean_abs_shap)), fill: C.teal}],
    barOptions: {direction: 'bar', grouping: 'clustered', gapWidth: 55}, xAxis: {textStyle: {fontSize: 21}},
    yAxis: {title: 'Mean absolute contribution (pp)', min: 0, max: 0.007, numberFormatCode: '0.000', textStyle: {fontSize: 18}, majorGridlines: {fill: C.line, width: 0.8}},
    dataLabels: {showValue: true, position: 'outEnd', numberFormatCode: '0.0000', textStyle: {fontSize: 20}},
  });
  text(item, 'Current return has\nthe largest effect\nin this model', 884, 215, 322, 120, {fontSize: 31, bold: true, color: C.teal});
  text(item, 'These values explain\nthe model forecast.\nThey do not prove causes.', 884, 402, 322, 130, {fontSize: 26});
  text(item, 'TreeSHAP decomposes each forecast into a baseline and feature contributions.', 72, 627, 1136, 39, {fontSize: 24, color: C.muted});
}

{
  const item = slide('Our comparison of the frameworks', 'The three explicit qualitative comparison criteria',
    `Simplicity means how easy these implementations are to set up and read. Transparency means how predictions can be inspected. Efficacy means the measured errors on the same dates. XGBoost has a compact API and native TreeSHAP used in this project. Keras has readable layers and fastai a high-level learner. Their dense networks need additional attribution to explain individual predictions. TabNet provides feature masks, but only the XGBoost TreeSHAP explanation was computed here. Flash requires legacy compatibility pins. ${NAMES[bestTestRMSE]} has the lowest test RMSE; ${NAMES[bestTestMAE]} has the lowest test MAE; ${NAMES[bestDeepValidation]} has the lowest deep validation RMSE. A simpler library is not automatically the most accurate. ${SOURCE.metrics}`);
  table(item, [
    ['Framework', 'Simplicity', 'Transparency', 'Measured efficacy'],
    ['XGBoost', 'Short tabular workflow', 'TreeSHAP used here', `RMSE ${fmt(score('xgboost').RMSE)} pp`],
    ['Keras', 'Readable layers', 'Extra explanation needed', bestTestRMSE === 'keras' ? 'Lowest test RMSE' : `RMSE ${fmt(score('keras').RMSE)} pp`],
    ['fastai', 'Less training code', 'Extra explanation needed', summary.selected_model === 'fastai' ? 'Chosen by validation' : `RMSE ${fmt(score('fastai').RMSE)} pp`],
    ['TabNet', 'More model settings', 'Feature masks available', bestTestMAE === 'tabnet' ? 'Lowest test MAE' : `RMSE ${fmt(score('tabnet').RMSE)} pp`],
    ['Lightning Flash', 'Older dependencies', 'Extra explanation needed', `RMSE ${fmt(score('flash').RMSE)} pp`],
  ], [220, 295, 315, 306], {height: 400, size: 24});
  text(item, 'Efficacy means measured accuracy; simplicity and transparency are separate criteria.', 72, 612, 1136, 49, {fontSize: 24, color: C.muted});
}

{
  const item = slide('Our conclusion', 'Conclusion, study limitations and future experiments',
    `Validation selected ${NAMES[summary.selected_model]}. Its later test RMSE is ${selected.RMSE} pp and R2 ${selected.R2}. The zero-return RMSE is ${score('zero_return').RMSE}; the selected model is ${Math.abs(rmseDifference)} pp ${rmseDifference > 0 ? 'worse' : 'better'}. ${NAMES[bestTestRMSE]} has the lowest test RMSE, but it was not the validation choice. The optional blend gives no additional gain here. Direction accuracy ${pct(selected.direction_accuracy)} is below the training-mean baseline ${pct(score('training_mean').direction_accuracy)}. These results do not establish a reliable forecasting advantage. The experiment has one index, one test era and one seed. Rolling retraining and external variables with known publication times are sensible next experiments. ${SOURCE.metrics}`, true);
  text(item, 'Past prices alone give little reliable forecasting power here.', 72, 172, 1136, 100, {fontSize: 38, bold: true, color: '#86D2C2'});
  text(item, `${NAMES[summary.selected_model]} test RMSE   ${fmt(selected.RMSE)} pp\nZero-return RMSE   ${fmt(score('zero_return').RMSE)} pp\n${NAMES[summary.selected_model]} test R²          ${fmt(selected.R2)}`, 72, 307, 580, 159, {fontSize: 29, color: C.white});
  text(item, `${NAMES[bestTestRMSE]} has the lowest test RMSE.\nKeep the earlier validation choice.\nThe optional blend adds no gain.`, 728, 307, 476, 159, {fontSize: 27, color: C.white});
  text(item, 'Limits: one index, one later test period and one random seed.\nNext: retrain over time and add features available at the forecast date.', 72, 537, 1136, 96, {fontSize: 28, color: '#D4E2E3'});
}

{
  const forecast = Number(historical[summary.selected_model]);
  const actual = Number(historical.target_return);
  const item = slide('Our project demonstration', 'Saved-checkpoint demonstration with a real observed outcome',
    `Run .\\run_demo.ps1 from the project folder to show the selected saved model, or add -All to show all nine candidates. It rebuilds the features with a seven-day weekday cycle, loads the saved scaler and checkpoints, and checks against the saved historical predictions. Feature date ${historical.Date}; outcome ${historical.TargetDate}; forecast ${forecast}%; actual ${actual}%. Sunday 8 November is a real observed exchange session. This is a historical replay, not a new live forecast. The full .\\run_all.ps1 command retrains every model, runs tests, executes the notebook, rebuilds Word/PDF/PPT, and refreshes checksums and the ZIP. No prediction cache bypasses training. -ResultsOnly supports experiment reproduction without the slide-authoring runtime. Sources: src/demo.py, run_demo.ps1, run_all.ps1 and results/test_predictions.csv.`);
  text(item, `Information through ${ds(historical.Date)}\nOutcome on ${ds(historical.TargetDate)}`, 72, 163, 1136, 88, {fontSize: 30});
  text(item, `${NAMES[summary.selected_model]} forecast`, 72, 315, 500, 45, {fontSize: 28, bold: true});
  text(item, `${forecast >= 0 ? '+' : '−'}${fmt(Math.abs(forecast))}%`, 72, 377, 500, 88, {fontSize: 64, bold: true, color: C.teal});
  text(item, 'Observed return', 711, 315, 490, 45, {fontSize: 28, bold: true});
  text(item, `${actual >= 0 ? '+' : '−'}${fmt(Math.abs(actual))}%`, 711, 377, 490, 88, {fontSize: 64, bold: true, color: C.copper});
  text(item, '.\\run_demo.ps1       Show this saved prediction', 72, 544, 1136, 45, {fontSize: 28, bold: true});
  text(item, '.\\run_all.ps1           Rebuild the complete project', 72, 606, 1136, 45, {fontSize: 28, color: C.muted});
}

{
  const item = slide('References and project materials', 'Primary sources, four-unit mapping, report, notebook and GitHub',
    `${SOURCE.index}\n${SOURCE.data}\nChen and Guestrin, 2016, XGBoost https://arxiv.org/abs/1603.02754 . Arik and Pfister, 2019 preprint, TabNet https://arxiv.org/abs/1908.07442 . Lundberg and Lee, 2017, SHAP https://arxiv.org/abs/1705.07874 . The four units are mapped in references/unit_1_2_mapping.md and references/unit_3_4_mapping.md. The specific Nifty Commodities brief controls the topic. Start with README.md for the plain-language project explanation, file map and commands. The report gives the complete methodology and the executed notebook shows the calculations. Repository https://github.com/Darshansg76/Team12-Nifty-Commodities-Return-Prediction is private.`);
  text(item, 'Primary references', 72, 167, 620, 44, {fontSize: 30, bold: true, color: C.teal});
  const references = [
    ['NSE Indices', 'Historical data and Nifty Commodities factsheet', 'https://www.niftyindices.com/reports/historical-data'],
    ['Chen and Guestrin, 2016', 'XGBoost', 'https://arxiv.org/abs/1603.02754'],
    ['Arik and Pfister, 2019', 'TabNet', 'https://arxiv.org/abs/1908.07442'],
    ['Lundberg and Lee, 2017', 'SHAP', 'https://arxiv.org/abs/1705.07874'],
  ];
  references.forEach(([author, subject, url], index) => {
    const top = 239 + index * 100;
    const label = text(item, author, 72, top, 640, 36, {fontSize: 26, bold: true});
    label.hyperlink = {uri: url, isExternal: true};
    text(item, subject, 72, top + 39, 650, 48, {fontSize: 23, color: C.muted});
  });
  text(item, 'Project materials', 813, 167, 395, 45, {fontSize: 30, bold: true, color: C.teal});
  text(item, 'README and report\nExplanation, methods and results', 813, 247, 395, 88, {fontSize: 26});
  text(item, 'Executed notebook\nCalculations and graphs', 813, 362, 395, 88, {fontSize: 26});
  const link = text(item, 'GitHub repository', 813, 498, 395, 45, {fontSize: 29, bold: true, color: C.teal});
  link.hyperlink = {uri: 'https://github.com/Darshansg76/Team12-Nifty-Commodities-Return-Prediction', isExternal: true};
  text(item, 'Darshansg76\nTeam12-Nifty-Commodities-\nReturn-Prediction', 813, 550, 395, 91, {fontSize: 22, color: C.muted});
}

// Natural opening sentences help the team explain each slide in its own voice.
const openings = [
  'Our project is Nifty Commodities benchmark return prediction. We are Team 12, and we compared five machine learning frameworks on the same forecasting task.',
  'We wanted to predict the percentage return of the Nifty Commodities index for the next trading session. We used regression because the prediction is a number. The target is 100*(C(t+1)/C(t)-1), calculated from two successive observed closes. A forecast is made after the current close. The example uses actual closing values.',
  'We first prepared the official price data. We then explored it, created model inputs, trained the five frameworks and compared their results. Finally, we explained the findings and prepared the project materials.',
  'We explored the training data before comparing the models. Most returns are near zero, but some sessions have large moves. Volatility also changes over time, so forecasting errors can differ across periods.',
  'We converted the price history into 23 numeric inputs. These describe recent returns, averages, volatility and daily price movements. We used only information available at the current close, and kept all seven weekdays distinct.',
  'We kept the observations in time order. The models learned from the earlier training period, validation helped us choose the model, and the later test period checked its performance.',
  'We trained every framework requested in the brief. XGBoost uses small trees, three frameworks train compact dense neural networks, and TabNet learns which features to focus on. All five received the same inputs and dates.',
  'We measured forecasting errors using RMSE and MAE, and measured fit using R-squared. We also checked whether the forecast direction was correct. Simple baselines helped us judge whether extra model complexity added value. RMSE is sqrt(mean((actual-forecast)^2)); MAE is mean(abs(actual-forecast)); R-squared is 1-SSE/SST.',
  `We chose ${NAMES[summary.selected_model]} because it had the lowest validation RMSE. We made this choice before comparing test scores. Our optional blend reduced to the same fastai model, so it added no benefit in this run.`,
  `These are the results on ${test.length} later test sessions. ${NAMES[summary.selected_model]} is highlighted because validation selected it. ${NAMES[bestTestRMSE]} had the lowest test RMSE, but that later result did not change our earlier model choice.`,
  'Our forecasts stayed close to zero even when the observed return moved sharply. This explains why the selected model captured little of the actual variation.',
  'We used TreeSHAP to inspect the XGBoost forecasts. Current return had the largest average contribution. This explains the fitted model, and does not prove an economic cause.',
  'We compared the frameworks on three criteria. Simplicity concerns how easy the implementation is to use, transparency concerns how forecasts can be explained, and efficacy concerns the measured forecasting errors.',
  'We completed the required framework comparison, but the results show limited forecasting power from this index history alone. The selected fastai model did not improve test RMSE over zero return. More time periods and additional information would be useful next experiments.',
  'This is a replay of one actual historical prediction using our saved fastai model. The forecast and observed return are shown side by side. The demo command loads the model, while the full command rebuilds the project.',
  'These are our main data and method references. The report provides the full explanation, the notebook shows the calculations, and the private GitHub repository contains the code and project files.',
];
for (const [index, item] of p.slides.items.entries()) {
  item.speakerNotes.text = `${openings[index]}\n\n${item.speakerNotes.text}`;
}
if (p.slides.items.length !== 16) throw new Error('The presentation outline requires 16 slides.');
const stamp = Date.now();
const candidatePath = path.join(BUILD, `candidate-${stamp}.pptx`);
const validatedPath = path.join(BUILD, 'validated', `validated-${stamp}.pptx`);
await (await PresentationFile.exportPptx(p)).save(candidatePath);
const requiredTables = [...new Set(tableSlides)];
const requiredCharts = [...new Set(chartSlides)];
const result = await finalizePresentation({
  workspaceDir: ROOT, candidatePath, finalPath: validatedPath, explicitTotalSlideCount: 16,
  pythonExecutable: path.join(DEP, 'python/python.exe'),
  integrityValidatorPath: path.join(SKILL, 'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(SKILL, 'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs: ['--expected-slide-size-emu', '12192000,6858000', '--validate-bullet-geometry', '--validate-heading-fit', ...requiredTables.flatMap(number => ['--require-native-table-slide', String(number)])],
  requiredNativeTableOwnerSlides: requiredTables, requiredNativeChartOwnerSlides: requiredCharts,
  materializeLiteralChartWorkbooks: true, fontPolicy: {basis: 'design', families: [FONT]}, verifyArtifactToolImport: true,
  receiptPath: path.join(BUILD, `validation-${stamp}.json`),
});
const checked = await PresentationFile.importPptx(await FileBlob.load(validatedPath));
for (const [index, item] of checked.slides.items.entries()) {
  const png = await checked.export({slide: item, format: 'png', scale: 1});
  await fs.writeFile(path.join(BUILD, `slide-${String(index + 1).padStart(2, '0')}.png`), new Uint8Array(await png.arrayBuffer()));
}
await fs.writeFile(path.join(BUILD, 'content_coverage.json'), JSON.stringify(coverage, null, 2));
await fs.writeFile(path.join(BUILD, 'build_result.json'), JSON.stringify({slides: checked.slides.items.length, candidatePath, validatedPath, tableSlides: requiredTables, chartSlides: requiredCharts, result}, null, 2));
await fs.copyFile(validatedPath, FINAL_PPTX);
console.log(`Saved and rendered ${checked.slides.items.length} slides. Native tables on ${requiredTables.join(', ')}. Native charts on ${requiredCharts.join(', ')}.`);
