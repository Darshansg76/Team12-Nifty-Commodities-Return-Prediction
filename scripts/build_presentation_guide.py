"""Build the team's detailed slide explanations and presentation scripts."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import re

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deliverables' / 'Team_12_Presentation_Guide.docx'
DECK = ROOT / 'deliverables' / 'Team_12_Presentation.pptx'
summary = json.loads((ROOT / 'results/run_summary.json').read_text())
data = json.loads((ROOT / 'results/data_summary.json').read_text())
scores = list(csv.DictReader((ROOT / 'results/metrics.csv').open()))
blend = json.loads((ROOT / 'results/blend_selection.json').read_text())
NAMES = {'zero_return':'Zero return', 'training_mean':'Training mean', 'ridge':'Ridge',
         'xgboost':'XGBoost', 'keras':'Keras', 'fastai':'fastai', 'tabnet':'TabNet',
         'flash':'Lightning Flash', 'blend':'Blend'}

def metric(name, field, split='test'):
    return float(next(r[field] for r in scores if r['model'] == name and r['split'] == split))

SLIDES = [
    dict(title='Nifty Commodities', seconds=30,
         script='''Good morning. We are Team 12: Darshan Govekar, Dhanraj Rathod and Shridhar Umesh Golipalle. Our project is Nifty Commodities benchmark return prediction. We investigated whether historical index prices can help predict the next trading session's percentage return. We compared five machine learning frameworks using the same data and evaluation process. We will introduce the problem, explain our work and present the results.''',
         explanation=[
             'Nifty Commodities is an equity index representing listed companies in commodity-related industries. The observations are index values. The project does not directly forecast a physical commodity price such as the price of gold or crude oil.',
             'A benchmark is a reference index used to describe market performance. Here, return prediction means predicting the percentage change in the benchmark between two observed closing values. A higher historical index level does not establish that the following session return is predictable.',
             'The cover chart shows actual monthly last observed closing values from the complete modeling period. It provides historical context; it is not a chart of model predictions. Present the team and objective without explaining every market movement on this slide.'
         ],
         point='Point briefly to the project title and team names. Identify the small chart as historical index values.',
         precision='The project predicts the next session percentage return. It does not claim a guaranteed market movement or a profitable trading strategy.',
         transition='We will begin with the prediction problem and a simple example of a return.'),
    dict(title='Introduction to our project', seconds=45,
         script='''Our objective is to predict the next trading-session return of the Nifty Commodities index using information available after the current session closes. We use regression because the output is a number, such as a positive or negative percentage return. In the example, the index increased from 2,517.75 to 2,574.20. This is a return of about 2.24 percent. Our model tries to estimate such a return before the next observed closing value is known. We compare five frameworks on this same task.''',
         explanation=[
             'A return expresses the change relative to the starting value. In the slide example, the increase is 56.45 index points. Dividing that change by 2,517.75 and multiplying by 100 gives approximately 2.2421 percent, displayed as 2.24 percent.',
             'The forecast is made after the official close of feature date t. At that time, the current session open, high, low and close are available. The target becomes known only at the next observed close. The next session can occur after a holiday or weekend rather than on the next calendar day.',
             'Regression predicts the numerical return. Classification would predict a category such as up or down. This project trains regression models and later checks their predicted signs as an additional direction diagnostic. Direction accuracy is not a separately trained classifier.'
         ],
         equation='return',
         point='Point to the two dates and closing values, then to the displayed positive return. Explain the calculation using those values.',
         precision='A 2.24 percent index return is a relative change in the index, rather than an increase of 2.24 index points.',
         transition='The next slide gives an overview of how we completed the project.'),
    dict(title='What we did', seconds=30,
         script='''We completed the project in four stages. First, we prepared the official data and retained 3,644 sessions with complete prices. Second, we explored the data and created 23 model inputs. Third, we trained the five required frameworks using the same time periods and compared their errors. Finally, we explained the forecasts, compared implementation simplicity and transparency, and prepared the report, presentation and GitHub repository.''',
         explanation=[
             'The original download contains 4,182 sessions beginning in 2010. The first 538 form an initial block with missing official open, high and low values. We excluded that block rather than inventing those prices. The retained complete period runs from 27 February 2012 through 9 November 2026.',
             'OHLC means open, high, low and close. These are the opening, highest, lowest and closing values for a session. Source checks also reject duplicate dates, nonpositive prices and inconsistent daily price ranges. Genuine extreme movements are retained.',
             'The workflow separates data preparation, exploration, modeling and interpretation. The requested end date is 10 November 2026, but the final returned session is 9 November. The original source responses and their hashes remain available so the dataset can be checked.'
         ],
         point='Follow the four numbered steps in order. Say what each step produced; leave detailed features and model settings for later slides.',
         precision='The 538 excluded sessions had incomplete official OHLC values. They were not removed because a model predicted them poorly.',
         transition='We first explored the training data to understand its distribution and changing volatility.'),
    dict(title='We explored the data', seconds=60,
         script='''Before interpreting model results, we explored the training data. The left chart shows the distribution of next-session returns. Most observations are close to zero, but a few sessions have large positive or negative returns. The mean is about 0.0476 percent, while the standard deviation is about 1.2769 percentage points. This shows that the small positive average sits inside much larger daily fluctuations. The right chart shows that volatility changes over time, with a particularly large annual peak in 2020. The training range extends from about minus 12.25 percent to plus 7.60 percent. These patterns make daily return forecasting challenging.''',
         explanation=[
             'EDA means exploratory data analysis. It helps describe data quality, distributions and relationships before making claims about model efficacy. The graphs and descriptive statistics on this slide use the 2,380 training rows, so later test outcomes do not guide model selection.',
             'The histogram horizontal axis represents percentage return; its vertical axis counts observations in each interval. A tall central region means small returns are common. The less frequent observations far from zero are the tails. Those extremes remain part of evaluation.',
             'Standard deviation measures the spread of returns around their average. It is not a maximum error or a guarantee that every return lies within that distance. The right chart plots the maximum trailing 20-session volatility reached in each year. It does not show the average volatility of each year. The notebook also provides the training correlation matrix.'
         ],
         point='Use the left chart to explain the central concentration and tails. Use the right chart to explain changing volatility, then connect both to the statistics below.',
         precision='Keep the periods and units attached: these are training statistics; the mean is a percent return and standard deviation is in percentage points.',
         transition='We then converted the available price history into numerical inputs for the models.'),
    dict(title='We created 23 model inputs', seconds=75,
         script='''A feature is a numerical clue given to the model. We created 23 features in four groups. Eight features describe current and earlier returns and recent price trends. Six describe average returns, volatility and distance from moving averages. Three describe the daily price structure: the open-to-close change, daily range and overnight gap. The remaining six describe RSI, drawdown and calendar information. RSI compares recent upward and downward movements, while drawdown measures distance below a recent high. Every feature uses information available by the current close. We also use a seven-day weekday cycle because the official sample contains 18 special weekend sessions. This keeps Saturday and Sunday distinct from other weekdays. The next session return is the outcome to predict and is never supplied as an input.''',
         explanation=[
             'The eight recent-change inputs are the current return, four lagged returns at 1, 2, 3 and 5 sessions, and momentum over 5, 10 and 20 sessions. A lag looks backward. Momentum measures change over a recent window; neither requires future prices.',
             'The six rolling inputs contain a return mean, sample standard deviation and close-to-moving-average distance, each calculated over 5 and 20 sessions. A moving average smooths recent values. The three daily-structure features describe different aspects of the current session and its opening gap.',
             'The final group contains 14-session RSI, 60-session drawdown, two weekday coordinates and two month coordinates. Sine and cosine represent repeating calendar cycles. The longest window requires 59 initial warm-up rows, and the final row has no available next-session target. Thus 3,644 complete sessions produce 3,584 labeled feature rows before two split-boundary removals.'
         ],
         point='Walk through the four group counts: 8, 6, 3 and 6, totaling 23. Then point to the current-close rule and seven-day calendar statement.',
         precision='Current-session OHLC is available only after its close. A future close can form a training target, but cannot become an input feature.',
         transition='After creating the features, we separated earlier learning periods from later evaluation periods.'),
    dict(title='We split the data by time', seconds=60,
         script='''We kept the observations in chronological order. Training uses 2,380 rows from 2012 through 2021 and teaches the models their parameters. Validation uses 493 rows in 2022 and 2023 to control stopping and choose the candidate. The final test uses 709 later rows from 2024 onward. We learn scaling settings from training only and apply them to the later periods. We also remove boundary rows when their next-session outcome reaches the following period. Three earlier historical checks provide additional evaluation within the training era. This process keeps later outcomes out of model fitting and selection. Shridhar will now explain the five frameworks and how we measured their performance.''',
         explanation=[
             'The exact feature-date ranges are 22 May 2012 to 30 December 2021 for training, 3 January 2022 to 28 December 2023 for validation, and 1 January 2024 to 8 November 2026 for test. The test outcomes extend through 9 November. Feature dates and target dates serve different purposes.',
             'StandardScaler learns each feature mean and standard deviation from the fitting block. Reusing those settings on later data avoids learning their distribution in advance. Boundary purging also ensures that a training outcome does not reach the first feature date of the next partition.',
             'The three expanding historical checks remain within the pre-2022 training era. Each scores 252 later sessions and uses a separate 126-session period for early stopping, with boundary gaps. They inspect sensitivity across earlier periods. The final validation period supports stopping and selection; it is therefore less independent than the test period.'
         ],
         point='Read the table across from training to validation to test. Explain the purpose of each column before discussing the row counts.',
         precision='The 2,380 plus 493 plus 709 rows total 3,582. The difference from 3,584 labeled rows is the two boundary removals.',
         transition='Handover to Shridhar for slide 7 and the modeling section.'),
    dict(title='We trained five frameworks', seconds=75,
         script='''We trained every framework requested in the brief. XGBoost builds small decision trees, adding trees to correct earlier prediction errors. Keras provides a readable way to define and train a neural network; here it uses its PyTorch backend. fastai provides a high-level learner that reduces training code. TabNet uses attention to select useful features during different processing steps. Lightning Flash organizes the neural network through a Task and Trainer. Keras, fastai and Flash use compact dense networks with hidden layers of 64 and 32 units. The five implementations all receive the same features, target and date partitions. We are comparing these actual configurations, rather than claiming that one framework is always best for every dataset. We also repeat each framework across the three earlier historical checks.''',
         explanation=[
             'A framework is software used to construct and train a model. A model is the mathematical system that learns a relationship between inputs and target. Keras, fastai and Flash are different training interfaces here, although their fitted dense network structures are similar. A hidden unit performs an intermediate calculation; the final output is one numerical return.',
             'XGBoost uses depth-2 trees, up to 160 rounds and learning rate 0.03. The dense networks use 64 and 32 ReLU units. TabNet uses three attentive steps with widths of 8. Deep models train for up to 40 epochs with early stopping. An epoch is one pass through the training data; early stopping restores the best monitored weights.',
             'Keras uses real Keras training on PyTorch. fastai uses its tabular learner. Flash uses its real Task and Trainer APIs with a custom regression network and pinned older dependencies. There are five final framework fits plus fifteen historical-check fits. These are compact comparisons with one seed, not an exhaustive tuning search.'
         ],
         point='Move down the five framework rows. Explain the model role of each, then connect the shared-input statement to a fair comparison.',
         precision='Three frameworks use similar dense networks. Different framework names do not imply five completely different model architectures.',
         transition='We measured every candidate with the same error measures and simple comparison baselines.'),
    dict(title='How we measured performance', seconds=60,
         script='''We used several measures because they describe different aspects of a forecast. RMSE gives greater weight to large errors, while MAE is the average absolute error. Lower values are better for both. Their unit is return percentage points. For example, if the actual return is one percent and the forecast is 0.2 percent, the absolute error is 0.8 percentage points. R-squared compares squared error with the variation in observed outcomes, and higher is better. Direction accuracy checks whether predicted and actual signs agree. We also compare against zero return, the training mean and Ridge regression. These simple baselines help establish whether additional model complexity provides useful forecasting value.''',
         explanation=[
             'For RMSE, calculate each forecast error, square it, average those squared errors and take the square root. For MAE, average the absolute errors. The squaring step makes RMSE more sensitive to occasional large mistakes.',
             'In the R-squared formula, SSE is the sum of squared prediction errors. SST is the sum of squared distances of actual outcomes from their evaluation-period mean. R-squared can be negative. That reference mean uses evaluation outcomes retrospectively, so it differs from a deployable training-mean baseline.',
             'Zero return predicts no change. Training mean predicts the fixed average return learned from training. Ridge is a regularized linear model. Direction is derived from the regression forecasts using return greater than zero; exact zero counts as nonpositive. Direction accuracy should be compared with the constant-direction baseline, especially when up and down observations are imbalanced.'
         ],
         equation='metrics',
         point='Explain the meaning and better direction of each metric. Then name the three baselines; do not read every formula aloud.',
         precision='An RMSE of 1.18 percentage points is an error measure. It is not 118 percent error or a classification accuracy.',
         transition='We used validation RMSE to choose the candidate before comparing the later test scores.'),
    dict(title='We chose the model on validation', seconds=45,
         script=f'''Our selection rule was to choose the candidate with the lowest validation RMSE, including the simple baselines. fastai had the lowest value at approximately {metric('fastai','RMSE','validation'):.4f} percentage points, so it became our selected model. We also tried an optional weighted blend of XGBoost and the best deep model. Validation selected zero percent XGBoost and one hundred percent fastai. Therefore, the blend produced the same predictions as fastai and added no gain. We fixed this choice before interpreting the later test scores.''',
         explanation=[
             'Validation is the development period used to compare choices. The table shows the five required framework scores in increasing RMSE order. The report also includes the baselines and optional blend. fastai is the selected candidate under the stated rule.',
             'The optional blend tests eleven XGBoost weights from zero through one. The remaining weight belongs to the deep component chosen using validation. A boundary weight is a legitimate outcome: zero XGBoost weight makes the blend identical to the deep model.',
             'Validation also helps determine when training stops, so its error may be optimistic after these choices. This is why a later test period is needed. Looking at test scores and changing the winner afterward would turn test data into another selection period.'
         ],
         point='Point to fastai at the top of the validation table, then to the zero/one-hundred blend statement below.',
         precision='The project selects fastai because of validation performance. It does not select it because it has the best score in every later test metric.',
         transition='We then evaluated the frozen candidates on the 709 later test observations.'),
    dict(title='Our results on 709 test sessions', seconds=75,
         script=f'''These are the results on the 709 later test sessions. The highlighted fastai row identifies the model selected using validation. Its test RMSE is {metric('fastai','RMSE'):.4f} percentage points and its MAE is {metric('fastai','MAE'):.4f}. Keras has the lowest test RMSE at {metric('keras','RMSE'):.4f}, TabNet has the lowest test MAE, and XGBoost has the highest recorded direction accuracy. These are different measures, so they can identify different strengths. We retain the earlier fastai selection instead of changing it after seeing the test. Most R-squared values are close to zero. Even Keras explains only about {100*metric('keras','R2'):.2f} percent of test variation under that metric. The results therefore show limited forecasting power, and the optional blend simply repeats the fastai row.''',
         explanation=[
             'Read lower RMSE and MAE as smaller forecasting errors, and higher R-squared and direction as better values. Compare frameworks on the same dates and target. The green highlight records the earlier selection decision; it is not a mark that fastai wins every test measure.',
             f"fastai direction accuracy is {metric('fastai','direction_accuracy'):.2%}, compared with {metric('training_mean','direction_accuracy'):.2%} for the training-mean predictor. A direction score should therefore be judged against a meaningful baseline. The zero-return sign is treated as nonpositive, which explains its different directional result.",
             'A low MAE does not guarantee low RMSE because RMSE penalizes large errors more strongly. Negative R-squared values remain valid. These test comparisons describe the fitted configurations and one time period; they do not establish a universal ranking of the five libraries.'
         ],
         table='test',
         point='First identify the highlighted fastai row. Then point to Keras RMSE, TabNet MAE and the simple baselines. Summarize patterns rather than reading every cell.',
         precision='Keep the distinction explicit: fastai was selected on validation; Keras achieved the lowest test RMSE.',
         transition='The next plot helps explain why the selected model captures little of the observed variation.'),
    dict(title='What our forecasts show', seconds=45,
         script='''This plot compares actual returns on the horizontal axis with predicted returns on the vertical axis. The diagonal line represents a perfect prediction. Our forecasts cluster near zero even when the actual return moves sharply. The observed standard deviation is about 1.181 percentage points, while the predicted standard deviation is only about 0.160. Therefore, the model predicts much less variation than the market actually shows. It misses the size of many large movements, which is consistent with the low R-squared result. Dhanraj will now explain model interpretation, the framework comparison and our conclusions.''',
         explanation=[
             'Each point represents one of the 709 evaluated observations. A point on the diagonal has equal actual and predicted returns. For example, an actual return of positive 3 percent would require a positive 3 percent forecast to lie on that line.',
             'The narrow band around the horizontal zero line shows small forecasts across a much wider range of actual returns. A forecast close to zero does not mean an index value close to zero: the output is a return, not the index level.',
             'The two displayed variations are sample standard deviations across test observations. Their difference describes forecast behaviour. It does not prove a single cause of the forecasting weakness or establish a formal uncertainty interval for each prediction.'
         ],
         point='Identify both axes and the perfect-prediction line, then trace the narrow band of predictions around zero.',
         precision='Use this chart to explain the limited fit. Do not claim that matching the direction of a few points establishes reliable forecasts.',
         transition='Handover to Dhanraj for slide 12 and the interpretation and conclusion section.'),
    dict(title='What influenced the XGBoost forecasts', seconds=75,
         script='''We also wanted to understand how a fitted model produced its predictions. We used TreeSHAP to explain the XGBoost forecasts. It separates a forecast into a baseline and contributions from the input features. The chart ranks features by their average absolute contribution on validation observations. Current return has the largest contribution, followed by earlier returns and other indicators. A longer bar means a larger average effect on this fitted model output. It does not tell us that the feature always pushes returns upward. These are explanations of XGBoost, although fastai is our selected model. They describe what the model used, and do not prove that a feature causes future market movements. Correlated inputs can also share explanatory credit. The horizontal axis measures return percentage points. A value near 0.0064 is a small average contribution to the model output, and it is not a prediction accuracy percentage.''',
         explanation=[
             'SHAP is an attribution method: it assigns portions of a model output to its inputs relative to a reference. TreeSHAP is the tree-model implementation used here. For an individual prediction, the baseline and feature contributions add to the model output.',
             'The displayed bars average the absolute contributions across validation rows. Taking absolute values removes direction. Thus a bar indicates typical contribution magnitude, not whether a feature consistently raises or lowers the forecast. Current return averages approximately 0.0064 percentage points in this XGBoost model.',
             'The project calculates explanations using trees through the best stopping iteration. A numerical additivity check verifies that contributions reconstruct the same predictions to rounding precision. Only XGBoost TreeSHAP was computed here; the chart is not an explanation of fastai or evidence that every framework received the same attribution analysis.'
         ],
         point='Start with the longest bar and explain the horizontal axis unit. Then emphasize the statement that these contributions explain a model rather than prove causes.',
         precision='Current return has the largest average absolute contribution in this fitted XGBoost analysis. That is not a universal claim about market causation.',
         transition='We compared forecasting errors alongside the practical simplicity and transparency of each framework.'),
    dict(title='Our comparison of the frameworks', seconds=75,
         script='''We compared the frameworks on three separate criteria. Simplicity concerns how easy the implementation is to build and read. Transparency concerns how forecasts can be inspected or explained. Efficacy concerns the actual measured forecasting errors. XGBoost has a short tabular workflow and supports the TreeSHAP explanation we calculated. Keras makes network layers readable, while fastai reduces the amount of training code. Their neural forecasts need additional explanation methods. TabNet provides feature masks, although it introduces more model settings. Flash required older pinned dependencies and extra setup. In the measured results, Keras had the lowest test RMSE, TabNet the lowest test MAE, and fastai was chosen on validation. These criteria should be discussed separately because ease of use does not automatically imply better forecasting accuracy.''',
         explanation=[
             'Simplicity is a practical assessment of these implementations, rather than a measured universal numeric score. Readable layers or fewer lines can make an implementation easier to maintain, while legacy dependency constraints can add setup work.',
             'Transparency concerns the connection between inputs and forecasts. Readable training code does not, by itself, explain an individual neural-network output. TabNet exposes attention masks; these are available explanation tools, not proof of economic causation. The calculated attribution results in this project are the XGBoost TreeSHAP values.',
             'Efficacy is judged from common validation/test dates, regression errors and supplementary direction results. No framework wins every dimension. The table refers to the configurations actually trained, not all architectures or hyperparameters that could be implemented in each library.'
         ],
         point='Explain the three comparison columns first. Then use examples from XGBoost, a dense-network framework, TabNet and Flash without rereading every row.',
         precision='Feature masks are available in TabNet, but this project does not claim that it calculated and analyzed TabNet masks alongside TreeSHAP.',
         transition='These comparisons lead to our overall conclusion about the forecasting task.'),
    dict(title='Our conclusion', seconds=60,
         script=f'''Our conclusion is that this index price history alone provides little reliable next-session forecasting power in the experiment. Validation selected fastai, but its test RMSE of {metric('fastai','RMSE'):.4f} percentage points was slightly worse than the zero-return baseline at {metric('zero_return','RMSE'):.4f}. Keras recorded the lowest test RMSE, while the optional blend added no gain. This remains a useful project finding because we compared all required frameworks and reported their outcomes honestly. The study covers one index, one later test period and one random seed. Useful next experiments would examine retraining over time and additional information available at each forecast date. These results do not establish a reliable trading advantage.''',
         explanation=[
             f"The selected model RMSE exceeds zero return by approximately {metric('fastai','RMSE')-metric('zero_return','RMSE'):.4f} percentage points. This is a very small difference, so describe the forecasting advantage as unestablished rather than claiming a dramatic failure. The selected R-squared is close to zero and negative.",
             'The completed assignment evaluates methods and their practical tradeoffs. A weak predictive result is still evidence about this problem and feature design. It should not be hidden by taking an absolute value of R-squared, changing the target after seeing the test, or choosing a new winner from test performance.',
             'Inputs contain the index OHLC history and known calendar values. They omit factors such as exchange rates, macroeconomic releases and news. Any added feature must have been available at the forecast time. More independent periods and repeated seeds would help assess stability; future improvement remains an experiment rather than a promise.'
         ],
         point='Compare fastai with zero return, then discuss the limitations and proposed next experiments below.',
         precision='The project is complete as a framework comparison. It does not establish that its selected model reliably outperforms simple return forecasts.',
         transition='We will show one historical prediction loaded from the saved model.'),
    dict(title='Our project demonstration', seconds=75,
         script='''This slide demonstrates one actual historical prediction using the saved fastai model. The information is available through 8 November 2026, and the outcome is observed on 9 November. fastai predicts a return of minus 0.2653 percent, while the actual return is minus 0.1339 percent. Both are negative, so this example gets the direction right. However, the predicted fall is larger than the observed fall, giving an absolute error of about 0.1314 percentage points. One example does not establish overall accuracy; that is why we evaluated all 709 test observations. The run-demo command loads the saved model and reproduces the historical prediction. The run-all command retrains the models and rebuilds the full project materials.''',
         explanation=[
             'The demonstration is a historical replay. It reconstructs the relevant features, loads the training scaler and saved checkpoint, and verifies agreement with the saved prediction. It does not refit the model or produce a new live-market forecast.',
             'The source includes a special Sunday session on 8 November, so the feature date is a valid observed session. The seven-day encoding keeps that date distinct. The numerical error is the absolute difference between the two displayed percentage returns; correctly predicting the sign does not imply predicting the magnitude accurately.',
             'Run .\\run_demo.ps1 in PowerShell from the prepared project folder. Adding -All displays all nine candidates. Run .\\run_all.ps1 to retrain and rebuild the notebook, reports, presentation and ZIP; this can take longer. If the environment is missing on another computer, setup is required. Full slide/report authoring uses the prepared runtime.'
         ],
         point='Show feature and outcome dates first, then compare forecast and actual return. Run the short demo if time allows; do not start full retraining during the presentation.',
         precision='This is a saved historical example. Present its correct direction alongside its magnitude error and the overall test results.',
         transition='The last slide identifies the sources and the project materials.'),
    dict(title='References and project materials', seconds=15,
         script='''These are our main data and method references. The report explains the methodology, the executed notebook shows the calculations, and the GitHub repository contains the code and project files. Thank you.''',
         explanation=[
             'NSE Indices supplies the historical index information and factsheet. The XGBoost and TabNet papers describe the respective model methods, and the SHAP paper describes the explanation method. The supplied course units are mapped to the project in the references folder.',
             'The Word/PDF report provides the detailed methodology and conclusions. The notebook contains executed calculations and graphs. The repository also retains original source responses, processed partitions, model checkpoints and saved predictions, so the results can be inspected.',
             'The repository is private in the prepared project. People who need to open it require appropriate GitHub access. Keep this final slide brief: the full method discussion belongs in the earlier slides and report.'
         ],
         point='Identify the references on the left and project materials on the right. Use the repository link when sharing the code.',
         precision='References support the data and methods; the reported Nifty Commodities metrics come from this project experiment.',
         transition='End the presentation after the closing sentence.')
]

TIMES = [(1, 6, 'Darshan Govekar', 'PES1UG24AM355'),
         (7, 11, 'Shridhar Umesh Golipalle', 'PES1UG25AM814'),
         (12, 16, 'Dhanraj Rathod', 'PES1UG24AM359')]
def owner(number):
    return next(name for first, last, name, _ in TIMES if first <= number <= last)

doc = Document()
section = doc.sections[0]
section.page_width = Inches(8.5)
section.page_height = Inches(11)
section.top_margin = Inches(.62)
section.bottom_margin = Inches(.62)
section.left_margin = Inches(.7)
section.right_margin = Inches(.7)
section.footer_distance = Inches(.25)
for name in ['Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2', 'Heading 3']:
    style = doc.styles[name]
    style.font.name = 'Arial'
    style.font.color.rgb = RGBColor(0, 0, 0)
    style.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), 'Arial')
for border in list(doc.styles.element.xpath('.//w:pBdr')):
    border.getparent().remove(border)
normal = doc.styles['Normal']
normal.font.size = Pt(11)
normal.paragraph_format.line_spacing = 1.06
normal.paragraph_format.space_after = Pt(5)
doc.styles['Title'].font.size = Pt(25)
doc.styles['Title'].paragraph_format.space_after = Pt(10)
doc.styles['Heading 1'].font.size = Pt(19)
doc.styles['Heading 1'].paragraph_format.space_after = Pt(6)
doc.styles['Heading 2'].font.size = Pt(11.5)
doc.styles['Heading 2'].font.bold = True
doc.styles['Heading 2'].paragraph_format.space_before = Pt(7)
doc.styles['Heading 2'].paragraph_format.space_after = Pt(3)
for name in ['Heading 1', 'Heading 2']:
    doc.styles[name].paragraph_format.keep_with_next = True
footer = section.footer.paragraphs[0]
footer.alignment = 2
footer.add_run('Team 12 presentation guide   |   ')
field = OxmlElement('w:fldSimple')
field.set(qn('w:instr'), 'PAGE')
footer._p.append(field)
for run in footer.runs:
    run.font.size = Pt(8)

def paragraph(text):
    return doc.add_paragraph(text)

def heading(text):
    return doc.add_paragraph(text, 'Heading 2')

def table(headers, rows, widths, highlight_rows=(), centered_columns=None):
    centered_columns = set(range(1,len(headers))) if centered_columns is None else set(centered_columns)
    t = doc.add_table(rows=1, cols=len(headers))
    t.autofit = False
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, value in enumerate(headers):
        t.rows[0].cells[j].text = str(value)
    for values in rows:
        for cell, value in zip(t.add_row().cells, values):
            cell.text = str(value)
    for j, width in enumerate(widths):
        t.columns[j].width = Inches(width)
    for i, row in enumerate(t.rows):
        trpr = row._tr.get_or_add_trPr()
        trpr.append(OxmlElement('w:cantSplit'))
        if i == 0:
            trpr.append(OxmlElement('w:tblHeader'))
        for j, cell in enumerate(row.cells):
            cell.width = Inches(widths[j])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            props = cell._tc.get_or_add_tcPr()
            shade = OxmlElement('w:shd')
            shade.set(qn('w:fill'), '173E52' if i == 0 else ('DDEFE8' if i in highlight_rows else ('F1F5F6' if i % 2 else 'FFFFFF')))
            props.append(shade)
            borders = OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right']:
                item = OxmlElement('w:' + edge)
                for key, value in [('val','single'),('sz','4'),('color','D9D9D9')]:
                    item.set(qn('w:' + key), value)
                borders.append(item)
            props.append(borders)
            margins = OxmlElement('w:tcMar')
            for edge in ['top','bottom','left','right']:
                item = OxmlElement('w:' + edge)
                item.set(qn('w:w'), '75')
                item.set(qn('w:type'), 'dxa')
                margins.append(item)
            props.append(margins)
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.line_spacing = 1
                if j in centered_columns:
                    p.alignment = 1
                for run in p.runs:
                    run.font.size = Pt(10)
                    run.bold = i == 0 or i in highlight_rows
                    run.font.color.rgb = RGBColor(255,255,255) if i == 0 else RGBColor(0,0,0)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return t

def math_run(text):
    run = OxmlElement('m:r')
    props = OxmlElement('m:rPr')
    props.append(OxmlElement('m:nor'))
    run.append(props)
    value = OxmlElement('m:t')
    value.set(qn('xml:space'), 'preserve')
    value.text = text
    run.append(value)
    return run

def fraction(numerator, denominator):
    f = OxmlElement('m:f')
    num = OxmlElement('m:num'); num.append(math_run(numerator))
    den = OxmlElement('m:den'); den.append(math_run(denominator))
    f.extend([num, den])
    return f

def squared(text):
    s = OxmlElement('m:sSup')
    base = OxmlElement('m:e'); base.append(math_run(text))
    power = OxmlElement('m:sup'); power.append(math_run('2'))
    s.extend([base, power])
    return s

def equation(parts):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(5)
    math = OxmlElement('m:oMath')
    for part in parts:
        math.append(math_run(part) if isinstance(part, str) else part)
    p._p.append(math)

presentation = Presentation(DECK)
assert len(presentation.slides) == len(SLIDES) == 16
for i, item in enumerate(SLIDES):
    actual = [s.text for s in presentation.slides[i].shapes if s.has_text_frame]
    assert item['title'] in actual, (i + 1, item['title'])
assert summary['selected_model'] == 'fastai'
assert blend['xgboost_weight'] == 0 and blend['deep_component'] == 'fastai'

doc.add_paragraph('Nifty Commodities Presentation Guide', 'Title')
doc.add_paragraph('Detailed slide explanations and speaking scripts', 'Subtitle')
paragraph('Team 12   |   Prepared 13 November 2026')
paragraph('This guide follows the current 16-slide presentation. It explains the concepts behind each slide and gives a natural script for presenting them. The central finding is limited next-session return predictability from this index history. fastai is the validation-selected model; Keras has the lowest later test RMSE.')
heading('Presenter assignments')
table(['Presenter','SRN','Slides','Target'],
      [[name,srn,f'{a} to {b}','5 minutes'] for a,b,name,srn in TIMES], [2.65,2.05,1.0,1.4])
heading('Using this guide')
paragraph('Read What this slide means to understand the material. Rehearse the What to say script in your own voice, with the slide open beside it. Use What to point to when discussing a chart or table. The transition links your explanation to the next slide or presenter.')
paragraph('The target is approximately 15 minutes overall. Each teammate has 5 minutes, with more time reserved for content-heavy slides. The detailed study notes are additional preparation, rather than extra material to read aloud. Adjust the pace after rehearsal instead of rushing through every number.')
heading('Presentation structure')
paragraph('Slides 1 and 2 introduce the project. Slides 3 to 9 explain the work, from data preparation through model selection. Slides 10 to 15 discuss results, interpretation, conclusions and the historical demonstration. Slide 16 identifies the sources and project materials.')
heading('Three distinctions to keep clear')
paragraph('A return is a percentage change in the index. A regression error is measured in percentage points. Direction accuracy is a separate sign diagnostic. Also distinguish validation selection from the lowest retrospective test error, and model explanations from evidence of market causation.')

counts = Counter()
for number, item in enumerate(SLIDES, 1):
    doc.add_page_break()
    doc.add_paragraph(f'Slide {number} {item["title"]}', 'Heading 1')
    meta = paragraph(f'Presenter: {owner(number)}   |   Suggested time: {item["seconds"]} seconds')
    for run in meta.runs:
        run.font.size = Pt(9.5)
    heading('What to say')
    paragraph(item['script'])
    counts[owner(number)] += len(re.findall(r"\b[\w]+(?:['-][\w]+)*\b", item['script']))
    heading('What this slide means')
    if item.get('table') == 'test':
        table(['Candidate','RMSE pp','MAE pp','R squared','Direction'],
              [[NAMES[r['model']],f"{float(r['RMSE']):.4f}",f"{float(r['MAE']):.4f}",
                f"{float(r['R2']):.4f}",f"{float(r['direction_accuracy']):.2%}"]
               for r in scores if r['split'] == 'test'], [2.0,1.25,1.25,1.2,1.4], highlight_rows=[6])
    for text in item['explanation']:
        paragraph(text)
    if item.get('equation') == 'return':
        equation(['Return (%) = ', fraction('Next close − Current close', 'Current close'), ' × 100'])
    if item.get('equation') == 'metrics':
        radical = OxmlElement('m:rad')
        props = OxmlElement('m:radPr')
        hide = OxmlElement('m:degHide'); hide.set(qn('m:val'),'1'); props.append(hide)
        radical.append(props)
        radical.append(OxmlElement('m:deg'))
        radicand = OxmlElement('m:e')
        radicand.append(math_run('mean(')); radicand.append(squared('(actual − forecast)')); radicand.append(math_run(')'))
        radical.append(radicand)
        equation(['RMSE = ', radical])
        equation(['MAE = mean(|actual − forecast|)'])
        equation([squared('R'), ' = 1 − ', fraction('SSE','SST')])
    heading('What to point to')
    paragraph(item['point'])
    heading('Key point to keep precise')
    paragraph(item['precision'])
    heading('Transition')
    paragraph(item['transition'])

doc.add_page_break()
doc.add_paragraph('Terms and presentation reminders', 'Heading 1')
table(['Term','Meaning in this project'], [
    ['OHLC','Open, high, low and close values for an observed trading session.'],
    ['Feature','A numerical input known at the forecast time.'],
    ['Target','The next observed session return that the model is trained to predict.'],
    ['Lag and momentum','A lag looks backward to an earlier observation; momentum measures change over a window.'],
    ['Volatility','The variability of returns, measured here using trailing sample standard deviation.'],
    ['RSI and drawdown','RSI compares upward/downward moves; drawdown describes distance below a recent high.'],
    ['Scaling','Transforming features using means and standard deviations learned from training only.'],
    ['Epoch and early stopping','An epoch is a pass through training data; early stopping restores the best monitored weights.'],
    ['Framework and model','A framework supplies software tools; a model is the fitted mathematical predictor.'],
    ['Baseline','A simple reference predictor used to judge whether added complexity helps.'],
    ['Percentage point','A difference between percentage returns, such as 1.0 percent minus 0.2 percent giving 0.8 pp.'],
    ['R squared','A signed comparison of squared forecast error with observed variation around the evaluation mean.'],
    ['TreeSHAP','A decomposition of a tree-model forecast into a baseline and feature contributions.'],
    ['Seed','A fixed random starting setting; one seed does not establish stability across all initializations.'],
], [1.65,5.45], centered_columns=[])
heading('Delivery reminders')
paragraph('State the question first, then describe the work and interpret the evidence. Explain the strongest patterns in a table instead of reading every cell. Keep index values, percent returns and percentage-point errors separate. The selected model is fastai; the lowest test RMSE belongs to Keras. The example is a historical replay, and the overall forecasting advantage is limited.')
heading('Source materials')
paragraph('The slide order, titles and chart cues follow deliverables/Team_12_Presentation.pptx. Numerical values use results/metrics.csv, results/run_summary.json and results/data_summary.json. Data preparation and feature definitions are implemented in src/pipeline.py; framework details are in src/model_adapters.py. Primary data and method references appear on slide 16 and in the project report.')

for a,b,name,_ in TIMES:
    assert sum(s['seconds'] for s in SLIDES[a-1:b]) == 300
assert max(counts.values()) / min(counts.values()) < 1.10, counts
doc.core_properties.title = 'Nifty Commodities Presentation Guide'
doc.core_properties.subject = 'Detailed slide explanations and balanced team speaking scripts'
doc.core_properties.author = 'Team 12'
OUT.parent.mkdir(exist_ok=True)
doc.save(OUT)
build = ROOT / '.build' / 'presentation_guide'
build.mkdir(parents=True, exist_ok=True)
(build / 'content_manifest.json').write_text(json.dumps({
    'source_deck_sha256':hashlib.sha256(DECK.read_bytes()).hexdigest(),
    'slides':16,'target_pages':18,'script_words_by_presenter':dict(counts),
    'target_seconds_by_presenter':{name:300 for _,_,name,_ in TIMES},
    'guide_path':str(OUT),
},indent=2),encoding='utf-8')
print(json.dumps({'file':str(OUT),'slides':16,'script_words_by_presenter':dict(counts)}))
