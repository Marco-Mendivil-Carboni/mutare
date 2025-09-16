import msgpack
from pathlib import Path
import numpy as np
from typing import TypedDict, List, cast


class SummaryStats(TypedDict):
    mean: float
    std_dev: float
    sem: float
    is_eq: bool


class Results(TypedDict):
    growth_rate: List[SummaryStats]
    prob_extinct: List[SummaryStats]
    prob_env: List[SummaryStats]
    avg_prob_phe: List[SummaryStats]


def read_results(sim_dir: Path, run_idx: int) -> Results:
    file_path = sim_dir / f"run-{run_idx:04}/results.msgpack"
    with file_path.open("rb") as file:
        results = msgpack.unpack(file)
    return cast(Results, results)


class GrowthRate(TypedDict):  # stop using a TypedDict for this
    avg: float
    avg_err: float
    sig: float
    sig_err: float


def compute_growth_rate(sim_dir: Path, run_idx: int) -> GrowthRate:
    results = read_results(sim_dir, run_idx)
    mean = results["growth_rate"][0]["mean"]
    std_dev = results["growth_rate"][0]["std_dev"]
    sem = results["growth_rate"][0]["sem"]
    n_eff = (std_dev / sem) ** 2
    return {
        "avg": mean,
        "avg_err": sem,
        "sig": std_dev,
        "sig_err": std_dev / np.sqrt(2 * (n_eff - 1)),
    }
