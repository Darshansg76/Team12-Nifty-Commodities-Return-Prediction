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
const BUILD = path.join(ROOT, '.build/slides_refined');
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
const reduction = 100 * (Number(score('zero_return').RMSE) - Number(selected.RMSE)) / Number(score('zero_return').RMSE);
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
  text(item, title, 72, 48, 1136, 76, {fontSize: 44, bold: true, color: dark ? C.white : C.ink});
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
  const item = slide('Prediction target', 'Introduction, index meaning, forecast timing and target calculation',
    `${SOURCE.index} At the official close of session t, today OHLC is available. The outcome becomes known at the next observed close. Regression estimates the return magnitude. Direction accuracy later compares signs. The numeric example uses real source closes on 27 and 28 February 2012 and gives ${example}%. ${SOURCE.data}`);
  text(item, 'Nifty Commodities tracks listed companies in commodity-related sectors.', 72, 160, 1080, 85, {fontSize: 31});
  text(item, 'r(t+1) = 100 × [C(t+1) / C(t) − 1]', 72, 279, 1136, 65, {fontSize: 42, bold: true, color: C.teal});
  text(item, 'C(t) is the closing index value at session t.', 72, 352, 1136, 35, {fontSize: 24, color: C.muted});
  text(item, 'Forecast after the current close.\nEvaluate at the next observed trading close.', 72, 411, 540, 95, {fontSize: 28});
  text(item, 'Actual source example', 710, 410, 490, 38, {fontSize: 28, bold: true});
  text(item, '27 Feb 2012      2,517.75\n28 Feb 2012      2,574.20', 710, 462, 490, 80, {fontSize: 27});
  text(item, `Next-session return   +${fmt(example, 2)}%`, 710, 570, 490, 48, {fontSize: 29, bold: true, color: C.teal});
}

