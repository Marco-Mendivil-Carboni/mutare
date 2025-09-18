import msgpack
from pathlib import Path
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import TypedDict, List, Callable, cast


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


@dataclass
class NormResults:
    norm_growth_rate: pd.DataFrame
    rate_extinct: pd.DataFrame
    prob_env: pd.DataFrame
    avg_prob_phe: pd.DataFrame

    @classmethod
    def from_results(cls, results: Results, time_step: float):
        def normalize_num_cols(
            df: pd.DataFrame, func: Callable[[pd.DataFrame], pd.DataFrame]
        ) -> pd.DataFrame:
            num_cols = df.select_dtypes(include="number").columns
            df[num_cols] = func(df[num_cols])
            return df

        return cls(
            norm_growth_rate=normalize_num_cols(
                pd.DataFrame(results["growth_rate"]), lambda x: x / time_step
            ),
            rate_extinct=normalize_num_cols(
                pd.DataFrame(results["prob_extinct"]),
                lambda x: -cast(pd.DataFrame, np.log(1.0 - x)) / time_step,
            ),
            prob_env=pd.DataFrame(results["prob_env"]),
            avg_prob_phe=pd.DataFrame(results["avg_prob_phe"]),
        )


def read_results(sim_dir: Path, run_idx: int) -> Results:
    file_path = sim_dir / f"run-{run_idx:04}/results.msgpack"
    with file_path.open("rb") as file:
        results = msgpack.unpack(file)
    return cast(Results, results)
