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
    prob_env: List[SummaryStats]
    avg_prob_phe: List[SummaryStats]
    discrete_growth_rate: List[SummaryStats]


def read_results(sim_dir: Path, run_idx: int) -> Results:
    file_path = sim_dir / f"run-{run_idx:04}/results.msgpack"
    with file_path.open("rb") as file:
        results = msgpack.unpack(file)
    return cast(Results, results)


class GrowthRateResult(TypedDict):
    avg_W: float
    avg_W_err: float
    sig_W: float
    sig_W_err: float


def compute_growth_rate_result(sim_dir: Path, run_idx: int) -> GrowthRateResult:
    results = read_results(sim_dir, run_idx)
    mean = results["discrete_growth_rate"][0]["mean"]
    std_dev = results["discrete_growth_rate"][0]["std_dev"]
    sem = results["discrete_growth_rate"][0]["sem"]
    n_eff = (std_dev / sem) ** 2
    return {
        "avg_W": mean,
        "avg_W_err": sem,
        "sig_W": std_dev,
        "sig_W_err": std_dev / np.sqrt(2 * (n_eff - 1)),
    }
