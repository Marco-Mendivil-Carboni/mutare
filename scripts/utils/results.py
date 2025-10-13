import msgpack
from pathlib import Path
import numpy as np
import pandas as pd
from typing import TypedDict, List, cast

from .exec import SimJob


class ObservableResult(TypedDict):
    shape: List[int]
    average_vec: List[float]


class Results(TypedDict):
    time_step: ObservableResult
    rel_diff_n_agents: ObservableResult
    prob_extinct: ObservableResult
    prob_env: ObservableResult
    avg_strat_phe: ObservableResult
    std_dev_strat_phe: ObservableResult


def read_results(sim_dir: Path, run_idx: int) -> Results:
    file_path = sim_dir / f"run-{run_idx:04}/results.msgpack"
    with file_path.open("rb") as file:
        results = msgpack.unpack(file)
    return cast(Results, results)


def convert_to_df(result: ObservableResult) -> pd.DataFrame:
    return pd.DataFrame(
        result["average_vec"],
        index=pd.MultiIndex.from_tuples(np.ndindex(tuple(result["shape"]))),
        columns=["average"],
    )


def collect_sim_jobs_results(sim_jobs: List[SimJob]) -> pd.DataFrame:
    sim_jobs_results = []
    for sim_job in sim_jobs:
        job_results = []
        for run_idx in range(sim_job.run_options.n_runs):
            results = read_results(sim_job.sim_dir, run_idx)
            results = {
                name: convert_to_df(cast(ObservableResult, result))
                for name, result in results.items()
            }
            results = pd.DataFrame(
                {
                    "growth_rate": results["rel_diff_n_agents"]["average"]
                    / results["time_step"]["average"],
                    "extinct_rate": results["prob_extinct"]["average"]
                    / results["time_step"]["average"],
                    "std_dev_strat_phe": results["std_dev_strat_phe"]["average"],
                }
            )

            job_results.append(results)

        job_results = pd.concat(job_results)
        job_results = pd.DataFrame(
            {"mean": job_results.mean(), "sem": job_results.sem()}
        ).transpose()

        job_results["with_mut"] = sim_job.config["model"]["prob_mut"] > 0.0

        sim_jobs_results.append(job_results)

    return pd.concat(sim_jobs_results)
