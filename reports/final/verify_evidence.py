"""Read-only acceptance checks for report evidence, independent of metric helpers.

Run with the project's Python and PYTHONPATH=src. This is a report QA utility,
not a new pricing API or a proof of model suitability for real trading.
"""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from option_hedging.contracts import OptionSpec
from option_hedging.experiments.verify_run import verify_run
from option_hedging.validation.payoff_reference import integrate_payoff

ROOT = Path(__file__).resolve().parents[2]


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def check_study(path):
    integrity = verify_run(path)
    cfg = json.loads((path / "effective_config.json").read_text())
    metadata = json.loads((path / "bootstrap_fields.json").read_text())
    bootstrap = np.load(path / "bootstrap_statistics.npy", allow_pickle=False)
    n = cfg["simulation"]["paths"]
    raw = read_csv(path / "path_results.csv")
    groups = {}
    for row in raw:
        groups.setdefault(int(row["scenario_id"]), []).append(row)
    scenarios = {int(r["scenario_id"]): r for r in read_csv(path / "scenarios.csv")}
    metrics = {(int(r["scenario_id"]), r["premium_basis"]): r
               for r in read_csv(path / "metrics.csv")}
    cell_id = {(r["scenario_id"], r["premium_basis"]): i
               for i, r in enumerate(metadata["cells"])}
    max_error = 0.0

    def close(actual, expected, tolerance=1e-9):
        nonlocal max_error
        error = float(np.max(np.abs(np.asarray(actual) - np.asarray(expected))))
        max_error = max(max_error, error)
        if error > tolerance:
            raise AssertionError((actual, expected, error))

    for case_id, rows in groups.items():
        assert [int(r["path_id"]) for r in rows] == list(range(n))
        pnl = np.array([float(r["terminal_pnl"]) for r in rows])
        common = np.array([float(r["common_premium_pnl"]) for r in rows])
        close(common - pnl, float(scenarios[case_id]["premium_shift"]))
        for basis, values in (("model", pnl), ("common_reference", common)):
            saved = metrics[case_id, basis]
            stats = [np.mean(values), np.std(values, ddof=1),
                     np.sqrt(np.mean(values**2)), *np.quantile(values, [.05, .5, .95])]
            close(stats, [float(saved[k]) for k in metadata["statistics"]])
            close(float(saved["probability_loss"]), np.mean(values < 0))
            index = cell_id[case_id, basis]
            bounds = np.quantile(bootstrap[:, index, :], [.025, .975], axis=0)
            for k, field in enumerate(metadata["statistics"]):
                close(bounds[:, k], [float(saved[field + "_ci_low"]),
                                      float(saved[field + "_ci_high"])])
        if scenarios[case_id]["strategy"] == "delta_hedged":
            source = scenarios[case_id]
            free_id = next(i for i, c in scenarios.items()
                           if c["strategy"] == "delta_hedged"
                           and c["hedge_volatility"] == source["hedge_volatility"]
                           and c["rebalance_every_steps"] == source["rebalance_every_steps"]
                           and float(c["one_way_cost_bps"]) == 0)
            free = np.array([float(r["terminal_pnl"]) for r in groups[free_id]])
            close(free - pnl, [float(r["financed_costs"]) for r in rows])

    paired = read_csv(path / "paired_comparisons.csv")
    for pair in paired:
        basis = pair["premium_basis"]
        left, right = int(pair["left_scenario_id"]), int(pair["right_scenario_id"])
        for name, column in (("mean_pnl", 0), ("rmse", 2)):
            close(float(pair[name + "_difference"]),
                  float(metrics[left, basis][name]) - float(metrics[right, basis][name]))
            draws = bootstrap[:, cell_id[left, basis], column] - bootstrap[:, cell_id[right, basis], column]
            close(np.quantile(draws, [.025, .975]),
                  [float(pair[name + "_difference_ci_low"]), float(pair[name + "_difference_ci_high"])])
    market = cfg["market"]
    for case in scenarios.values():
        spec = OptionSpec(market["spot"], market["strike"], market["maturity_years"],
                          market["risk_free_rate"], float(case["hedge_volatility"]), "call")
        close(float(case["initial_premium"]), integrate_payoff(spec).price)
    return dict(integrity=integrity, paths=n, raw_rows=len(raw), metric_cells=len(metrics),
                paired_rows=len(paired), maximum_absolute_numeric_difference=max_error,
                point_statistics_and_saved_CI_endpoints_recomputed=True,
                path_ids_and_financed_cost_identities=True,
                initial_premiums_checked_by_payoff_integration=True)


def main():
    evidence = {
        "scope": "Report artifact/statistic QA; not market validation or new source replay",
        "studies": {name: check_study(ROOT / "reports/examples" / name)
                    for name in ("milestone-5", "contract-review/hedging")},
        "other_integrity": {name: verify_run(ROOT / "reports/examples" / name)
                            for name in ("milestone-2b", "research-validation", "milestone-4",
                                         "contract-review/pricing", "contract-review/monte-carlo")},
    }
    p = ROOT / "reports/examples/contract-review/pricing/baseline.csv"
    for row in read_csv(p):
        spec = OptionSpec(120, 125, .5, .04, .25, row["kind"])
        assert abs(float(row["price"]) - integrate_payoff(spec).price) < 1e-9
    evidence["contract_review_call_put_integrals_passed"] = True
    mcroot = ROOT / "reports/examples/contract-review/monte-carlo"
    mcgroups = {}
    for row in read_csv(mcroot / "estimates.csv"):
        key = tuple(row[k] for k in ("kind", "strike", "n_paths", "method"))
        mcgroups.setdefault(key, []).append(row)
    for row in read_csv(mcroot / "metrics.csv"):
        key = tuple(row[k] for k in ("kind", "strike", "n_paths", "method"))
        samples = mcgroups[key]
        errors = np.array([float(r["price"]) - float(r["reference"]) for r in samples])
        coverage = np.mean([float(r["ci_low"]) <= float(r["reference"]) <= float(r["ci_high"])
                            for r in samples])
        assert abs(float(row["rmse"]) - np.sqrt(np.mean(errors**2))) < 1e-12
        assert abs(float(row["bias"]) - np.mean(errors)) < 1e-12
        assert abs(float(row["coverage"]) - coverage) < 1e-12
        assert [int(r["repeat"]) for r in samples] == list(range(32))
    evidence["contract_review_monte_carlo"] = dict(raw_estimates=sum(map(len, mcgroups.values())),
                                                  cells=len(mcgroups), point_metrics_recomputed=True)
    evidence["input_sha256"] = {}
    inputs = [ROOT / "reports/examples/milestone-2b/summary.json",
              ROOT / "reports/examples/research-validation/summary.json",
              ROOT / "reports/examples/milestone-5/metrics.csv", p,
              mcroot / "summary.json", mcroot / "metrics.csv", mcroot / "estimates.csv"]
    for item in inputs:
        evidence["input_sha256"][str(item.relative_to(ROOT))] = hashlib.sha256(item.read_bytes()).hexdigest()
    output = ROOT / "reports/verification/final-report-evidence.json"
    output.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
