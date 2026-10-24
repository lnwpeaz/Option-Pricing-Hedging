"""Reference-aware macro-repeat metrics with shared-ID paired bootstrap.

Bootstrap key=[81,contract index,N,seed]. All methods share resampled requested
macro IDs, including explicit missing/failed outcomes. Conditional RMSE ranges
assume the empirical reference band contains truth; they are not confidence bounds.
"""
import math
import numpy as np
import pandas as pd


def coverage_flags(low,high,point,radius):
    return (bool(low<=point+radius and high>=point-radius),
            bool(low<=point-radius and high>=point+radius))


def _quantiles(values):
    values=np.asarray(values);values=values[np.isfinite(values)]
    return tuple(float(x) for x in np.quantile(values,[.025,.975])) if len(values) else (None,None)


def _mean(values):
    scale=float(np.max(np.abs(values))) if len(values) else 0.
    if not scale:return 0.
    normalized=math.fsum(float(x) for x in values/scale)/len(values)
    result=normalized*scale
    if not math.isfinite(result) or (normalized!=0 and result==0):
        raise FloatingPointError('aggregate mean outside numeric range')
    return result


def _sd(values):
    scale=float(np.max(np.abs(values)))
    if not scale:return 0.
    normalized=float(np.std(values/scale,ddof=1));result=normalized*scale
    if not math.isfinite(result) or (normalized>0 and result==0) or (result==0 and np.any(values!=values[0])):
        raise FloatingPointError('aggregate dispersion outside numeric range')
    return result


def _rmse(values):
    scale=float(np.max(np.abs(values))) if len(values) else 0.
    return scale*math.sqrt(float(np.mean((values/scale)**2))) if scale else 0.


def _boot(values,indices,*,squared=False,sd=False):
    scale=np.nanmax(np.abs(values)) if np.any(np.isfinite(values)) else 0.
    normalized=values/(scale if scale else 1.)
    x=normalized[indices];ok=np.isfinite(x);n=ok.sum(axis=1);clean=np.where(ok,x,0.)
    means=np.divide(clean.sum(axis=1),n,out=np.full(len(n),np.nan),where=n>0)
    if squared:
        means=np.sqrt(np.divide((clean**2).sum(axis=1),n,out=np.full(len(n),np.nan),where=n>0))
    if sd:
        centered=np.where(ok,x-means[:,None],0.)
        means=np.sqrt(np.divide((centered**2).sum(axis=1),n-1,out=np.full(len(n),np.nan),where=n>1))
    return means*scale


def _wilson(successes,n):
    if not n:return None,None
    z=1.959963984540054;p=successes/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return center-half,center+half


def _work_product(rmse,work):
    if rmse is None:return None
    if rmse==0:return 0.
    logv=2*math.log(rmse)+math.log(work) if work>0 else -math.inf
    return math.exp(logv) if -745<logv<709 else (0. if work==0 else None)


