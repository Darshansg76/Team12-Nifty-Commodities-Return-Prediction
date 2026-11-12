"""Predict the next session's return using five required ML frameworks.

Read main() as six steps: load data, build past-only features, check earlier
periods, train the five models, select on validation, and evaluate on test.
Run from the project root: python src/pipeline.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import time

os.environ.setdefault('KERAS_BACKEND', 'torch')
os.environ.setdefault('MPLCONFIGDIR', str(Path(__file__).resolve().parents[1] / '.cache' / 'matplotlib'))
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.linear_model import Ridge
import joblib

ROOT = Path(__file__).resolve().parents[1]
FEATURE_COLUMNS = [
    'return_1', 'return_lag_1', 'return_lag_2', 'return_lag_3', 'return_lag_5',
    'momentum_5', 'momentum_10', 'momentum_20', 'volatility_5', 'volatility_20',
    'mean_return_5', 'mean_return_20', 'close_to_sma_5', 'close_to_sma_20',
    'intraday_return', 'range_pct', 'overnight_gap', 'rsi_14', 'drawdown_60',
    'weekday_sin', 'weekday_cos', 'month_sin', 'month_cos',
]
MODEL_NAMES = ['xgboost', 'keras', 'fastai', 'tabnet', 'flash']


def build_features(raw: pd.DataFrame) -> pd.DataFrame:
    """At close t, predict 100*(close[t+1]/close[t]-1), never a shuffled target."""
    d = raw.copy()
    d['Date'] = pd.to_datetime(d['Date'])
    d = d.sort_values('Date').reset_index(drop=True)
    if d.Date.duplicated().any():
        raise ValueError('Duplicate source dates')
    for col in ['Open', 'High', 'Low', 'Close']:
        d[col] = pd.to_numeric(d[col], errors='raise')
    if not np.isfinite(d[['Open','High','Low','Close']]).all().all():
        raise ValueError('Missing/nonfinite raw prices')
    if (d[['Open','High','Low','Close']] <= 0).any().any():
        raise ValueError('Nonpositive price')
    if ((d.High < d[['Open','Close','Low']].max(axis=1)) | (d.Low > d[['Open','Close','High']].min(axis=1))).any():
        raise ValueError('Inconsistent OHLC source values')
    c = d.Close
    r = c.pct_change(fill_method=None) * 100
    out = pd.DataFrame({'Date':d.Date, 'TargetDate':d.Date.shift(-1), 'Close':c})
    out['return_1'] = r
    for lag in [1,2,3,5]:
        out[f'return_lag_{lag}'] = r.shift(lag)
    for window in [5,10,20]:
        out[f'momentum_{window}'] = c.pct_change(window, fill_method=None) * 100
    for window in [5,20]:
        out[f'volatility_{window}'] = r.rolling(window).std()
        out[f'mean_return_{window}'] = r.rolling(window).mean()
        out[f'close_to_sma_{window}'] = (c / c.rolling(window).mean() - 1) * 100
    out['intraday_return'] = (c / d.Open - 1) * 100
    out['range_pct'] = (d.High - d.Low) / c * 100
    out['overnight_gap'] = (d.Open / c.shift(1) - 1) * 100
    delta = c.diff()
    up = delta.clip(lower=0).rolling(14).mean()
    down = (-delta.clip(upper=0)).rolling(14).mean()
    out['rsi_14'] = 100 - 100 / (1 + up / down.replace(0, np.nan))
    out.loc[(down == 0) & (up > 0), 'rsi_14'] = 100
    out.loc[(down == 0) & (up == 0), 'rsi_14'] = 50
    out['drawdown_60'] = (c / c.rolling(60).max() - 1) * 100
    # Use all seven calendar days: NSE occasionally holds weekend sessions.
    # A five-day cycle would incorrectly make Saturday equal Monday.
    out['weekday_sin'] = np.sin(2*np.pi*d.Date.dt.dayofweek/7)
    out['weekday_cos'] = np.cos(2*np.pi*d.Date.dt.dayofweek/7)
    out['month_sin'] = np.sin(2*np.pi*(d.Date.dt.month-1)/12)
    out['month_cos'] = np.cos(2*np.pi*(d.Date.dt.month-1)/12)
    out['target_return'] = r.shift(-1)
    return out.replace([np.inf,-np.inf],np.nan).dropna(subset=FEATURE_COLUMNS+['target_return','TargetDate']).reset_index(drop=True)


def split_dataset(frame):
    """Keep time order and remove outcomes that reach the next period."""
    train = frame.loc[frame.Date <= '2021-12-31'].copy()
    val = frame.loc[(frame.Date > '2021-12-31') & (frame.Date <= '2023-12-31')].copy()
    test = frame.loc[frame.Date > '2023-12-31'].copy()
    if any(len(x) == 0 for x in [train,val,test]):
        raise ValueError('Need historical data covering train, validation and test date ranges')
    train = train.loc[train.TargetDate < val.Date.min()].copy()
    val = val.loc[val.TargetDate < test.Date.min()].copy()
    assert train.TargetDate.max() < val.Date.min()
    assert val.TargetDate.max() < test.Date.min()
    return train, val, test


def make_arrays(train, val, test):
    """Learn feature scaling on training data and reuse it for later dates."""
    scaler = StandardScaler().fit(train[FEATURE_COLUMNS])
    ans = {'scaler':scaler}
    for label, part in [('train',train),('val',val),('test',test)]:
        ans['X_'+label] = scaler.transform(part[FEATURE_COLUMNS]).astype('float32')
        ans['y_'+label] = part.target_return.to_numpy(dtype='float32')
    return ans


def metrics(y, pred):
    """Return errors in percentage points, signed R2 and sign accuracy."""
    y,pred = np.asarray(y,dtype=float),np.asarray(pred,dtype=float).ravel()
    return {'RMSE':float(np.sqrt(mean_squared_error(y,pred))),
            'MAE':float(mean_absolute_error(y,pred)), 'R2':float(r2_score(y,pred)),
            'direction_accuracy':float(np.mean((y>0)==(pred>0))),
            'bias':float(np.mean(pred-y)), 'n':len(y)}


def dump(path, obj):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(obj,indent=2,default=str),encoding='utf-8')


def plot_results(raw, frame, train, val, test, pred, scores, summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140})
    out=ROOT/'results'/'figures'; out.mkdir(parents=True,exist_ok=True)
    def save(name):
        plt.tight_layout(); plt.savefig(out/name,bbox_inches='tight'); plt.close()
    fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
    axes[0].plot(raw.Date,raw.Close,color='#123D55',lw=1)
    axes[0].set(ylabel='Price index points',title='Nifty Commodities price index and daily returns')
    axes[1].plot(frame.Date,frame.return_1,color='#168F88',lw=.5)
    axes[1].set(ylabel='Daily return (%)',xlabel='Date')
    for ax in axes:
        ax.axvline(pd.Timestamp('2022-01-01'),color='#B85B28',ls='--',lw=1)
        ax.axvline(pd.Timestamp('2024-01-01'),color='#B85B28',ls='--',lw=1)
    save('01_history.png')
    fig,axes=plt.subplots(1,2,figsize=(10,3.7))
    axes[0].hist(train.target_return,bins=65,color='#123D55',alpha=.85)
    axes[0].set(xlabel='Next session return (%)',ylabel='Training observations',title='Training return distribution')
    axes[1].plot(train.Date,train.volatility_20,color='#168F88',lw=.8)
    axes[1].set(xlabel='Date',ylabel='20-session volatility (pp)',title='Volatility changes over time')
    save('02_eda.png')
    corr=train[FEATURE_COLUMNS+['target_return']].corr()
    fig,ax=plt.subplots(figsize=(10,8)); im=ax.imshow(corr,cmap='RdBu_r',vmin=-1,vmax=1)
    ax.set_xticks(range(len(corr)),corr.columns,rotation=90,fontsize=7); ax.set_yticks(range(len(corr)),corr.columns,fontsize=7)
    fig.colorbar(im,ax=ax,shrink=.75,label='Training Pearson correlation'); save('03_correlation.png')
    order=scores.loc[scores.split=='test'].sort_values('RMSE')
    fig,ax=plt.subplots(figsize=(9,4)); ax.barh(order.model,order.RMSE,color=['#168F88' if n==summary['selected_model'] else '#123D55' for n in order.model])
    ax.invert_yaxis(); ax.set(xlabel='Test RMSE (percentage points)',title='Frozen test comparison'); save('04_model_comparison.png')
    chosen=summary['selected_model']
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    axes[0].scatter(test.target_return,pred[chosen],s=8,alpha=.35,color='#123D55')
    lo,hi=float(test.target_return.min()),float(test.target_return.max()); axes[0].plot([lo,hi],[lo,hi],ls='--',color='#B85B28')
    axes[0].set(xlabel='Observed return (%)',ylabel='Predicted return (%)',title=f'Validation-selected model: {chosen}')
    axes[1].hist(test.target_return.to_numpy()-pred[chosen],bins=45,color='#168F88')
    axes[1].set(xlabel='Residual (percentage points)',ylabel='Test observations',title='Test residuals'); save('05_diagnostics.png')
    annual=[]
    for year,part in test.groupby(test.Date.dt.year):
        idx=test.index.get_indexer(part.index)
        annual.append({'year':int(year),**metrics(part.target_return,pred[chosen][idx])})
    pd.DataFrame(annual).to_csv(ROOT/'results'/'annual_test_metrics.csv',index=False)
    if (ROOT/'results'/'xgboost_shap_importance.csv').exists():
        imp=pd.read_csv(ROOT/'results'/'xgboost_shap_importance.csv')
        imp=imp.loc[imp.mean_abs_shap > 0].head(6).iloc[::-1]
        fig,ax=plt.subplots(figsize=(9,4)); ax.barh(imp.feature,imp.mean_abs_shap,color='#123D55')
        ax.set(xlabel='Mean absolute TreeSHAP contribution (pp)',title='XGBoost explanations on validation data'); save('06_explanations.png')


def main(skip_cv=False):
    from model_adapters import fit_predict
    start=time.perf_counter()
    results=ROOT/'results'; results.mkdir(exist_ok=True)
    # 1. Load the included official snapshot; downloading is a separate choice.
    rawpath=ROOT/'data'/'raw'/'nifty_commodities_complete_ohlc.csv'
    raw=pd.read_csv(rawpath).rename(columns=str.title)
    raw['Date']=pd.to_datetime(raw['Date'])
    raw=raw.loc[raw.Date <= '2026-11-10'].sort_values('Date').reset_index(drop=True)
    full_source=pd.read_csv(ROOT/'data'/'raw'/'nifty_commodities_daily.csv')
    # 2. Make 23 features and chronological train / validation / test periods.
    frame=build_features(raw); train,val,test=split_dataset(frame)
    (ROOT/'data'/'processed').mkdir(exist_ok=True)
    frame.to_csv(ROOT/'data'/'processed'/'features.csv',index=False)
    for label,part in [('train',train),('validation',val),('test',test)]:
        part.to_csv(ROOT/'data'/'processed'/f'{label}.csv',index=False)
    dump(results/'data_summary.json',{
        'raw_rows':len(raw),'raw_start':raw.Date.min(),'raw_end':raw.Date.max(),
        'full_source_rows':len(full_source),'initial_rows_excluded_missing_ohlc':len(full_source)-len(raw),
        'missing_policy':'Exclude contiguous initial missing-OHL era through 2012-02-24; no interior sessions removed or prices imputed.',
        'raw_sha256':hashlib.sha256(rawpath.read_bytes()).hexdigest(),
        'feature_count':len(FEATURE_COLUMNS),'feature_rows':len(frame),
        'partitions':{label:{'rows':len(p),'feature_start':p.Date.min(),'feature_end':p.Date.max(),'target_end':p.TargetDate.max()} for label,p in [('train',train),('validation',val),('test',test)]},
        'target':'100 * (Close[next observed trading session] / Close[t] - 1)',
        'forecast_time':'After the official close of feature date t',
        'missing_ohlc':int(raw[['Open','High','Low','Close']].isna().sum().sum()),
        'duplicate_dates':int(raw.Date.duplicated().sum()),
        'training_target_statistics':train.target_return.describe().to_dict(),
        'training_target_skew':train.target_return.skew(),
        'training_target_excess_kurtosis':train.target_return.kurt(),
        'training_up_fraction':float((train.target_return>0).mean()),
        'calendar_encoding':{'weekday_cycle_days':7,'month_cycle_months':12,
                             'weekend_source_sessions':int((raw.Date.dt.dayofweek >= 5).sum())},
    })
    a=make_arrays(train,val,test); joblib.dump(a['scaler'],ROOT/'models'/'scaler.joblib')
    dump(ROOT/'models'/'features.json',FEATURE_COLUMNS)
    # 3. Check all frameworks on the same three earlier historical periods.
    cvrows=[]
    configs={'xgboost':{'max_depth':2,'n_estimators':160,'learning_rate':.03}}
    if not skip_cv:
        for fold,(it,iv) in enumerate(TimeSeriesSplit(n_splits=3,gap=1,test_size=252).split(train),1):
            ft,fv=train.iloc[it],train.iloc[iv]
            # Last 126 training sessions monitor stopping; outer 252 never do.
            inner_stop=ft.iloc[-126:]
            inner_train=ft.iloc[:-127]
            assert inner_train.TargetDate.max() < inner_stop.Date.min()
            assert inner_stop.TargetDate.max() < fv.Date.min()
            fa=make_arrays(inner_train,inner_stop,fv)
            for name in MODEL_NAMES:
                output=ROOT/'models'/'cv'/f'fold_{fold}'/name; output.mkdir(parents=True,exist_ok=True)
                print(f'CV fold {fold}: {name}',flush=True)
                _,vp,meta=fit_predict(name,fa['X_train'],fa['y_train'],fa['X_val'],fa['y_val'],fa['X_test'],seed=42,output_dir=output,config=configs.get(name))
                np.savez(output/'predictions.npz',validation=vp)
                dump(output/'metadata.json',meta)
                cvrows.append({'fold':fold,'model':name,'train_n':len(inner_train),'early_stopping_n':len(inner_stop),'validation_n':len(fv),'train_end':str(inner_train.Date.max().date()),'validation_start':str(fv.Date.min().date()),**metrics(fa['y_test'],vp)})
        cv=pd.DataFrame(cvrows); cv.to_csv(results/'cv_metrics.csv',index=False)
        cv.groupby('model')[['RMSE','MAE','R2','direction_accuracy']].agg(['mean','std']).to_csv(results/'cv_summary.csv')
    # 4. Fit simple baselines, then each of the five required frameworks.
    vp={};tp={};metas={};rows=[]
    for name,constant in [('zero_return',0.),('training_mean',float(a['y_train'].mean()))]:
        vp[name]=np.full(len(val),constant);tp[name]=np.full(len(test),constant)
    ridge=Ridge(alpha=100).fit(a['X_train'],a['y_train'])
    vp['ridge']=ridge.predict(a['X_val']);tp['ridge']=ridge.predict(a['X_test'])
    joblib.dump(ridge,ROOT/'models'/'ridge.joblib')
    for name in MODEL_NAMES:
        output=ROOT/'models'/name;output.mkdir(exist_ok=True)
        print('Final development fit: '+name,flush=True)
        vp[name],tp[name],metas[name]=fit_predict(name,a['X_train'],a['y_train'],a['X_val'],a['y_val'],a['X_test'],seed=42,output_dir=output,config=configs.get(name))
        np.savez(output/'predictions.npz',validation=vp[name],test=tp[name])
        dump(output/'metadata.json',metas[name])
    # 5. Optional extension: try a weighted average using validation only.
    best_deep=min(['keras','fastai','tabnet','flash'],key=lambda n:metrics(a['y_val'],vp[n])['RMSE'])
    grid=[]
    for weight in np.linspace(0,1,11):
        p=weight*vp['xgboost']+(1-weight)*vp[best_deep]
        grid.append({'xgboost_weight':float(weight),'RMSE':metrics(a['y_val'],p)['RMSE']})
    weight=min(grid,key=lambda r:r['RMSE'])['xgboost_weight']
    vp['blend']=weight*vp['xgboost']+(1-weight)*vp[best_deep]
    tp['blend']=weight*tp['xgboost']+(1-weight)*tp[best_deep]
    dump(results/'blend_selection.json',{'deep_component':best_deep,'xgboost_weight':weight,'grid':grid,'selection_data':'validation only; no test optimization'})
    # 6. Choose by validation RMSE first, then report every test result.
    selected=min(vp,key=lambda n:metrics(a['y_val'],vp[n])['RMSE'])
    for name in vp:
        rows.append({'model':name,'split':'validation',**metrics(a['y_val'],vp[name])})
        rows.append({'model':name,'split':'test',**metrics(a['y_test'],tp[name])})
    scores=pd.DataFrame(rows);scores.to_csv(results/'metrics.csv',index=False)
    for label,part,pr in [('validation',val,vp),('test',test,tp)]:
        p=part[['Date','TargetDate','Close','target_return']].reset_index(drop=True)
        for n in pr:p[n]=pr[n]
        p.to_csv(results/f'{label}_predictions.csv',index=False)
    # TreeSHAP is supplied natively by XGBoost; no approximation package needed.
    try:
        import xgboost as xgb
        modelpath=ROOT/'models'/'xgboost'/'xgboost.ubj'
        if not modelpath.exists():
            modelpath=next((ROOT/'models'/'xgboost').glob('*.json'))
        booster=xgb.Booster();booster.load_model(modelpath)
        best_iteration=int(booster.attr('best_iteration'))+1 if booster.attr('best_iteration') is not None else 0
        contributions=booster.predict(xgb.DMatrix(a['X_val']),pred_contribs=True,iteration_range=(0,best_iteration))
        pd.DataFrame({'feature':FEATURE_COLUMNS,'mean_abs_shap':np.abs(contributions[:,:-1]).mean(axis=0)}).sort_values('mean_abs_shap',ascending=False).to_csv(results/'xgboost_shap_importance.csv',index=False)
        dump(results/'shap_check.json',{'max_additivity_error':float(np.max(np.abs(contributions.sum(axis=1)-vp['xgboost']))),'explained_partition':'validation','method':'XGBoost native TreeSHAP pred_contribs=True','bias_mean':float(contributions[:,-1].mean())})
    except Exception as exc:
        dump(results/'shap_error.json',{'error':str(exc)})
    summary={'selected_model':selected,'selection_rule':'lowest validation RMSE including baselines',
             'selected_validation':metrics(a['y_val'],vp[selected]),'selected_test':metrics(a['y_test'],tp[selected]),
             'best_test_model_descriptive_only':scores[scores.split=='test'].sort_values('RMSE').iloc[0].model,
             'blend_deep_component':best_deep,'blend_xgboost_weight':weight,
             'elapsed_seconds':time.perf_counter()-start,'seed':42,'python':platform.python_version(),
             'models':metas,'cv_skipped':skip_cv,
             'limits':['One index and one held-out era. Daily returns are noisy.',
                       'Validation supports early stopping and blend selection, so validation scores are optimistic.',
                       'No investment performance or executable trading profits are claimed.',
                       'Data are a price index, excluding dividend reinvestment.']}
    dump(results/'run_summary.json',summary)
    plot_results(raw,frame,train,val,test,tp,scores,summary)
    print(scores.to_string(index=False),flush=True)
    print('Validation-selected model: '+selected,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--skip-cv',action='store_true')
    args=parser.parse_args()
    (ROOT/'models').mkdir(exist_ok=True)
    main(args.skip_cv)
