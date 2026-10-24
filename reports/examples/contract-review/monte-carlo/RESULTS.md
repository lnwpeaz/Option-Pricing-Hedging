# Monte Carlo pricing: accuracy, uncertainty and computational efficiency

This is an executed model-based numerical experiment, not trading performance.
European options without dividends; S=120, baseline K=125,
T=0.5 years, r=4.0%, sigma=25.0%.
Prices use exact terminal GBM under risk-neutral drift r. Black-Scholes is used
only as the experiment's analytic reference, separate from the MC estimator.

## Experiment design

- Production sample sizes: [4096, 16384, 65536].
- Strikes: [110.0, 125.0, 140.0]; both call and put; all three methods; 32 independent repeats per cell.
- Control beta uses 1024 additional independent pilot paths per run.
- Antithetic N counts terminal evaluations; N/2 independent pair averages determine SE.
- PCG64 with SeedSequence identifiers; every raw seed key is in estimates.csv.
- RMSE percentile intervals use 1000 bootstrap resamples of independent repeats.
- Coverage intervals are 95% Wilson intervals for the proportion of runs whose normal CI contains truth.

## Baseline strike, largest sample size: N=65,536

| Kind | Method | Bias | RMSE | Mean SE | CI coverage | MSE gain vs plain | Median ms |
|---|---|---:|---:|---:|---:|---:|---:|
| call | antithetic | 0.002484 | 0.037261 | 0.041588 | 100.0% | 2.57 | 0.526 |
| call | control | 0.005304 | 0.027253 | 0.025286 | 96.9% | 4.81 | 0.675 |
| call | plain | 0.017718 | 0.059768 | 0.050581 | 90.6% | 1.00 | 0.606 |
| put | antithetic | -0.006371 | 0.032522 | 0.027670 | 93.8% | 2.52 | 0.521 |
| put | control | 0.002262 | 0.028888 | 0.025277 | 90.6% | 3.19 | 0.662 |
| put | plain | -0.007575 | 0.051628 | 0.047065 | 93.8% | 1.00 | 0.605 |

MSE gain compares equal production N. Control uses extra pilot work: consult
work_normalized_gain and time_efficiency_gain in metrics.csv before judging cost.
Reported gains are empirical ratios with finite-repeat uncertainty, not guaranteed
speedups. Lower time*RMSE^2 is a useful local efficiency diagnostic; it is not an
equal-wall-clock experiment or a universal performance ranking.

Log-log empirical RMSE slopes across the sample grid (the MC asymptotic reference is -0.5):

- call / plain: -0.436
- call / antithetic: -0.566
- call / control: -0.476
- put / plain: -0.397
- put / antithetic: -0.391
- put / control: -0.445

The baseline is one payoff regime. robustness.png and the full metrics.csv retain
all strike/kind scenarios; benefits can change when a payoff becomes rare or nearly linear.
Raw signed errors, CI endpoints and fitted beta values are retained in estimates.csv.

## Computer Engineering measurements

Kernel-only benchmark: 65,536 identical pre-generated normals,
5 timed repetitions after warm-up, alternating scalar/vector order.
Median scalar/vector speedup on this run: **14.95x**.
Both kernels compute discounted payoff means. RNG generation and sample uncertainty
are excluded from both; vectorized array allocation and validation are included.
This is not the speedup of a complete MC price, and the Python scalar baseline
is educational rather than a tuned compiled competitor.

Complete plain-MC batching benchmark includes RNG, payoff, validation and sample
statistics; Generator construction is excluded from every timed call. Batch order
alternates. Allocation is measured in a separate untimed pass with tracemalloc.

| Batch size | Median complete price ms | Peak traced MiB |
|---:|---:|---:|
| 512 | 2.459 | 0.033 |
| 4,096 | 0.851 | 0.252 |
| 32,768 | 0.606 | 1.845 |
| 65,536 | 0.605 | 2.689 |

Time complexity is O(N + pilot paths); peak numerical workspace is O(batch size).
Exact terminal sampling avoids building N x 253 path matrices for European prices.
The allocation figures are observed Python/NumPy traced allocations, not RSS or a
guaranteed byte budget. BLAS/threading, CPU caches, scheduling, thermals, sample size
and tracing overhead affect measurements. No GPU or multicore implementation was measured.

## Statistical and numerical limits

Normal confidence intervals are approximate. A single interval need not contain
truth. Finite-repeat coverage itself is uncertain. Zero observed variance can mean
no rare payoffs were sampled; it does not establish an exact price. zero_se_repeats
is recorded explicitly. Pilot-fitted control estimates and intervals are not clipped
to theoretical option bounds. Overflow, terminal underflow and unrepresentable
moments raise explicit errors; arbitrary extreme floating-point inputs are not supported.

## Reproduction and artifacts

From the project root, choose a new output folder:

```sh
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.monte_carlo_demo \
  --config configs/monte_carlo.toml --output-dir reports/runs/my-monte-carlo
```

For this exact run use the saved input_config.toml. manifest.json records source,
config and output SHA-256 hashes, versions, platform and RNG derivation. Same inputs
and recorded environment reproduce numerical estimates; timings and figure bytes
are not guaranteed across environments. NumPy does not promise identical samples
across every build or different RNG call shapes. This run does not simulate hedging.