def summarize(estimates,references,*,bootstrap_repeats,seed):
    metrics=[];paired=[];refs=references.set_index('contract_id')
    for (cid,budget),group in estimates.groupby(['contract_id','n_paths'],sort=False):
        reference=refs.loc[cid];valid_ref=reference['status'] in ('available','low_precision') and pd.notna(reference['price'])
        point=float(reference['price']) if valid_ref else None
        radius=float(reference['precision_radius']) if valid_ref and pd.notna(reference['precision_radius']) else None
        exact=bool(reference['is_exact']) and valid_ref
        ids=sorted(group['macro_repeat'].unique());id_map={x:i for i,x in enumerate(ids)}
        rng=np.random.default_rng(np.random.SeedSequence([81,int(cid[1:]),int(budget),seed]))
        indices=rng.integers(0,len(ids),size=(bootstrap_repeats,len(ids)))
        arrays={};errors={};boot_errors={};eligible={}
        for method,rows in group.groupby('method',sort=False):
            good=rows[rows['status'].isin(['sampled','deterministic'])]
            values=np.full(len(ids),np.nan)
            for row in good.itertuples():values[id_map[row.macro_repeat]]=row.price
            arrays[method]=values
            sample=values[np.isfinite(values)];n=len(sample)
            error=values-point if valid_ref else np.full(len(ids),np.nan);errors[method]=error
            rmse=_rmse(sample-point) if valid_ref and n else None
            dominates=(radius is None or reference['status']!='available' or rmse is None or radius>.1*rmse)
            eligible[method]=not dominates and len(good)==len(rows)
            row=dict(contract_id=cid,n_paths=int(budget),method=method,requested_count=len(rows),completed_count=n,
                failed_count=len(rows)-n,reference_status=reference['status'],reference_kind=reference['precision_kind'],
                reference_price=point,reference_radius=radius,reference_dominates_error=dominates,rank_eligible=eligible[method],
                bias=_mean(sample-point) if valid_ref and n else None,rmse=rmse,
                empirical_sd=_sd(sample) if n>1 else None,
                mean_reported_se=_mean(good['standard_error'].to_numpy()) if n else None,
                zero_se_count=int((good['standard_error']==0).sum()),
                conditional_rmse_low=max(0.,rmse-radius) if rmse is not None and radius is not None else None,
                conditional_rmse_high=rmse+radius if rmse is not None and radius is not None else None)
            boot_errors[method]=_boot(error,indices,squared=True)
            row['bootstrap_rmse_low'],row['bootstrap_rmse_high']=_quantiles(boot_errors[method])
            row['bootstrap_bias_low'],row['bootstrap_bias_high']=_quantiles(_boot(error,indices))
            row['bootstrap_sd_low'],row['bootstrap_sd_high']=_quantiles(_boot(values,indices,sd=True))
            flags=[]
            if valid_ref and radius is not None:
                flags=[coverage_flags(r.ci_low,r.ci_high,point,radius) for r in good.itertuples()]
            possible=np.full(len(ids),np.nan);definite=possible.copy()
            for (r,flag) in zip(good.itertuples(),flags):possible[id_map[r.macro_repeat]],definite[id_map[r.macro_repeat]]=flag
            row['possible_coverage']=float(np.mean([f[0] for f in flags])) if flags else None
            row['definite_coverage']=float(np.mean([f[1] for f in flags])) if flags else None
            for name,vals in [('possible',possible),('definite',definite)]:
                row[f'{name}_coverage_ci_low'],row[f'{name}_coverage_ci_high']=_quantiles(_boot(vals,indices))
            row['coverage_exact']=row['possible_coverage'] if exact else None
            row['coverage_wilson_low'],row['coverage_wilson_high']=_wilson(sum(f[0] for f in flags),n) if exact else (None,None)
            for field in ['production_paths','pilot_paths','payoff_evaluations','control_payoff_evaluations','normal_coordinates']:
                row[field+'_mean']=float(good[field].mean()) if n else None
            work=(row['payoff_evaluations_mean'] or 0)+(row['control_payoff_evaluations_mean'] or 0)
            row['rmse_squared_times_production_paths']=_work_product(rmse,row['production_paths_mean'] or 0)
            row['rmse_squared_times_total_payoffs']=_work_product(rmse,work)
            metrics.append(row)
        pairs=[('sobol_bridge','sobol')]
        pairs += [(method,'plain') for method in arrays if method!='plain']
        for a,b in pairs:
            if a not in arrays or b not in arrays:continue
            both=np.isfinite(arrays[a])&np.isfinite(arrays[b]);count=int(both.sum())
            diff=np.where(both,arrays[a]-arrays[b],np.nan)
            low,high=_quantiles(_boot(diff,indices))
            ea=np.where(both,errors[a],np.nan);eb=np.where(both,errors[b],np.nan)
            ra=_rmse(ea[both]) if valid_ref and count else None
            rb=_rmse(eb[both]) if valid_ref and count else None
            ba=_boot(ea,indices,squared=True);bb=_boot(eb,indices,squared=True)
            ratio_boot=np.divide(ba,bb,out=np.full_like(ba,np.nan),where=bb>0)
            rlo,rhi=_quantiles(ratio_boot);dlo,dhi=_quantiles(ba-bb)
            paired.append(dict(contract_id=cid,n_paths=int(budget),method_a=a,method_b=b,paired_repeats=count,
                mean_price_difference=_mean(diff[both]) if count else None,difference_ci_low=low,difference_ci_high=high,
                rmse_ratio=ra/rb if rb and ra is not None else None,rmse_ratio_ci_low=rlo,rmse_ratio_ci_high=rhi,
                rmse_difference=ra-rb if ra is not None and rb is not None else None,
                rmse_difference_ci_low=dlo,rmse_difference_ci_high=dhi,
                undefined_ratio_bootstraps=int((~np.isfinite(ratio_boot)).sum()),
                rank_eligible=eligible[a] and eligible[b]))
    return pd.DataFrame(metrics),pd.DataFrame(paired)
