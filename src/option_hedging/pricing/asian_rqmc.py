"""Independent scrambled Sobol quadrature; t uncertainty across scrambles.

Within-scramble points are dependent and are never treated as IID for SE. One
scramble's O((N/R)*m) points/normals are allocated, then payoffs are batched.
"""
import math
import numpy as np
from scipy.special import ndtri
from scipy.stats import qmc,t
from option_hedging.asian_contracts import AsianEstimate
from option_hedging.pricing._asian_statistics import ScaledMoments,currency,interval
from option_hedging.pricing.asian_samples import target_payoffs


def normals_from_uniforms(uniforms):
    raw=np.asarray(uniforms)
    if raw.dtype.kind not in 'fiu':raise TypeError('uniform points must be real numeric values')
    u=np.asarray(raw,dtype=float)
    if u.ndim!=2 or not np.all(np.isfinite(u)) or np.any((u<=0)|(u>=1)):
        raise ValueError('Sobol endpoint/nonfinite point cannot map to a finite normal')
    return ndtri(u)


def price_qmc(spec, *, n_paths, rng, method, batch_size, scrambles, bits):
    m=len(spec.fixing_times);n=n_paths//scrambles
    # All child entropies drawn before path work. Equal parent keys pair forward
    # and bridge methods using identical uniforms, without coupling scrambles.
    entropies=rng.integers(0,2**32,size=(scrambles,4),dtype=np.uint32)
    construction='bridge' if method=='sobol_bridge' else 'increments'
    prices=[]
    for entropy in entropies:
        child=np.random.Generator(np.random.PCG64(np.random.SeedSequence(entropy)))
        sampler=qmc.Sobol(d=m,scramble=True,bits=bits,rng=child)
        u=sampler.random_base2(n.bit_length()-1)
        z=normals_from_uniforms(u)
        moments=ScaledMoments()
        for start in range(0,n,batch_size):
            moments.update(target_payoffs(spec,z[start:start+batch_size],construction=construction))
        prices.append(currency(moments.mean_value,spec.spot))
    summary=ScaledMoments();summary.update(np.asarray(prices))
    mean,se=summary.mean_value,summary.standard_error
    low,high=interval(mean,se,float(t.ppf(.975,scrambles-1)))
    diagnostics=[f'sobol_bits={bits}','approximate_student_t_95']
    if se==0:diagnostics.append('zero_observed_variance')
    return AsianEstimate(mean,se,low,high,method,'sampled',n_paths,n_paths,scrambles,0,
                         n_paths*m,n_paths,0,scrambles,None,tuple(prices),tuple(diagnostics))
