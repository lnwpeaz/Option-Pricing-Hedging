"""Pure exact Brownian transforms on explicit fixings, excluding time zero.

Bridge order: terminal first, FIFO index bisection, left interval before right.
Conditional means/variances use actual times, including on irregular schedules.
"""
from collections import deque
import math
import numpy as np
from option_hedging.asian_contracts import validate_times


def brownian_from_normals(normals, fixing_times, *, construction='increments'):
    t=np.asarray(validate_times(fixing_times))
    raw=np.asarray(normals)
    if raw.dtype.kind not in 'fiu':raise TypeError('normals must be real numeric values')
    z=np.asarray(raw,dtype=float)
    if z.ndim!=2 or z.shape[1]!=len(t) or z.shape[0]<1:
        raise ValueError('normals must have shape (nonempty batch, fixings)')
    if not np.all(np.isfinite(z)):raise ValueError('normals must be finite')
    if construction not in ('increments','bridge'):raise ValueError('unknown Brownian construction')
    with np.errstate(over='raise',invalid='raise',under='ignore'):
        if construction=='increments':
            w=np.cumsum(z*np.sqrt(np.diff(np.r_[0.,t])),axis=1)
        else:
            times=np.r_[0.,t]; m=len(t)
            values=np.empty((len(z),m+1));values[:,0]=0.
            values[:,m]=math.sqrt(t[-1])*z[:,0]
            queue=deque([(0,m)]);coordinate=1
            while queue:
                left,right=queue.popleft()
                if right-left<2:continue
                mid=(left+right)//2;tl,tm,tr=times[[left,mid,right]]
                weight=(tm-tl)/(tr-tl)
                conditional_sd=math.sqrt(tm-tl)*math.sqrt((tr-tm)/(tr-tl))
                values[:,mid]=(1-weight)*values[:,left]+weight*values[:,right]+conditional_sd*z[:,coordinate]
                coordinate+=1;queue.extend([(left,mid),(mid,right)])
            w=values[:,1:]
    if not np.all(np.isfinite(w)):raise FloatingPointError('unrepresentable Brownian values')
    return w
