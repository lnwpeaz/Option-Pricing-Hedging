"""Explicit benchmark boundaries: kernel-only versus complete batched pricing."""

import math
from time import perf_counter
import tracemalloc

import numpy as np

from option_hedging.contracts import OptionSpec
from option_hedging.pricing.monte_carlo import price
from option_hedging.simulation.gbm import terminal_from_normals


def scalar_payoff_mean(spec: OptionSpec, normals: np.ndarray) -> float:
    """Pedagogical Python loop; samples already exist, no RNG or sample SE."""
    location = math.log(spec.spot) + (spec.risk_free_rate - .5 * spec.volatility ** 2) * spec.maturity_years
    scale = spec.volatility * math.sqrt(spec.maturity_years)
    discount = math.exp(-spec.risk_free_rate * spec.maturity_years)
    total = 0.0
    for z in normals:
        terminal = math.exp(location + scale * float(z))
        total += discount * max(terminal - spec.strike if spec.kind == "call"
                                else spec.strike - terminal, 0.0)
    return total / len(normals)


def vector_payoff_mean(spec: OptionSpec, normals: np.ndarray) -> float:
    """Same payoff work as scalar; vectorization includes array validation/allocation."""
    terminal = terminal_from_normals(spot=spec.spot, drift=spec.risk_free_rate,
                                    volatility=spec.volatility,
                                    maturity_years=spec.maturity_years, normals=normals)
    payoff = np.maximum(terminal - spec.strike if spec.kind == "call"
                        else spec.strike - terminal, 0.0)
    return float(np.mean(payoff * math.exp(-spec.risk_free_rate * spec.maturity_years)))


def run_benchmarks(spec: OptionSpec, *, n_paths: int, batch_sizes: list[int],
                   repeats: int, seed: int) -> tuple[list[dict], list[dict]]:
    """Warm up, alternate order, retain all timings; memory pass is separate.

    traced_peak_bytes is Python/NumPy traced allocation, not process RSS. The
    pre-generated normals live outside kernel timings; complete pricing includes
    sampling, validation, payoff, and uncertainty, but excludes RNG construction.
    """
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([9, seed])))
    normals = rng.standard_normal(n_paths)
    functions = {"scalar": scalar_payoff_mean, "vectorized": vector_payoff_mean}
    expected = vector_payoff_mean(spec, normals)
    for function in functions.values():
        if not math.isclose(function(spec, normals), expected, rel_tol=1e-11, abs_tol=1e-11):
            raise ValueError("Scalar/vector benchmark kernels disagree")
    kernels = []
    for repeat in range(repeats):
        order = ("scalar", "vectorized") if repeat % 2 == 0 else ("vectorized", "scalar")
        for name in order:
            start = perf_counter()
            value = functions[name](spec, normals)
            elapsed = perf_counter() - start
            kernels.append(dict(implementation=name, repeat=repeat, n_paths=n_paths,
                                price=value, elapsed_seconds=elapsed,
                                paths_per_second=n_paths / max(elapsed, 1e-12)))
    batches = []
    for batch in batch_sizes:
        # Warm up each batch policy before recording it.
        price(spec, n_paths=n_paths, rng=np.random.Generator(np.random.PCG64(seed)), batch_size=batch)
    for repeat in range(repeats):
        order = batch_sizes if repeat % 2 == 0 else batch_sizes[::-1]
        for batch in order:
            rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([10, repeat, seed])))
            start = perf_counter()
            result = price(spec, n_paths=n_paths, rng=rng, batch_size=batch)
            elapsed = perf_counter() - start
            batches.append(dict(batch_size=batch, repeat=repeat, n_paths=n_paths,
                                price=result.price, standard_error=result.standard_error,
                                elapsed_seconds=elapsed, paths_per_second=n_paths / max(elapsed, 1e-12)))
    if tracemalloc.is_tracing():
        raise RuntimeError("Allocation benchmark requires tracemalloc to be initially off")
    peaks = {}
    for batch in batch_sizes:
        rng = np.random.Generator(np.random.PCG64(seed))
        tracemalloc.start()
        try:
            price(spec, n_paths=n_paths, rng=rng, batch_size=batch)
            peaks[batch] = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
    for row in batches:
        row["traced_peak_bytes"] = peaks[row["batch_size"]]
    return kernels, batches
