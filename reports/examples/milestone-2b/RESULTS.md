# Monte Carlo pricing: accuracy, uncertainty and computational efficiency

This is an executed model-based numerical experiment, not trading performance.
European options without dividends; S=100, baseline K=100,
T=1 years, r=5.0%, sigma=20.0%.
Prices use exact terminal GBM under risk-neutral drift r. Black-Scholes is used
only as the experiment's external numerical reference, never by the MC estimator.

## Experiment design

- Production sample sizes: [1024, 4096, 16384, 65536, 262144].
- Strikes: [80.0, 100.0, 120.0]; both call and put; all three methods; 64 independent repeats per cell.
- Control beta uses 2048 additional independent pilot paths per run.
- Antithetic N counts terminal evaluations; N/2 independent pair averages determine SE.
- PCG64 with SeedSequence identifiers; every raw seed key is in estimates.csv.
- RMSE percentile intervals use 2000 bootstrap resamples of independent repeats.
- Coverage intervals are 95% Wilson intervals for the proportion of runs whose normal CI contains truth.

## Baseline strike, largest sample size: N=262,144

| Kind | Method | Bias | RMSE | Mean SE | CI coverage | MSE gain vs plain | Median ms |
|---|---|---:|---:|---:|---:|---:|---:|
| call | antithetic | -0.000517 | 0.020207 | 0.020306 | 95.3% | 2.32 | 1.955 |
| call | control | 0.003112 | 0.009748 | 0.010968 | 100.0% | 9.95 | 2.452 |
| call | plain | -0.008179 | 0.030748 | 0.028742 | 96.9% | 1.00 | 2.253 |
| put | antithetic | 0.000589 | 0.012067 | 0.012940 | 93.8% | 1.73 | 1.928 |
| put | control | -0.001158 | 0.009536 | 0.010967 | 96.9% | 2.76 | 2.427 |
| put | plain | -0.001993 | 0.015851 | 0.016906 | 96.9% | 1.00 | 2.239 |

MSE gain compares equal production N. Control uses extra pilot work: consult
work_normalized_gain and time_efficiency_gain in metrics.csv before judging cost.
Reported gains are empirical ratios with finite-repeat uncertainty, not guaranteed
speedups. Lower time*RMSE^2 is a useful local efficiency diagnostic; it is not an
equal-wall-clock experiment or a universal performance ranking.

Log-log empirical RMSE slopes across the sample grid (the MC asymptotic reference is -0.5):

- call / plain: -0.477
- call / antithetic: -0.489
- call / control: -0.507
- put / plain: -0.513
- put / antithetic: -0.502
- put / control: -0.510

The baseline is one payoff regime. robustness.png and the full metrics.csv retain
all strike/kind scenarios; benefits can change when a payoff becomes rare or nearly linear.
Raw signed errors, CI endpoints and fitted beta values are retained in estimates.csv.

## Computer Engineering measurements

Kernel-only benchmark: 262,144 identical pre-generated normals,
9 timed repetitions after warm-up, alternating scalar/vector order.
Median scalar/vector speedup on this run: **13.06x**.
Both kernels compute discounted payoff means. RNG generation and sample uncertainty
are excluded from both; vectorized array allocation and validation are included.
This is not the speedup of a complete MC price, and the Python scalar baseline
is educational rather than a tuned compiled competitor.

Complete plain-MC batching benchmark includes RNG, payoff, validation and sample
statistics; Generator construction is excluded from every timed call. Batch order
alternates. Allocation is measured in a separate untimed pass with tracemalloc.

| Batch size | Median complete price ms | Peak traced MiB |
|---:|---:|---:|
| 512 | 9.551 | 0.033 |
| 4,096 | 3.383 | 0.252 |
| 32,768 | 2.408 | 1.845 |
| 262,144 | 2.875 | 10.501 |

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
