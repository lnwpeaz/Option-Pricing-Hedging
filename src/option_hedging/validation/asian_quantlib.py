"""Optional QuantLib comparator with explicit dated conventions and precision.

Choi's finest predeclared level is always the reference point. Cross-method
precision is empirical, never a guaranteed bound or a certificate of correctness.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
import importlib
import math
from time import perf_counter
import numpy as np
from option_hedging.pricing.asian_reference import arithmetic_bounds

FD_GRIDS=((100,100,80),(200,200,160),(400,400,320))
CHOI_LEVELS=(5,10,15)
MC_SEEDS=(9101,9102,9103,9104)
MC_PATHS=262144


@dataclass(frozen=True)
class ReferenceResult:
    price: float | None
    precision_radius: float | None
    precision_kind: str
    status: str
    diagnostics: tuple[str,...]=()


def _ql():
    return importlib.import_module('QuantLib')


def _date(ql,base_date):
    d=date.fromisoformat(base_date) if isinstance(base_date,str) else base_date
    return ql.Date(d.day,d.month,d.year)


def validate_fixing_dates(spec,base_date,dates):
    ql=_ql();base=_date(ql,base_date);dc=ql.Actual365Fixed()
    if len(dates)!=len(spec.fixing_times):raise ValueError('external fixing count mismatch')
    for actual,t in zip(dates,spec.fixing_times):
        if abs(dc.yearFraction(base,actual)-t)>1e-14:
            raise ValueError('external fixing dates do not match ACT/365F contract times')


def fixing_dates(spec,base_date):
    ql=_ql();base=_date(ql,base_date)
    offsets=[round(365*t) for t in spec.fixing_times]
    dates=[base+day for day in offsets]
    validate_fixing_dates(spec,base_date,dates)
    return dates


@contextmanager
def _evaluation_date(ql,base):
    old=ql.Settings.instance().evaluationDate
    try:
        ql.Settings.instance().evaluationDate=base
        yield
    finally:
        ql.Settings.instance().evaluationDate=old


def _process(ql,spec,base):
    dc=ql.Actual365Fixed()
    r=ql.YieldTermStructureHandle(ql.FlatForward(base,spec.risk_free_rate,dc))
    q=ql.YieldTermStructureHandle(ql.FlatForward(base,0.,dc))
    vol=ql.BlackVolTermStructureHandle(ql.BlackConstantVol(base,ql.NullCalendar(),spec.volatility,dc))
    return ql.BlackScholesMertonProcess(ql.QuoteHandle(ql.SimpleQuote(spec.spot)),q,r,vol)


def external_checks(spec, *, base_date, settings):
    """Retain all predeclared engine results, including failures and raw timings."""
    try:
        ql=_ql()
        if ql.__version__!=settings.get('quantlib_version','1.44'):
            raise ValueError(f'QuantLib version {ql.__version__} differs from requested pin')
        dates=fixing_dates(spec,base_date);base=_date(ql,base_date)
    except (ImportError,ValueError,OverflowError,RuntimeError) as exc:
        return [dict(engine='availability',level='',price=None,error_estimate=None,
                     elapsed_seconds=0.,status='unavailable',diagnostic=str(exc))]
    rows=[]
    with _evaluation_date(ql,base):
        process=_process(ql,spec,base)
        payoff=ql.PlainVanillaPayoff(ql.Option.Call if spec.kind=='call' else ql.Option.Put,spec.strike)
        exercise=ql.EuropeanExercise(dates[-1])
        if len(dates)==1:
            option=ql.VanillaOption(payoff,exercise)
            engines=[('analytic_single','exact',lambda:ql.AnalyticEuropeanEngine(process),False)]
        elif spec.averaging=='geometric':
            option=ql.DiscreteAveragingAsianOption(ql.Average.Geometric,1.,0,dates,payoff,exercise)
            engines=[('analytic_geometric','exact',lambda:ql.AnalyticDiscreteGeometricAveragePriceAsianEngine(process),False)]
        elif spec.volatility==0:
            avg=spec.spot*sum(math.exp(spec.risk_free_rate*t) for t in spec.fixing_times)/len(dates)
            value=math.exp(-spec.risk_free_rate*spec.maturity_years)*max((avg-spec.strike)*(1 if spec.kind=='call' else -1),0.)
            return [dict(engine='deterministic',level='exact',price=value,error_estimate=None,
                         elapsed_seconds=0.,status='completed',diagnostic='dated deterministic payoff')]
        else:
            option=ql.DiscreteAveragingAsianOption(ql.Average.Arithmetic,0.,0,dates,payoff,exercise)
            engines=[]
            for grid in FD_GRIDS:
                engines.append(('fd',','.join(map(str,grid)),lambda grid=grid:ql.FdBlackScholesAsianEngine(process,*grid),False))
            for level in CHOI_LEVELS:
                engines.append(('choi',str(level),lambda level=level:ql.ChoiAsianEngine(process,level,2**21),False))
            for seed in MC_SEEDS:
                engines.append(('mc_control',str(seed),lambda seed=seed:ql.MCDiscreteArithmeticAPEngine(
                    process,'pseudorandom',controlVariate=True,requiredSamples=MC_PATHS,seed=seed),True))
        for engine,level,factory,is_mc in engines:
            start=perf_counter()
            row=dict(engine=engine,level=level,price=None,error_estimate=None,status='failed',diagnostic='')
            try:
                option.setPricingEngine(factory());value=float(option.NPV())
                error=float(option.errorEstimate()) if is_mc else None
                if not math.isfinite(value) or (error is not None and (not math.isfinite(error) or error<0)):
                    raise ValueError('nonfinite external engine output')
                row.update(price=value,error_estimate=error,status='completed')
            except (RuntimeError,ValueError,OverflowError) as exc:row['diagnostic']=str(exc)
            row['elapsed_seconds']=perf_counter()-start;rows.append(row)
    return rows


def assess_reference(spec,checks, *, settings):
    completed=[r for r in checks if r['status']=='completed']
    exact=[r for r in completed if r['engine'].startswith('analytic') or r['engine']=='deterministic']
    if exact:return ReferenceResult(exact[-1]['price'],0.,'external_analytic','available')
    choi=[r for r in completed if r['engine']=='choi'];fd=[r for r in completed if r['engine']=='fd']
    if len(choi)!=3 or len(fd)!=3:
        return ReferenceResult(None,None,'unavailable','unavailable',tuple(r['diagnostic'] or 'incomplete external reference' for r in checks if r['status']!='completed'))
    point=choi[-1]['price']
    cd=abs(choi[-1]['price']-choi[-2]['price']);fdiff=abs(fd[-1]['price']-fd[-2]['price'])
    radius=max(2*cd,2*fdiff,abs(point-fd[-1]['price']))
    notes=[]
    if radius>settings.get('precision_target',.0005):notes.append('empirical_radius_exceeds_target')
    if cd>max(1e-10,1.05*abs(choi[-2]['price']-choi[-3]['price'])):notes.append('choi_nonconvergence')
    if fdiff>max(1e-10,1.05*abs(fd[-2]['price']-fd[-3]['price'])):notes.append('fd_nonconvergence')
    lo,hi=arithmetic_bounds(spec)
    if any(not lo-1e-10<=r['price']<=hi+1e-10 for r in completed):notes.append('external_price_outside_bounds')
    mc=[r for r in completed if r['engine']=='mc_control']
    if len(mc)!=4:notes.append('incomplete_mc_crosscheck')
    else:
        values=np.array([r['price'] for r in mc]);se=max(float(values.std(ddof=1)/2),
            math.sqrt(sum(r['error_estimate']**2 for r in mc))/4)
        if abs(float(values.mean())-point)>3*se+radius:notes.append('mc_crosscheck_disagreement')
    if any(r['status']!='completed' for r in checks):notes.append('external_engine_failure')
    return ReferenceResult(point,radius,'empirical_cross_method','low_precision' if notes else 'available',tuple(notes))


def reference_price(spec, *, base_date, settings):
    return assess_reference(spec,external_checks(spec,base_date=base_date,settings=settings),settings=settings)
