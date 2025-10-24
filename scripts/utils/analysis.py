import msgpack
from pathlib import Path
import pandas as pd
from typing import TypedDict, Dict, List, cast

from .exec import SimJob


class Analysis(TypedDict):
    growth_rate: float
    extinct_rate: int
    avg_strat_phe: List[float]
    std_dev_strat_phe: float


def read_analysis(sim_dir: Path, run_idx: int) -> Analysis:
    file_path = sim_dir / f"run-{run_idx:04}/analysis.msgpack"
    with file_path.open("rb") as file:
        analysis = msgpack.unpack(file)
    return cast(Analysis, analysis)


def collect_avg_analyses(sim_jobs: List[SimJob]) -> pd.DataFrame:
    avg_analyses = []
    for sim_job in sim_jobs:
        analyses = []
        for run_idx in range(sim_job.run_options.n_runs):
            analysis = read_analysis(sim_job.sim_dir, run_idx)
            analysis = cast(Dict, analysis)
            analysis["avg_strat_phe_0"] = analysis["avg_strat_phe"][0]
            analysis.pop("avg_strat_phe")
            analysis = pd.DataFrame(analysis, index=[run_idx])

            analyses.append(analysis)

        analyses = pd.concat(analyses)

        avg_analysis = []
        for column in analyses.columns:
            avg_analysis.append(analyses[column].mean())
            avg_analysis.append(analyses[column].sem())
        avg_analysis = pd.DataFrame([avg_analysis])
        avg_analysis.columns = pd.MultiIndex.from_product(
            [analyses.columns, ["mean", "sem"]]
        )

        avg_analysis["with_mut"] = sim_job.config["model"]["prob_mut"] > 0.0
        avg_analysis["strat_phe_0"] = sim_job.config["init"]["strat_phe"][0]

        avg_analyses.append(avg_analysis)

    return pd.concat(avg_analyses, ignore_index=True)
