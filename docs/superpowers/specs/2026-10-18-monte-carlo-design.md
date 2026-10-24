# Monte Carlo as the computational centerpiece

The user explicitly requested continued implementation and emphasized Monte Carlo as
the bridge to Computer Engineering. Deliver a reproducible numerical experiment,
not merely a random price. Implementation proceeds in this chat under that authorization.

## Selected design

Compare three estimators: plain independent Monte Carlo, antithetic pairs, and a
discounted-stock control variate fitted on an independent pilot. Use exact terminal
GBM sampling under drift r, with no time discretization bias for European payoffs.
Alternative GPU/distributed implementations are deferred: first establish a tested
CPU reference, measure bottlenecks, and make any later acceleration comparable.

The public price API accepts an OptionSpec, explicit numpy Generator, n_paths,
method, batch_size and pilot_paths. No file I/O, global RNG, analytic option price,
or silently clipped results enter the estimator. Return frozen PriceEstimate with
price, sample standard error, approximate normal 95% CI, production path count,
independent observation count, pilot count, method and fitted beta.

For antithetic, n_paths is even and at least four; independent observations are
pair averages, hence n_paths/2. For control, pilot paths are additional work and
never included in production statistics. E[exp(-rT) S_T] = S0 is the known control
expectation. Plain/control require at least two production paths. Finite-sample
normal intervals are approximate; zero observed variance is not proof of accuracy
for a rare payoff. Adjusted control estimates are not clipped to option bounds.

## Engineering

Use NumPy vectorization, bounded batches and merged central moments for stable
O(batch_size) workspace, O(n_paths + pilot_paths) runtime. A shared terminal-GBM
transform in simulation/gbm.py accepts explicit drift and supplied normals; full
time-grid market paths remain milestone 3. Reject nonfinite/underflowed terminal
values and unrepresentable moments with clear errors. Handle expiry and sigma=0
without consuming RNG. Validate integers (including rejecting booleans) and RNG.

Use explicit PCG64 generators and SeedSequence identifiers for independent
experiment cells and repeats. Save seed construction, exact config, versions,
platform, source hashes and artifact hashes. Same environment/config gives the
same numerical results; timings are inherently variable and RNG streams are not
promised identical across NumPy builds or different batch call shapes.

## Experiments and evidence

Run call and put over increasing production sample sizes and repeated independent
seeds. Save every estimate, SE, CI, beta, count and elapsed time. Aggregate bias,
empirical RMSE, mean SE, empirical SD, 95% coverage with Wilson uncertainty,
median runtime and time*RMSE^2. Record pilot cost and independent sample counts.
Fit log-log RMSE slopes as finite-sample diagnostics, not guarantees.

Separately benchmark a transparent scalar payoff kernel against the vectorized
kernel on identical pre-generated normals, warm up, alternate execution order,
record repeated timings, and assert numerical agreement. Exclude RNG/statistics
from both kernels and label that boundary. Benchmark end-to-end batching with RNG
and statistics included; report observed Python/NumPy traced peak allocations
(not RSS) in a separate pass, plus theoretical complexity.

Generate readable static figures, all raw CSVs, an English results brief and a
Thai learning guide connecting RNG, vectorization, online reduction, complexity,
error budgets and benchmark design. Include limits and commands to reproduce.
Refuse existing output directories and validate/calculate before output creation.
No historical trading, hedge performance or guaranteed speedup claims.

## Acceptance

Independent fixed-normal calculations verify discounting, sample SE, pairing and
pilot separation. Statistical tests use repeated seeds and broad predeclared
tolerances. CLI tests exercise actual outputs, rerun reproducibility, invalid
config and overwrite prevention. All previous tests remain green. Run the full
experiment and inspect every figure before reporting measured findings.
