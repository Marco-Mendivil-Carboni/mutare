import msgpack
from pathlib import Path
import pandas as pd
from typing import TypedDict, Dict, List, cast

from .exec import SimJob


class Observables(TypedDict):
    time: float
    time_step: float
    growth_rate: float
    n_extinct: int
    avg_strat_phe: List[float]
    std_dev_strat_phe: float


def read_analysis(sim_dir: Path, run_idx: int) -> Observables:
    file_path = sim_dir / f"run-{run_idx:04}/analysis.msgpack"
    with file_path.open("rb") as file:
        analysis = msgpack.unpack(file)
    return cast(Observables, analysis)


def collect_sim_jobs_avg_analysis(sim_jobs: List[SimJob]) -> pd.DataFrame:
    sim_jobs_avg_analysis = []
    for sim_job in sim_jobs:
        job_analysis = []
        for run_idx in range(sim_job.run_options.n_runs):
            analysis = read_analysis(sim_job.sim_dir, run_idx)
            analysis = cast(Dict, analysis)
            analysis["avg_strat_phe_0"] = analysis["avg_strat_phe"][0]
            analysis.pop("avg_strat_phe")
            analysis["extinct_rate"] = analysis["n_extinct"] / analysis["time"]
            analysis.pop("n_extinct")
            analysis = pd.DataFrame(analysis, index=[run_idx])
            print(analysis)

            job_analysis.append(analysis)

        job_analysis = pd.concat(job_analysis)

        job_avg_analysis = []
        for column in job_analysis.columns:
            job_avg_analysis.append(job_analysis[column].mean())
            job_avg_analysis.append(job_analysis[column].sem())
        job_avg_analysis = pd.DataFrame([job_avg_analysis])
        job_avg_analysis.columns = pd.MultiIndex.from_product(
            [job_analysis.columns, ["mean", "sem"]]
        )

        job_avg_analysis["with_mut"] = sim_job.config["model"]["prob_mut"] > 0.0
        job_avg_analysis["strat_phe_0"] = sim_job.config["init"]["strat_phe"][0]

        sim_jobs_avg_analysis.append(job_avg_analysis)

    return pd.concat(sim_jobs_avg_analysis, ignore_index=True)