{
  const item = slide('Data and preparation', 'Official source, coverage, missing values and warm-up',
    `${SOURCE.data} There are 4,182 downloaded sessions. The first 538 have missing official open, high and low and form one initial block through 24 February 2012. Complete OHLC runs continuously from 27 February 2012 through 9 November 2026. The source checks reject duplicate dates, nonpositive prices and inconsistent OHLC. Genuine extremes remain. The request cutoff is 10 November, a trading holiday. A 60-session window removes 59 initial rows, and the final unknown target removes one row. This gives 3,584 labeled rows. Two boundary outcomes are additionally purged when partitioning.`);
  const stages = [
    [Number(provenance.rows).toLocaleString('en-US'), 'Downloaded sessions', 'Official NSE Indices history from January 2010'],
    ['538', 'Initial sessions excluded', 'Official open, high and low values are missing'],
    [Number(data.raw_rows).toLocaleString('en-US'), 'Complete OHLC sessions', '27 February 2012 to 9 November 2026'],
    [Number(data.feature_rows).toLocaleString('en-US'), 'Labeled feature rows', 'Trailing-window warm-up and final unknown target removed'],
  ];
  stages.forEach(([count, label, detail], index) => {
    const top = 164 + index * 115;
    text(item, count, 72, top, 225, 70, {fontSize: 52, bold: true, color: C.teal});
    text(item, label, 340, top + 2, 850, 40, {fontSize: 29, bold: true});
    text(item, detail, 340, top + 48, 850, 57, {fontSize: 25, color: C.muted});
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
  const item = slide('Exploratory data analysis', 'Training return distribution, tail behavior and changing volatility',
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
  text(item, `Excess kurtosis\n${fmt(data.training_target_excess_kurtosis, 2)}`, 911, 565, 290, 76, {fontSize: 27, bold: true});
}

{
  const item = slide('Features available at the forecast close', 'All 23 features and causal construction',
    `Returns and momentum comprise current return, lags 1/2/3/5 and 5/10/20-session momentum, totaling eight columns. Rolling statistics are volatility, mean return and close-to-SMA at 5 and 20 sessions, totaling six. Daily structure has intraday return, range/close and overnight gap. RSI14, drawdown60 and four calendar sine/cosine terms total six. RSI uses simple rolling averages. Every feature is causal. Full definitions are in FEATURE_COLUMNS and build_features in src/pipeline.py. ${SOURCE.protocol}`);
  table(item, [
    ['Feature group', 'Count', 'Inputs'],
    ['Returns and momentum', '8', 'Current return, four lags, 5/10/20-session momentum'],
    ['Rolling statistics', '6', '5/20-session volatility, means and moving-average distances'],
    ['Daily price structure', '3', 'Intraday return, high–low range and overnight gap'],
    ['Trend and calendar', '6', 'RSI 14, drawdown 60, weekday/month sine and cosine'],
  ], [280, 120, 736], {height: 360});
  text(item, '23 numeric features use prices available through session t.', 72, 573, 1120, 45, {fontSize: 30, bold: true, color: C.teal});
  text(item, 'The outcome belongs to the next observed session.', 72, 622, 1120, 36, {fontSize: 25, color: C.muted});
}

{
  const part = data.partitions;
  const foldNotes = FRAMEWORKS.map(name => {
    const rows = folds.filter(row => row.model === name);
    return `${NAMES[name]} outer-fold RMSE mean ${fmt(mean(rows.map(row => row.RMSE)))} and sample SD ${fmt(std(rows.map(row => row.RMSE)))} pp.`;
  }).join('\n');
  const item = slide('Chronological evaluation', 'Date partitions, scaling, purging and expanding cross validation',
    `${SOURCE.protocol} StandardScaler fits each training block and transforms its later blocks. TargetDate must be earlier than the next partition first feature date. Within training, three expanding outer folds use 252 scoring sessions and a one-row gap. Each outer training block holds back 126 sessions to monitor early stopping and purges one additional boundary row. The final fit uses training through 2021 and validation in 2022-2023. Validation guides stopping, blend selection and final candidate selection. Final test outcomes score the selected approach.\n${foldNotes}\nComplete fold scores and dates are in results/cv_metrics.csv.`);
  table(item, [
    ['Phase', 'Training', 'Validation', 'Final test'],
    ['Feature dates', `${ds(part.train.feature_start)}\nto ${ds(part.train.feature_end)}`, `${ds(part.validation.feature_start)}\nto ${ds(part.validation.feature_end)}`, `${ds(part.test.feature_start)}\nto ${ds(part.test.feature_end)}`],
    ['Rows', String(part.train.rows), String(part.validation.rows), String(part.test.rows)],
    ['Purpose', 'Fit models\nand scaler', 'Stop training\nand select blend', 'Evaluate the\nselected approach'],
  ], [180, 318, 319, 319], {height: 305, size: 25});
  text(item, 'Three expanding folds stay inside the training period.', 72, 517, 1136, 45, {fontSize: 30, bold: true, color: C.teal});
  text(item, 'Each fold uses 126 sessions for stopping and 252 for scoring.\nTraining-only scaling and one-row gaps protect the time boundaries.', 72, 577, 1136, 75, {fontSize: 26});
}

{
  const item = slide('Five framework implementations', 'All required frameworks and actual model architectures',
    `${SOURCE.deep} XGBoost adds shallow trees to reduce residual errors, using depth 2, maximum 160 trees, learning rate 0.03, subsample/column sample 0.9 and L2 5. Keras 3 uses its official PyTorch backend. fastai uses actual TabularPandas and tabular_learner. Lightning Flash uses a real flash.core.model.Task and flash.Trainer with a custom numeric regression backbone. All three dense networks have 64/32 ReLU hidden layers and a linear output. TabNet uses n_d=n_a=8, three attentive steps, gamma 1.3 and sparse penalty 0.001. Sources https://keras.io/getting_started/ , https://docs.fast.ai/tabular.learner.html , https://github.com/dreamquark-ai/tabnet , https://lightning-flash.readthedocs.io/en/stable/api/generated/flash.core.model.Task.html . Implementations are in src/model_adapters.py. Flash compatibility details are in docs/REPRODUCIBILITY.md.`);
  table(item, [
    ['Framework', 'Model and role'],
    ['XGBoost', 'Boosted trees learn residual errors. Depth 2, up to 160 trees.'],
    ['Keras on PyTorch', 'Dense network with 64 and 32 ReLU units, dropout and L2.'],
    ['PyTorch with fastai', 'tabular_learner trains a 64/32 dense regression network.'],
    ['PyTorch TabNet', 'Three attentive steps select features. Width 8 per step.'],
    ['Lightning Flash', 'Flash Task and Trainer fit a custom 64/32 dense network.'],
  ], [330, 806], {height: 420, size: 25});
  text(item, 'Every framework receives the same features and forecast target.', 72, 619, 1125, 40, {fontSize: 26, color: C.muted});
}

{
  const item = slide('Training and error measures', 'Early stopping, baselines, RMSE, MAE and signed R2',
    `Training minimizes mean squared error. Keras, fastai and Flash use Adam at 0.001 with batches of 64. TabNet uses Adam at 0.01, batch 256 and virtual batch 64. Deep models run at most 40 epochs with patience 5 and restore the best monitored weights. XGBoost uses stopping patience 20. The seed is 42 and Torch has two CPU threads. RMSE and MAE use percentage points. R2 is 1-SSE/SST, where SST measures variation around the evaluation outcome mean. Negative R2 means error exceeds that reference. Fixed zero return, fixed training mean and Ridge with alpha 100 provide simple baselines. Direction accuracy compares actual>0 with forecast>0. ${SOURCE.metrics}`);
  const measures = [
    ['RMSE', 'sqrt(mean((actual − forecast)²))', 'Emphasizes large errors. Measured in percentage points.'],
    ['MAE', 'mean(abs(actual − forecast))', 'Average absolute error. Measured in percentage points.'],
    ['R²', '1 − squared error / outcome variation', '1 is a perfect fit. Negative values can occur.'],
  ];
  measures.forEach(([name, formula, explanation], index) => {
    const top = 168 + index * 145;
    text(item, name, 72, top, 150, 52, {fontSize: 37, bold: true, color: C.teal});
    text(item, formula, 250, top + 2, 930, 45, {fontSize: 29, bold: true});
    text(item, explanation, 250, top + 61, 930, 49, {fontSize: 26, color: C.muted});
  });
  text(item, 'Deep models use up to 40 epochs with early stopping. Baselines are zero return, training mean and Ridge.', 72, 619, 1136, 48, {fontSize: 24});
}

{
  const item = slide('Validation chooses the blend', 'Innovation, selection rule, blend formula and validation score',
    `Validation chooses ${blend.deep_component} among the four deep frameworks by RMSE. Eleven candidate XGBoost weights 0.0 through 1.0 are then scored on the same validation block. The winning weight is ${blend.xgboost_weight}. Prediction=0.1*XGBoost+0.9*TabNet. The blend validation RMSE is ${score('blend', 'validation').RMSE} pp. TabNet alone scores ${score('tabnet', 'validation').RMSE} pp and training mean ${score('training_mean', 'validation').RMSE} pp. Validation also supports stopping and selection, which makes its scores optimistic. The later test evaluates the chosen configuration. The full table is results/metrics.csv and the weight grid is results/blend_selection.json.`);
  text(item, 'Forecast = 0.10 × XGBoost\n                 + 0.90 × TabNet', 72, 185, 530, 122, {fontSize: 34, bold: true, color: C.teal});
  text(item, 'The 2022–2023 validation period\nselects the deep component and weight.', 72, 353, 510, 95, {fontSize: 28});
  text(item, `${fmt(score('blend', 'validation').RMSE)} pp`, 72, 503, 510, 70, {fontSize: 49, bold: true});
  text(item, 'Validation RMSE of the selected blend', 72, 584, 520, 63, {fontSize: 25, color: C.muted});
  chart(item, 'line', {
    position: {left: 634, top: 172, width: 580, height: 430}, title: 'Validation error across blend weights',
    categories: blend.grid.map(row => fmt(row.xgboost_weight, 1)),
    series: [{name: 'Validation RMSE', values: blend.grid.map(row => row.RMSE), line: {fill: C.teal, width: 3}, marker: {symbol: 'circle', size: 6, fill: C.teal}}],
    xAxis: {title: 'XGBoost weight', textStyle: {fontSize: 19}},
    yAxis: {title: 'RMSE (pp)', min: 1.108, max: 1.124, majorUnit: 0.004, numberFormatCode: '0.000', textStyle: {fontSize: 19}, majorGridlines: {fill: C.line, width: 0.8}},
  });
}

{
  const item = slide('Test results on 709 future sessions', 'Full comparison of all five frameworks, baselines and blend',
    `${SOURCE.metrics} The test covers feature dates 1 January 2024 through 8 November 2026 and outcomes through 9 November. Validation selected the blend before these outcomes were scored. Keras has the lowest retrospective test RMSE and fastai has the lowest test MAE. The earlier blend selection is retained. The blend direction accuracy is ${pct(selected.direction_accuracy)}, and the training mean matches the majority positive-return class at ${pct(score('training_mean').direction_accuracy)}. Signed R2 values remain in the table. The green row identifies the selected model.`);
  table(item, [
    ['Model', 'RMSE (pp)', 'MAE (pp)', 'R²', 'Direction'],
    ...ORDER.map(name => {
      const result = score(name);
      return [NAMES[name], fmt(result.RMSE), fmt(result.MAE), fmt(result.R2), pct(result.direction_accuracy)];
    }),
  ], [282, 211, 211, 205, 227], {top: 155, height: 425, size: 24, pad: 6, highlightRows: [9]});
  text(item, 'Validation selected Blend. Keras has the lowest test RMSE.', 72, 612, 1136, 49, {fontSize: 26, color: C.muted});
}

{
  const actual = test.map(row => Number(row.target_return));
  const prediction = test.map(row => Number(row[summary.selected_model]));
  const item = slide('Forecast behavior on the test period', 'Observed-versus-predicted diagnostics and interpretation',
    `The plot contains all ${test.length} test outcomes. Both axes use -12 to 8 percentage points. The dashed diagonal represents perfect predictions. Observed sample standard deviation is ${std(actual)} pp, compared with predicted standard deviation ${std(prediction)} pp. Forecasts cluster near zero and capture little observed variation, consistent with R2 ${selected.R2}. Large realized moves receive much smaller forecasts. Source is results/test_predictions.csv.`);
  chart(item, 'scatter', {
    position: {left: 55, top: 159, width: 770, height: 459}, title: 'Observed and predicted returns', scatterOptions: {style: 'lineWithMarkers'},
    series: [
      {name: 'Blend forecast', xValues: actual, values: prediction, marker: {symbol: 'circle', size: 3, fill: C.teal}, line: {fill: 'none', width: 0}},
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
  const item = slide('Interpreting the XGBoost forecasts', 'TreeSHAP contributions and feature interpretation',
    `Native XGBoost TreeSHAP explains validation forecasts using only trees through the best stopping iteration. The chart contains six nonzero features ranked by mean absolute contribution. Current return has the largest attribution. Contributions describe output changes relative to the model bias, and correlated features can share credit. Maximum additivity error is ${shapCheck.max_additivity_error} pp. Sources are results/xgboost_shap_importance.csv and results/shap_check.json. Method https://arxiv.org/abs/1705.07874 and https://xgboost.readthedocs.io/en/stable/prediction.html . The supplied interpretability PDFs are mapped in references/unit_3_4_mapping.md.`);
  chart(item, 'bar', {
    position: {left: 52, top: 163, width: 795, height: 433}, title: 'Validation feature contributions', categories: important.map(row => labels[row.feature] || row.feature),
    series: [{name: 'Mean absolute SHAP contribution', values: important.map(row => Number(row.mean_abs_shap)), fill: C.teal}],
    barOptions: {direction: 'bar', grouping: 'clustered', gapWidth: 55}, xAxis: {textStyle: {fontSize: 21}},
    yAxis: {title: 'Mean absolute contribution (pp)', min: 0, max: 0.007, numberFormatCode: '0.000', textStyle: {fontSize: 18}, majorGridlines: {fill: C.line, width: 0.8}},
    dataLabels: {showValue: true, position: 'outEnd', numberFormatCode: '0.0000', textStyle: {fontSize: 20}},
  });
  text(item, 'Current return has\nthe largest attribution', 884, 215, 322, 120, {fontSize: 31, bold: true, color: C.teal});
  text(item, 'Contributions measure\neffects on the fitted\nmodel output.', 884, 402, 322, 130, {fontSize: 27});
  text(item, 'TreeSHAP decomposes each forecast into a baseline and feature contributions.', 72, 627, 1136, 39, {fontSize: 24, color: C.muted});
}

{
  const item = slide('Simplicity transparency and efficacy', 'The three explicit qualitative comparison criteria',
    `Simplicity concerns setup and maintenance for the implemented models. Transparency concerns inspection tools. Efficacy uses the common held-out dates. XGBoost has a compact tabular API and native TreeSHAP. Keras has a readable Dense API. fastai provides a high-level learner and callbacks. Dense networks can use post-hoc attribution. TabNet exposes attentive masks and additional tuning settings. Flash has explicit training steps and requires legacy compatibility pins. Keras has the lowest test RMSE ${score('keras').RMSE}. fastai has the lowest test MAE ${score('fastai').MAE}. TabNet has the lowest standalone deep validation RMSE. ${SOURCE.metrics}`);
  table(item, [
    ['Framework', 'Simplicity', 'Transparency', 'Measured efficacy'],
    ['XGBoost', 'Compact tabular API', 'Native TreeSHAP', `RMSE ${fmt(score('xgboost').RMSE)} pp`],
    ['Keras', 'Readable Dense API', 'Post-hoc attribution', 'Lowest test RMSE'],
    ['fastai', 'High-level learner', 'Post-hoc attribution', 'Lowest test MAE'],
    ['TabNet', 'More tuning settings', 'Attentive feature masks', 'Best deep validation'],
    ['Lightning Flash', 'Legacy setup required', 'Explicit training steps', `RMSE ${fmt(score('flash').RMSE)} pp`],
  ], [220, 295, 315, 306], {height: 400, size: 24});
  text(item, 'The setup comparison refers to the implementations used in this project.', 72, 612, 1136, 49, {fontSize: 26, color: C.muted});
}

{
  const item = slide('Conclusions and next steps', 'Conclusion, study limitations and future experiments',
    `Validation selected the 10% XGBoost and 90% TabNet blend. Test RMSE ${selected.RMSE} pp, R2 ${selected.R2} and relative RMSE improvement ${reduction}% over zero return indicate weak daily-return predictability. Direction accuracy ${pct(selected.direction_accuracy)} is below the fixed training mean ${pct(score('training_mean').direction_accuracy)}. The experiment uses one index own OHLC and calendar, one test era and one seed. Future experiments can add rolling retraining, repeated seeds and external variables with correct historical publication lags. Trading evaluation requires instrument, timing and cost assumptions. ${SOURCE.metrics}`, true);
  text(item, 'The selected blend captures little daily return variation.', 72, 172, 1136, 100, {fontSize: 38, bold: true, color: '#86D2C2'});
  text(item, `Test RMSE   ${fmt(selected.RMSE)} pp\nTest R²         ${fmt(selected.R2)}`, 72, 305, 520, 110, {fontSize: 32, color: C.white});
  text(item, `${fmt(reduction, 2)}% RMSE improvement over zero return.\nDirection accuracy ${pct(selected.direction_accuracy)}.\nTraining-mean direction accuracy ${pct(score('training_mean').direction_accuracy)}.`, 692, 305, 510, 142, {fontSize: 27, color: C.white});
  text(item, 'One index, one test era and one seed limit generalization.\nNext experiments can add rolling retraining and time-aligned external features.', 72, 528, 1136, 103, {fontSize: 28, color: '#D4E2E3'});
}

{
  const forecast = Number(historical[summary.selected_model]);
  const actual = Number(historical.target_return);
  const item = slide('Historical prediction demonstration', 'Saved-checkpoint demonstration with a real observed outcome',
    `Run python src/demo.py --all from the prepared project environment. It rebuilds features, loads the scaler and actual saved checkpoints, and compares predictions with the frozen CSV. The final feature date is ${historical.Date}, with outcome on ${historical.TargetDate}. Sunday 8 November is an observed exchange session in the supplied source. Blend forecast ${forecast}% and actual return ${actual}%. The demo reproduces all nine candidates within 0.00001 percentage points. Thirteen tests have passed, including the five actual framework reloads. This example is a historical replay. Sources are src/demo.py and the final row of results/test_predictions.csv.`);
  text(item, `Information through ${ds(historical.Date)}\nOutcome on ${ds(historical.TargetDate)}`, 72, 163, 1136, 88, {fontSize: 30});
  text(item, 'Blend forecast', 72, 315, 500, 45, {fontSize: 28, bold: true});
  text(item, `${forecast >= 0 ? '+' : '−'}${fmt(Math.abs(forecast))}%`, 72, 377, 500, 88, {fontSize: 64, bold: true, color: C.teal});
  text(item, 'Observed return', 711, 315, 490, 45, {fontSize: 28, bold: true});
  text(item, `${actual >= 0 ? '+' : '−'}${fmt(Math.abs(actual))}%`, 711, 377, 490, 88, {fontSize: 64, bold: true, color: C.copper});
  text(item, 'python src/demo.py --all', 72, 550, 1136, 49, {fontSize: 31, bold: true});
  text(item, 'Loads saved checkpoints and reproduces the frozen historical forecasts.', 72, 613, 1136, 46, {fontSize: 25, color: C.muted});
}

{
  const item = slide('References and project materials', 'Primary sources, four-unit mapping, report, notebook and GitHub',
    `${SOURCE.index}\n${SOURCE.data}\nChen and Guestrin, 2016, XGBoost https://arxiv.org/abs/1603.02754 . Arik and Pfister, 2019 preprint, TabNet https://arxiv.org/abs/1908.07442 . Lundberg and Lee, 2017, SHAP https://arxiv.org/abs/1705.07874 . The four units are mapped in references/unit_1_2_mapping.md and references/unit_3_4_mapping.md. The specific Nifty Commodities project brief controls the topic. Repository https://github.com/Darshansg76/Team12-Nifty-Commodities-Return-Prediction is private and the instructor needs access. Report deliverables/Team_12_Project_Report.pdf, notebook notebooks/Team_12_Analysis.ipynb and viva guide docs/VIVA_GUIDE.md contain further details.`);
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
  text(item, 'Report\nDetailed methods and results', 813, 247, 395, 88, {fontSize: 26});
  text(item, 'Executed notebook\nCode, graphs and saved outputs', 813, 362, 395, 88, {fontSize: 26});
  const link = text(item, 'GitHub repository', 813, 498, 395, 45, {fontSize: 29, bold: true, color: C.teal});
  link.hyperlink = {uri: 'https://github.com/Darshansg76/Team12-Nifty-Commodities-Return-Prediction', isExternal: true};
  text(item, 'Darshansg76\nTeam12-Nifty-Commodities-\nReturn-Prediction', 813, 550, 395, 91, {fontSize: 22, color: C.muted});
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
await fs.copyFile(validatedPath, path.join(ROOT, 'deliverables/Team_12_Presentation.pptx'));
console.log(`Saved and rendered ${checked.slides.items.length} slides. Native tables on ${requiredTables.join(', ')}. Native charts on ${requiredCharts.join(', ')}.`);
