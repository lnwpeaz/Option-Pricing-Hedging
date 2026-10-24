# GBM market paths: the bridge from pricing to hedging

Executed model experiment; no market data or hedge trades are used. The output
is a reusable collection of simulated stock paths, not a forecast or trading P&L.

## Scenario and timing

S0=100, maturity=1 years,
physical drift mu=8.0%, continuous risk-free rate r=5.0%,
constant annual volatility=20.0%, no dividends.
Both measures use the same Brownian shocks. Physical drift is an assumed scenario
parameter, not an estimated expected market return. RN drift r is for pricing checks.

The main sample contains **10,000 paths and 253 time points**
(252 intervals). Grid dates are regular k/252 years
strictly before expiry, then exact expiry; the final step may be shorter.
The first 12 path IDs are shown without selecting attractive outcomes.

## Exact transitions

```text
S_next = S_now * exp((drift - sigma^2/2)*dt + sigma*sqrt(dt)*Z)
Z ~ N(0,1), independent across paths and intervals
```

Log increments are accumulated in batches before exponentiation. This is exact
at the selected grid dates under constant-parameter GBM, without Euler time-step
bias. It does not recover the continuous trajectory between grid dates.
The generator validates irregular times, positivity, finite ranges and explicit
drift, and deterministic limits consume no random samples.

## Main-sample terminal results

| Measure | Sample mean | Theoretical mean | Sample SD | SE of mean |
|---|---:|---:|---:|---:|
| Physical | 107.938550 | 108.328707 | 21.767057 | 0.217671 |
| Risk-neutral | 104.748483 | 105.127110 | 21.123744 | 0.211237 |

Under physical GBM, E[S_T]=S0*exp(mu*T). Under RN GBM,
E[exp(-r*T)*S_T]=S0. Main-sample discounted RN mean:
**99.639840**, with sample SE **0.200935**,
against theoretical 100.000000. A finite sample need not match exactly.

## Independent-repeat diagnostics

All 32 repeats are retained; each contains 2,000 paths
per measure. The two measures share shocks within a repeat; different repeat IDs
have separate SeedSequence streams. The paired measures are not independent extra evidence.

| Measure | Ensemble terminal mean | Theory | Approx. 95% interval for ensemble mean |
|---|---:|---:|---:|
| Physical | 108.338874 | 108.328707 | [108.176038, 108.501711] |
| Risk-neutral | 105.136977 | 105.127110 | [104.978953, 105.295000] |

RN ensemble discounted mean=100.009386; approximate 95% interval
[99.859069, 100.159703].
These intervals use variation across independent repeats. Individual intervals
and time-point mean bands are approximate and are not simultaneous confidence bands.
The 5th–95th percentile fan in paths.png describes dispersion across paths,
not uncertainty in the mean and not a calibrated forecast interval for real prices.

Terminal log-return diagnostics across the independent repeats:

| Measure | Mean log return | Theory | Mean sample log-return variance | Theory |
|---|---:|---:|---:|---:|
| Physical | 0.060004 | 0.060000 | 0.040132 | 0.040000 |
| Risk-neutral | 0.030004 | 0.030000 | 0.040132 | 0.040000 |

The theoretical log-return mean is (drift-sigma^2/2)*T and variance is sigma^2*T.
Their ensemble standard errors and every repeat's values are retained in summary.json
and validation.csv. Common shocks make the log-return variances of paired measures
the same up to floating-point rounding; they are not two independent confirmations.

## Computer Engineering and saved data

The physical matrix has shape (10000, 253), dtype float64,
and data size **19.302 MiB** (excluding its NPY header).
The demo also holds the RN matrix for paired diagnostics. Work is O(N*M); returned
matrix storage is O(N*M), and one reusable float shock buffer is O(batch_size*M).
At configured batch_size=512, that buffer uses up to
0.984 MiB. This is not total process RSS.
Single-call simulation times in summary.json are illustrative, not a performance benchmark.

paths.npy contains physical paths; times.npy contains their exact grid. Load them
with allow_pickle=False. They provide the same path IDs for future hedge-frequency
and transaction-cost comparisons. preview_paths.csv preserves the first fixed IDs;
terminal_results.csv preserves paired final prices; time_statistics.csv and
validation.csv retain uncertainty and all repeat IDs.

## Reproduction

```sh
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.paths_demo \
  --config configs/gbm_paths.toml --output-dir reports/runs/my-gbm-paths
```

For the exact run use saved input_config.toml. Output folders must be new.
manifest.json records PCG64 seed construction, config, versions, platform, source
and artifact hashes. Fixed inputs/environment reproduce numerical outputs; times
and PNG bytes need not be stable across environments. RNG call shapes and library
versions are part of the reproducibility scope.

## Next step and limits

The next module is a self-financing short-call hedge ledger: opening premium,
stock trades, cash interest, transaction costs and terminal settlement. No hedge
effectiveness has been measured here. GBM excludes jumps, stochastic volatility,
liquidity constraints and changing spreads; its assumptions are explicit inputs.
