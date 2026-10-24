"""Discrete Asian Monte Carlo with explicit independent units and work counts."""
from numbers import Integral
import numpy as np
from option_hedging.asian_contracts import AsianOptionSpec, AsianEstimate
from option_hedging.pricing.asian_reference import geometric_price, deterministic_price
from option_hedging.pricing.asian_samples import discounted_payoffs, target_payoffs
from option_hedging.pricing._asian_statistics import ScaledMoments,currency,interval

METHODS=('plain','antithetic','control','sobol','sobol_bridge')
Z_95=1.959963984540054


def integer(name,value,minimum,maximum=None):
    if isinstance(value,(bool,np.bool_)) or not isinstance(value,Integral):
        raise TypeError(f'{name} must be an integer')
    if value<minimum or (maximum is not None and value>maximum):
        raise ValueError(f'{name} outside allowed range')
    return int(value)


def price(spec: AsianOptionSpec, *, n_paths: int, rng: np.random.Generator,
          method: str='plain', batch_size: int=1024, pilot_paths: int=512,
          scrambles: int=16, bits: int=52) -> AsianEstimate:
    """Approximate 95% interval; zero sample SE is not an exact-price assertion.

    Pilot paths are extra work. Antithetic SE uses pair means. Input settings
    remain validated in the deterministic limit, which does not consume RNG.
    """
    if not isinstance(spec,AsianOptionSpec):raise TypeError('spec must be AsianOptionSpec')
    n_paths=integer('n_paths',n_paths,2);batch_size=integer('batch_size',batch_size,2)
    pilot_paths=integer('pilot_paths',pilot_paths,2)
    scrambles=integer('scrambles',scrambles,2);bits=integer('bits',bits,1,52)
    if not isinstance(rng,np.random.Generator):raise TypeError('rng must be numpy Generator')
    if method not in METHODS:raise ValueError(f'unknown method: {method}')
    if method=='antithetic' and (n_paths<4 or n_paths%2):raise ValueError('antithetic requires even N>=4')
    if method=='control' and spec.averaging!='arithmetic':raise ValueError('control requires arithmetic averaging')
    if method in ('sobol','sobol_bridge'):
        if n_paths%scrambles:
            raise ValueError('QMC N must be divisible by R')
        per=n_paths//scrambles
        if per<1 or per&(per-1) or per>2**bits:
            raise ValueError('QMC N/R must be a power of two <= 2**bits')
    if spec.volatility==0:
        value=deterministic_price(spec)
        return AsianEstimate(value,0.,value,value,method,'deterministic',n_paths,0,0,0,0,0,0,0)
    if method in ('sobol','sobol_bridge'):
        from option_hedging.pricing.asian_rqmc import price_qmc
        return price_qmc(spec,n_paths=n_paths,rng=rng,method=method,batch_size=batch_size,
                         scrambles=scrambles,bits=bits)
    beta=None; diagnostics=[];m=len(spec.fixing_times)
    expectation=None
    if method=='control':
        pilot=ScaledMoments()
        for start in range(0,pilot_paths,batch_size):
            z=rng.standard_normal((min(batch_size,pilot_paths-start),m))
            y,x=discounted_payoffs(spec,z)
            pilot.update(np.column_stack((y,x)))
        beta=pilot.beta
        if pilot.m2[1,1]==0:diagnostics.append('zero_pilot_control_variance')
        g=geometric_price(spec);expectation=g/spec.spot
        if g>0 and expectation==0:raise FloatingPointError('control expectation underflow')
    units=n_paths//2 if method=='antithetic' else n_paths
    unit_batch=max(1,batch_size//2) if method=='antithetic' else batch_size
    moments=ScaledMoments()
    with np.errstate(over='raise',invalid='raise',divide='raise',under='ignore'):
        for start in range(0,units,unit_batch):
            z=rng.standard_normal((min(unit_batch,units-start),m))
            if method=='control':
                y,x=discounted_payoffs(spec,z)
                observations=y-beta*(x-expectation)
            else:
                observations=target_payoffs(spec,z)
                if method=='antithetic':observations=.5*observations+.5*target_payoffs(spec,-z)
            moments.update(observations)
    mean=currency(moments.mean_value,spec.spot);se=currency(moments.standard_error,spec.spot)
    low,high=interval(mean,se,Z_95)
    if se==0:diagnostics.append('zero_observed_variance')
    pilot_n=pilot_paths if method=='control' else 0
    return AsianEstimate(mean,se,low,high,method,'sampled',n_paths,n_paths,units,pilot_n,
                         (units+pilot_n)*m,n_paths+pilot_n,
                         n_paths+pilot_n if method=='control' else 0,0,beta,(),tuple(diagnostics))
