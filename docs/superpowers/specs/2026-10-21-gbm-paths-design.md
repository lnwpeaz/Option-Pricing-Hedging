# Milestone 3: reproducible GBM market paths

The user authorized the next previously described step: simulate full stock-price
paths for the future delta hedge. Execute in this chat. Pricing/Monte Carlo remains
implemented; the hedge ledger is deliberately the following milestone.

## Design choice

Use exact GBM log increments, not Euler discretization. The API requires drift
explicitly, so physical mu and risk-neutral r are caller decisions. Simulate in
path-major batches: O(N*M) time, O(N*M) returned matrix and O(B*M) workspace. A
step-major implementation could use less workspace but changes RNG mapping;
this implementation prioritizes a simple, documented, reproducible row layout.

`simulate_paths(*, spot, drift, volatility, times, n_paths, rng, batch_size=512)`
returns a float64 array with shape (n_paths, len(times)), exact initial spot,
positive finite prices, and no mutation of times or global RNG state. Accept
finite 1D numeric times starting at zero, strictly increasing, including [0].
Require positive spot and integer positive n_paths/batch_size, excluding booleans.
Zero volatility and [0] consume no RNG. Invalid range/underflow raises ValueError.
Keep the existing terminal-transform API and Monte Carlo behavior intact.

Generate standard normals in path-major batches and reuse the batch array for
increments, cumulative log returns and exponentiation. Fixed configuration and
NumPy environment reproduce numerical results; alternate batching is compared
with tolerance, not promised bit-for-bit across versions or platforms.

`make_time_grid(*, maturity_years, steps_per_year=252)` returns zero, regular
k/steps_per_year points strictly before expiry, and exact expiry. The final interval
may be shorter. Zero maturity returns [0]. Validate finite nonnegative maturity
and positive integer frequency. The core path function also accepts irregular grids.

## Executed learning demo

Use dedicated configs/gbm_paths.toml with [market], [simulation], [validation].
Baseline: S0=100, T=1, mu=.08, r=.05, sigma=.20, N=10000, 252 intervals.
Require positive demo maturity and at least two paths; support sigma=0 explicitly.
Generate physical and risk-neutral ensembles using identical Brownian shocks
(same explicit PCG64 seed construction) so drift comparisons are paired. Do not
count the paired measures as independent evidence.

Save physical paths.npy and times.npy for future hedging, first fixed path IDs in
preview_paths.csv, terminal_results.csv for both measures, time-point statistics,
32 independent repeated-seed validation rows per measure, summary.json, exact and
effective config, source/config/output hashes, platform and versions. Save two
readable figures and English RESULTS.md plus a Thai GBM learning guide.

Check physical E[S_T]=S0 exp(mu*T), risk-neutral E[exp(-rT)S_T]=S0, log-return
mean/variance and reproducibility. Use repeated samples and broad tolerances in
statistical tests, not a requirement that a single 95% interval always cover truth.
Quantile fan bands describe dispersion across paths, not confidence in mean price.
Keep all repeats; report ensemble uncertainty without declaring calibrated market
forecasting or hedge performance. Runtime is illustrative, not a speed benchmark.

All config validation and numerical calculations precede output creation. Refuse
existing output folders. A completed manifest is written last; output hashes exclude
the manifest itself. Old milestone manifests retain their historical source hashes.

## Acceptance

Tests first: irregular-grid manual calculation, shape/start/positivity, deterministic
limits/RNG consumption, explicit drift, global RNG isolation, batching/prefix
reproducibility, malformed grids and numerical range errors, independent-seed moments.
Real CLI tests verify loadable saved matrices, paired drift relation, complete raw
data, numeric reproducibility, invalid config/no output, no overwrite and hashes.
Run full suite and full demo, inspect figures, review code, and update project status.
