import msgpack
from pathlib import Path
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import TypedDict, List, Callable, cast

from .config import load_config
from .runner import SimJob


class SummaryStats(TypedDict):
    mean: float
    std_dev: float
    sem: float
    is_eq: bool


class ObservableResult(TypedDict):
    shape: List[int]
    stats_vec: List[SummaryStats]


class Results(TypedDict):
    growth_rate: ObservableResult
    prob_extinct: ObservableResult
    prob_env: ObservableResult
    avg_prob_phe: ObservableResult


@dataclass
class NormResults:
    norm_growth_rate: pd.DataFrame
    rate_extinct: pd.DataFrame
    prob_env: pd.DataFrame
    avg_prob_phe: pd.DataFrame

    @classmethod
    def from_results(cls, results: Results, time_step: float):
        def result_to_df(result: ObservableResult) -> pd.DataFrame:
            return pd.DataFrame(
                result["stats_vec"],
                index=pd.MultiIndex.from_tuples(np.ndindex(tuple(result["shape"]))),
            )

        def normalize_num_cols(
            df: pd.DataFrame, norm_func: Callable[[pd.DataFrame], pd.DataFrame]
        ) -> pd.DataFrame:
            num_cols = df.select_dtypes(include="number").columns
            df[num_cols] = norm_func(df[num_cols])
            return df

        return cls(
            norm_growth_rate=normalize_num_cols(
                result_to_df(results["growth_rate"]), lambda x: x / time_step
            ),
            rate_extinct=normalize_num_cols(
                result_to_df(results["prob_extinct"]),
                lambda x: -cast(pd.DataFrame, np.log(1.0 - x)) / time_step,
            ),
            prob_env=result_to_df(results["prob_env"]),
            avg_prob_phe=result_to_df(results["avg_prob_phe"]),
        )


def read_results(sim_dir: Path, run_idx: int) -> Results:
    file_path = sim_dir / f"run-{run_idx:04}/results.msgpack"
    with file_path.open("rb") as file:
        results = msgpack.unpack(file)
    return cast(Results, results)


def collect_all_scalar_results(
    sim_jobs: List[SimJob], time_step: float
) -> pd.DataFrame:
    all_scalar_results = []
    for sim_job in sim_jobs:
        for run_idx in range(sim_job.run_options.n_runs):
            norm_results = NormResults.from_results(
                read_results(sim_job.sim_dir, run_idx), time_step
            )

            scalar_results = []
            for name, df in {
                "norm_growth_rate": norm_results.norm_growth_rate,
                "rate_extinct": norm_results.rate_extinct,
            }.items():
                df.columns = pd.MultiIndex.from_product([[name], df.columns])
                scalar_results.append(df)

            scalar_results = pd.concat(scalar_results, axis=1)

            scalar_results["with_mut"] = (
                load_config(sim_job.sim_dir)["model"]["prob_mut"] > 0.0
            )

            all_scalar_results.append(scalar_results)

    return pd.concat(all_scalar_results)
