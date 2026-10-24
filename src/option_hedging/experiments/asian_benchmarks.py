"""Complete-estimator wall time, and separate untimed Python allocations."""
from dataclasses import asdict
from time import perf_counter
import tracemalloc
import numpy as np
from option_hedging.asian_contracts import AsianOptionSpec
from option_hedging.pricing.asian_monte_carlo import price


def benchmark(config):
    b=config['benchmark'];s=config['study'];o=config['option']
    times=[];allocations=[]
    if not b['enabled']:return times,allocations
    m=b['fixing_count'];fixings=tuple(((365*j)//m)/365 for j in range(1,m+1))
    spec=AsianOptionSpec(o['spot'],b['strike'],o['risk_free_rate'],o['volatility'],o['kind'],fixings,o['averaging'])
    def run(method,batch,repeat):
        rng=np.random.default_rng(np.random.SeedSequence([82,b['seed'],batch,repeat,0 if method=='sobol_bridge' else s['methods'].index(method)]))
        return price(spec,n_paths=b['paths'],method=method,rng=rng,batch_size=batch,
                     pilot_paths=s['pilot_paths'],scrambles=s['scrambles'],bits=s['sobol_bits'])
    for batch in b['batch_sizes']:
        warmups={}
        for method in s['methods']:
            try:
                run(method,batch,0);warmups[method]=('completed','')
            except (ValueError,FloatingPointError,OverflowError) as exc:
                warmups[method]=('failed',str(exc))
        for repeat in range(b['repeats']):
            order=s['methods'] if repeat%2==0 else list(reversed(s['methods']))
            for order_index,method in enumerate(order):
                start=perf_counter()
                try:
                    result=run(method,batch,repeat+1);elapsed=perf_counter()-start
                    row={k:v for k,v in asdict(result).items() if k not in ('scramble_prices','diagnostics')}
                    row.update(status='completed',error='')
                except (ValueError,FloatingPointError,OverflowError) as exc:
                    elapsed=perf_counter()-start;row=dict(status='failed',error=str(exc))
                row.update(method=method,batch_size=batch,repeat=repeat,order_index=order_index,elapsed_seconds=elapsed,
                           warmup_status=warmups[method][0],warmup_error=warmups[method][1])
                times.append(row)
        for method in s['methods']:
            tracemalloc.start()
            try:
                run(method,batch,b['repeats']+1);_,peak=tracemalloc.get_traced_memory()
                row=dict(method=method,batch_size=batch,peak_traced_bytes=peak,status='completed',error='')
            except (ValueError,FloatingPointError,OverflowError) as exc:
                row=dict(method=method,batch_size=batch,peak_traced_bytes=None,status='failed',error=str(exc))
            finally:tracemalloc.stop()
            allocations.append(row)
    return times,allocations
