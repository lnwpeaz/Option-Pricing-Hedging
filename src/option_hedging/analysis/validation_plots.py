"""Multi-regime checks show numerical errors and sampling-method limitations."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


COLORS = {"plain": "#64748b", "antithetic": "#008b8b", "control": "#dd7935"}
METHODS = tuple(COLORS)


def make_validation_figures(references, trees, metrics, *, tolerance, precision_floor):
    figures = {}
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "#f8fafc", "axes.facecolor": "white"}):
        fig, axes = plt.subplots(2, 1, figsize=(11, 8), layout="constrained")
        axes[0].plot([r["scenario_id"] for r in references], [r["absolute_difference"] for r in references],
                          "o", color="#008b8b", ms=3, label="Analytic vs independent payoff integral")
        axes[0].set_yscale("symlog", linthresh=1e-12)
        axes[0].set_ylim(0, max(2 * tolerance, 1.1 * max(r["absolute_difference"] for r in references)))
        axes[0].axhline(tolerance, color="#b75c38", ls="--", label=f"Predeclared absolute tolerance: {tolerance:g}")
        axes[0].set(title="Independent calculation across the whole declared domain", xlabel="Scenario ID (parameters in reference_checks.csv)",
                    ylabel="Absolute premium difference (linear below 1e-12)")
        axes[0].legend(fontsize=8)
        steps = sorted({r["steps"] for r in trees})
        # Include exact/near-zero errors without allowing tiny subnormal prices
        # to stretch the plot over hundreds of decades. Raw CSVs are untouched.
        data = [[max(r["absolute_error"], precision_floor) for r in trees if r["steps"] == n and r["status"] == "ok"]
                for n in steps]
        usable = [(n, values) for n, values in zip(steps, data) if values]
        if usable:
            axes[1].boxplot([values for _, values in usable], widths=.5)
            axes[1].set_xticks(range(1, len(usable) + 1), [str(n) for n, _ in usable])
            axes[1].set_yscale("log")
        axes[1].set(title="CRR error distribution across scenarios; convergence can oscillate",
                    xlabel="Tree steps", ylabel=f"Absolute price error (<= {precision_floor:g} shown at floor)")
        fig.suptitle("INDEPENDENT NUMERICAL VALIDATION  |  Prices checked beyond one baseline", fontsize=14, fontweight="bold")
        figures["validation.png"] = fig

        fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.5), layout="constrained")
        for method in METHODS:
            rows = [r for r in metrics if r["method"] == method]
            axes[0, 0].plot([r["scenario_id"] for r in rows], [r["coverage"] for r in rows],
                            ".", color=COLORS[method], ms=4, alpha=.7, label=method)
            regular = [r for r in rows if r["diagnostic_class"] == "regular" and r["sd_to_rms_se"] is not None]
            if regular:
                axes[0, 1].scatter([r["rms_standard_error"] for r in regular], [r["rmse"] for r in regular],
                                    s=12, alpha=.6, color=COLORS[method], label=method)
        axes[0, 0].axhline(.95, color="#334155", ls="--", lw=1)
        axes[0, 0].set(title="Raw 95% normal-CI coverage includes failures", xlabel="Scenario ID", ylabel="Fraction covering analytic reference", ylim=(-.03, 1.03))
        axes[0, 0].legend(fontsize=8)
        usable = [r for r in metrics if r["diagnostic_class"] == "regular" and r["rmse"] > precision_floor]
        if usable:
            low = min(min(r["rms_standard_error"], r["rmse"]) for r in usable)
            high = max(max(r["rms_standard_error"], r["rmse"]) for r in usable)
            axes[0, 1].plot([low, high], [low, high], "--", lw=1, color="#334155")
            axes[0, 1].set(xscale="log", yscale="log")
        axes[0, 1].set(title="Regular cells: uncertainty versus observed error", xlabel="RMS reported SE", ylabel="Empirical RMSE")
        axes[0, 1].legend(fontsize=8)
        ids = sorted({r["scenario_id"] for r in metrics})
        matrix = np.array([[next(r["zero_se_repeats"] for r in metrics if r["scenario_id"] == i and r["method"] == method)
                            for i in ids] for method in METHODS])
        heat = axes[1, 0].imshow(matrix, aspect="auto", interpolation="nearest", cmap="Oranges", vmin=0,
                                 vmax=max(1, max(r["repeats"] for r in metrics)), extent=(-.5, len(ids)-.5, 2.5, -.5))
        axes[1, 0].set_yticks(range(3), METHODS)
        axes[1, 0].set(title="No observed sample variance is retained explicitly", xlabel="Scenario ID", ylabel="Method")
        fig.colorbar(heat, ax=axes[1, 0], label="Zero-SE repeats")
        labels = ("regular", "partly_degenerate", "zero_observed_variance", "below_diagnostic_floor")
        palette = ("#008b8b", "#d0a75a", "#dd7935", "#94a3b8")
        left = np.zeros(3)
        for label, color in zip(labels, palette):
            counts = np.array([sum(r["method"] == method and r["diagnostic_class"] == label for r in metrics) for method in METHODS])
            axes[1, 1].barh(range(3), counts, left=left, color=color, label=label.replace("_", " "))
            left += counts
        axes[1, 1].set_yticks(range(3), METHODS)
        axes[1, 1].set(title="Separate interpretable uncertainty from degeneracy", xlabel="Number of scenario cells")
        axes[1, 1].legend(fontsize=7, loc="upper center", bbox_to_anchor=(.5, -.18), ncol=2)
        fig.suptitle("MONTE CARLO STRESS EVIDENCE  |  Rare payoffs and numerical floors matter\n"
                     "Raw coverage kept for every cell; Wilson intervals and classifications are in mc_metrics.csv", fontsize=13, fontweight="bold")
        figures["calibration.png"] = fig
        for figure in figures.values():
            for ax in figure.axes:
                ax.grid(alpha=.15)
    return figures
