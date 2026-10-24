"""Scale each coordinate before merging centered moments/covariances.

The covariance matrix stays in scaled units; currency scaling happens only after
standard errors are formed. Large or tiny representable samples need no squares
in their original units.
"""
import math
import numpy as np


class ScaledMoments:
    def __init__(self):
        self.n=0
        self.scale=None
        self.mean=None
        self.m2=None

    def update(self, values):
        x=np.asarray(values,dtype=float)
        if x.ndim==1:x=x[:,None]
        if x.ndim!=2 or not len(x) or not np.all(np.isfinite(x)):
            raise FloatingPointError('moments require nonempty finite observations')
        d=x.shape[1]
        if self.scale is None:
            self.scale=np.zeros(d);self.mean=np.zeros(d);self.m2=np.zeros((d,d))
        if d!=len(self.scale):raise ValueError('moment dimension changed')
        scales=np.maximum(self.scale,np.max(np.abs(x),axis=0))
        safe=np.where(scales>0,scales,1.)
        with np.errstate(over='raise',invalid='raise',divide='raise',under='ignore'):
            ratio=self.scale/safe
            old_mean=self.mean*ratio; old_m2=self.m2*np.outer(ratio,ratio)
            xs=x/safe
            if np.any((x!=0)&(xs==0)):raise FloatingPointError('moment rescaling underflow')
            bm=xs.mean(axis=0);centered=xs-bm
            batch_m2=centered.T@centered
            if np.any((np.diag(batch_m2)==0)&np.any(centered!=0,axis=0)):
                raise FloatingPointError('centered moment underflow')
            total=self.n+len(x);delta=bm-old_mean
            merge=np.outer(delta,delta)*(self.n/total)*len(x)
            if self.n and np.any((delta!=0)&(np.diag(merge)==0)):
                raise FloatingPointError('between batch moment underflow')
            self.m2=old_m2+batch_m2+merge
            self.mean=old_mean+delta*(len(x)/total)
            self.scale=scales;self.n=total
        if not np.all(np.isfinite(self.m2)) or not np.all(np.isfinite(self.mean)):
            raise FloatingPointError('unrepresentable moments')

    @property
    def mean_value(self):
        return self._restore(self.mean[0],self.scale[0])

    @staticmethod
    def _restore(value,scale):
        result=float(value)*float(scale)
        if not math.isfinite(result) or (value!=0 and scale!=0 and result==0):
            raise FloatingPointError('moment restoration outside numeric range')
        return result

    @property
    def standard_error(self):
        if self.n<2:raise ValueError('SE requires at least two independent observations')
        value=math.sqrt(float(self.m2[0,0]))/math.sqrt(self.n-1)/math.sqrt(self.n)
        return self._restore(value,self.scale[0])

    @property
    def beta(self):
        if self.scale[1]==0 or self.m2[1,1]==0:return 0.
        ratio=float(self.m2[0,1]/self.m2[1,1])
        if ratio==0:return 0.
        # Log scaling avoids overflow in an intermediate ratio of column scales.
        log_beta=math.log(abs(ratio))+math.log(self.scale[0])-math.log(self.scale[1])
        try:result=math.copysign(math.exp(log_beta),ratio)
        except OverflowError as exc:raise FloatingPointError('control coefficient overflow') from exc
        if not math.isfinite(result) or result==0:raise FloatingPointError('control coefficient range error')
        return result


def currency(value,spot):
    result=float(value)*spot
    if not math.isfinite(result) or (value!=0 and result==0):
        raise FloatingPointError('estimate currency scale outside numeric range')
    return result


def interval(mean,se,critical):
    low,high=mean-critical*se,mean+critical*se
    if not all(math.isfinite(v) for v in (mean,se,low,high)):
        raise FloatingPointError('unrepresentable estimate uncertainty')
    return low,high


def log_ratio(a,b):
    """Preserve neighboring positive floats before taking logarithms."""
    difference=a-b
    if abs(difference)<=.5*b:
        return math.log1p(difference/b)
    return math.log(a)-math.log(b)


def log_mean_exp(logs):
    """Row log averages, retaining small first- and second-order changes.

    Tiny logs need a series residual: expm1(x) itself can round to x and erase
    the positive arithmetic/geometric gap when first-order terms cancel.
    """
    logs=np.asarray(logs,dtype=float)
    if logs.ndim!=2 or not logs.shape[1] or not np.all(np.isfinite(logs)):
        raise FloatingPointError('log averages require finite nonempty rows')
    largest=logs.max(axis=1)
    with np.errstate(over='raise',invalid='raise',divide='raise',under='ignore'):
        out=largest+np.log1p(np.expm1(logs-largest[:,None]).mean(axis=1))
    tiny=np.maximum(np.abs(largest),np.abs(logs.min(axis=1)))<1e-8
    for index in np.flatnonzero(tiny):
        row=logs[index];linear=math.fsum(float(x) for x in row)/len(row)
        residual=math.fsum(float(x)*float(x)*(.5+float(x)*(1/6+float(x)/24)) for x in row)/len(row)
        if linear==0 and residual==0 and np.any(row!=0):
            raise FloatingPointError('positive average correction outside numeric range')
        out[index]=math.log1p(linear+residual)
    return out
