import msgpack
from pathlib import Path
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import TypedDict, List, cast

from .exec import SimJob


class SummaryStats(TypedDict):
    mean: float


class ObservableResult(TypedDict):
    shape: List[int]
    summary_stats_vec: List[SummaryStats]


class Results(TypedDict):
    time_step: ObservableResult
    growth_rate: ObservableResult
    extinction_rate: ObservableResult
    prob_env: ObservableResult
    avg_strat_phe: ObservableResult
    std_dev_strat_phe: ObservableResult


@dataclass
class NormResults:
    time_step: pd.DataFrame
    growth_rate: pd.DataFrame
    extinction_rate: pd.DataFrame
    prob_env: pd.DataFrame
    avg_strat_phe: pd.DataFrame
    # std_dev_strat_phe: pd.DataFrame

    @classmethod
    def from_results(cls, results: Results):
        def result_to_df(result: ObservableResult) -> pd.DataFrame:
            return pd.DataFrame(
                result["summary_stats_vec"],
                index=pd.MultiIndex.from_tuples(np.ndindex(tuple(result["shape"]))),
            )

        return cls(
            time_step=result_to_df(results["time_step"]),
            growth_rate=result_to_df(results["growth_rate"]),
            extinction_rate=result_to_df(results["extinction_rate"]),
            prob_env=result_to_df(results["prob_env"]),
            avg_strat_phe=result_to_df(results["avg_strat_phe"]),
            # std_dev_strat_phe=result_to_df(results["std_dev_strat_phe"]),
        )


def read_results(sim_dir: Path, run_idx: int) -> Results:
    file_path = sim_dir / f"run-{run_idx:04}/results.msgpack"
    with file_path.open("rb") as file:
        results = msgpack.unpack(file)
    return cast(Results, results)


def collect_all_scalar_results(sim_jobs: List[SimJob]) -> pd.DataFrame:
    all_scalar_results = []
    for sim_job in sim_jobs:
        for run_idx in range(sim_job.run_options.n_runs):
            norm_results = NormResults.from_results(
                read_results(sim_job.sim_dir, run_idx)
            )

            scalar_results = []
            for name, df in {
                "time_step": norm_results.time_step,
                "growth_rate": norm_results.growth_rate,
                "extinction_rate": norm_results.extinction_rate,
            }.items():
                df.columns = [name]
                scalar_results.append(df)
            scalar_results = pd.concat(scalar_results, axis=1)

            scalar_results["with_mut"] = sim_job.config["model"]["prob_mut"] > 0.0

            all_scalar_results.append(scalar_results)

    return pd.concat(all_scalar_results)
