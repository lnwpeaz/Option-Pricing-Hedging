"""Independent low-dimensional payoff quadrature; no pricing/kernel imports.

QUADPACK error and omitted-normal-tail bound are separate diagnostics. Neither
is a full floating-point error guarantee. Integration is over [-12,12].
"""
from dataclasses import dataclass
import math
import numpy as np
from scipy.integrate import quad
from scipy.special import ndtr


@dataclass(frozen=True)
class IntegralReference:
    price: float
    error_estimate: float
    tail_bound: float
    evaluations: int


def _integrate(f, points, tail):
    points=sorted(set([-12.,12.]+[float(x) for x in points if -12<x<12]))
    total=error=0.; count=0
    def measured(z):
        nonlocal count
        count+=1
        return f(z)*math.exp(-.5*z*z)/math.sqrt(2*math.pi)
    for a,b in zip(points,points[1:]):
        p,e=quad(measured,a,b,epsabs=1e-11,epsrel=2e-12,limit=200)
        total+=p;error+=e
    if not all(math.isfinite(x) for x in (total,error,tail)):
        raise FloatingPointError('nonfinite integral reference')
    return IntegralReference(total,error,tail,count)


def integrate_geometric(spec):
    t=np.array(spec.fixing_times); m=len(t)
    mu=math.log(spec.spot)+(spec.risk_free_rate-.5*spec.volatility**2)*sum(t)/m
    var=spec.volatility**2*sum(min(x,y) for x in t for y in t)/m**2
    sd=math.sqrt(var); discount=math.exp(-spec.risk_free_rate*t[-1])
    sign=1 if spec.kind=='call' else -1
    if sd==0:return IntegralReference(discount*max(sign*(math.exp(mu)-spec.strike),0),0.,0.,0)
    boundary=(math.log(spec.strike)-mu)/sd
    tail=discount*(math.exp(mu+.5*var)*(ndtr(-12-sd)+ndtr(sd-12))+spec.strike*2*ndtr(-12))
    return _integrate(lambda z:discount*max(sign*(math.exp(mu+sd*z)-spec.strike),0),
                      [0,sd,boundary],float(tail))


def integrate_two_fixing(spec):
    if len(spec.fixing_times)!=2 or spec.averaging!='arithmetic':
        raise ValueError('requires two arithmetic fixings')
    t1,t2=spec.fixing_times; dt=t2-t1; r=spec.risk_free_rate; sig=spec.volatility
    sign=1 if spec.kind=='call' else -1; discount=math.exp(-r*t2)
    if sig==0:
        avg=spec.spot*(math.exp(r*t1)+math.exp(r*t2))/2
        return IntegralReference(discount*max(sign*(avg-spec.strike),0),0.,0.,0)
    sd1=sig*math.sqrt(t1); sd2=sig*math.sqrt(dt)
    def conditional(z):
        s1=spec.spot*math.exp((r-.5*sig*sig)*t1+sd1*z)
        mean2=s1*math.exp(r*dt); strike2=2*spec.strike-s1
        if strike2<=0:return discount*(.5*(s1+mean2)-spec.strike) if sign==1 else 0.
        d2=(math.log(s1/strike2)+(r-.5*sig*sig)*dt)/sd2; d1=d2+sd2
        value=(mean2*ndtr(d1)-strike2*ndtr(d2)) if sign==1 else (strike2*ndtr(-d2)-mean2*ndtr(-d1))
        return .5*discount*float(value)
    boundary=(math.log(2*spec.strike/spec.spot)-(r-.5*sig*sig)*t1)/sd1
    tail=discount*(spec.spot*(math.exp(r*t1)+math.exp(r*t2))/2*(ndtr(-12-sd1)+ndtr(sd1-12))+spec.strike*2*ndtr(-12))
    return _integrate(conditional,[0,sd1,boundary],float(tail))
