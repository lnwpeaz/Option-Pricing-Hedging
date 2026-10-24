# Saved runs, integrity and source replay

New runs of pricing_demo, convergence_demo, monte_carlo_demo, paths_demo,
validation_demo, hedge_demo and the paired runner preserve actual source bytes in `source_snapshot.zip`. The completed
manifest is written last, after figures, data and snapshot, and lists artifact SHA-256s.
`status=completed` means the run finished writing; numerical acceptance is recorded
separately in the results/summary, for example `analytic_checks_passed`.

## Verify recorded bytes

```sh
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.verify_run \
  reports/examples/research-validation
```

The verifier reads without executing archived code. It checks exact input bytes,
declared artifact hashes, archive hash, safe relative archive names, exact archive
entry set, inner content hashes and source alignment with the run manifest.
These checks establish consistency relative to the supplied manifest. They are not
a signature, author authentication or a correctness proof of reported calculations.
They do not reject unrelated extra files outside the archive.

The earlier `milestone-1`, `milestone-2a`, `milestone-2b` and `milestone-3` examples
retain their original records. Source hashes identify their original code; they
cannot recover missing old source bytes. The verifier reports `source_recoverable=false`
for these runs. Some earlier records lack artifact hashes; this is reported as an
unavailable check, not a passing one. Do not compare historical source hashes to
current source and conclude that historical results were created by current code.

## Recover source and replay trusted runs

Extract a trusted, locally generated snapshot into a fresh directory. Read
`SNAPSHOT.json` for Python/platform/runtime versions and `REPLAY.md` for its entrypoint.
The archive contains:

- All package Python sources under `src/option_hedging/` and exact `input_config.toml`.
- Runtime dependency versions, Python/platform metadata and replay instructions.
- Available checkout tests/configs, pyproject, README and dependency snapshot.

From that extracted directory, use the recorded environment and execute:

```sh
PYTHONPATH=src /absolute/path/to/python -m option_hedging.experiments.validation_demo \
  --config input_config.toml --output-dir replay-output
```

The executable path may point to the original `.venv/bin/python`; setting `PYTHONPATH`
to the extracted `src` makes the recovered package supply the calculation code.
For validation_demo, compare `reference_checks.csv`, `tree_checks.csv`,
`mc_estimates.csv`, `mc_metrics.csv` and `summary.json`. Those files contain no timings.
For convergence_demo ignore `elapsed_seconds` when comparing numerical CSV columns.
MC benchmark timing, manifests' timestamps and figure/ZIP bytes are not numerical
replay acceptance criteria.

Recorded dependency pins are an environment snapshot, not a portable hash-verified
lock or a reconstruction of compiler/BLAS/platform. Matching seeds alone is insufficient
when library versions, call shapes or numerical builds change. See
[NumPy's RNG compatibility policy](https://numpy.org/doc/stable/reference/random/compatibility.html).
Replay evidence here applies to the recorded current environment; it does not assert
cross-platform byte identity. The verifier never automatically extracts or executes
untrusted archives.

## Independent reference boundaries

The new validation reference integrates discounted payoff directly under a normal
shock, independently of the project pricing/GBM routines. Normal tails supply a
separate upper bound on omitted payoff. The adaptive quadrature's error estimate
is not a rigorous total floating-point error bound; see
[SciPy quad](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad.html).
Absolute agreement does not establish relative accuracy for arbitrarily tiny prices
or validate the model against real markets. Raw degenerate CI outcomes remain in
saved data; the diagnostic floor only changes interpretation and figure scaling.

## Milestone4 replay acceptance

For hedge_demo compare path.csv, ledger.csv, unhedged_ledger.csv,
accounting_checks.csv and summary.json byte-for-byte in the recorded environment.
No RNG/timing fields enter these files. Read the snapshot REPLAY.md for its
entrypoint. Image/manifest bytes are not numerical replay criteria. The one-path
ledger validates accounting, not the distribution of hedge performance.

## Milestone5 replay acceptance

Compare scenarios.csv, path_results.csv, metrics.csv, paired_comparisons.csv,
scalar_checks.csv, ledger.csv, summary.json and bootstrap_fields.json. Compare
paths.npy/times.npy/bootstrap_statistics.npy arrays exactly under the recorded
environment. performance.json contains timing observations and is excluded from
numerical repeatability claims, while its saved bytes still have an artifact hash.
Shared-ID bootstrap is conditional on the simulated model; reproducible arrays do
not establish effectiveness on real portfolios.


## V2-A Asian numerical replay

Canonical inputs: configs/asian_study.toml; executed outputs: reports/examples/v2-asian/.
Optional research comparator is pinned in requirements-research.txt (QuantLib==1.44)
and captured in runtime pins/source archives when installed. SciPy>=1.15 is required
for the Sobol rng API; the recorded environment uses 1.18.1. Study RNG keys are
[80,fixing identity,strike index,N,macro repeat,method stream ID,seed]; Sobol and
bridge share stream ID3. Child scrambles derive from R four-word uint32 entropies.
Bootstrap keys=[81,contract index,N,seed], sharing requested macro IDs across methods.
No Python hash() or global RNG is used. Config bytes are preserved exactly.

reports/verification/audit_asian.py independently rederives saved QMC uncertainty,
control pilot coefficients, work counters, reference classifications and macro/
paired bootstrap endpoints. The canonical audit proof is v2-asian-checks.json.
reports/verification/replay_asian.py verifies the trusted archive, extracts captured
sources into a new folder, checks the actual imported module path/runtime pins and
executes the full CLI. Numerical CSV/JSON and exact input comparisons are separated
from stage timings, benchmark/allocation observations and figures. Never treat
hash verification alone as proof of execution or mathematical correctness.

Reference precision gate is independent of byte completion: all 6 primary external
references are low_precision, and all 90 precision rankings are withheld. Replay
reproduces this limitation rather than changing engines/grids to obtain a pass.
