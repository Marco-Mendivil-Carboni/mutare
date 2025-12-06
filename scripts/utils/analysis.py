import msgpack
from pathlib import Path
import pandas as pd
from enum import Enum, auto
from typing import TypedDict, cast

from .exec import SimJob


class Analysis(TypedDict):
    dist_n_agents: list[float]
    growth_rate: float
    extinct_rate: float
    avg_strat_phe: list[float]
    std_dev_strat_phe: float
    dist_strat_phe: list[list[float]]
    dist_phe: list[float]


def read_analysis(sim_dir: Path, run_idx: int) -> Analysis:
    file_path = sim_dir / f"run-{run_idx:04}/analysis.msgpack"
    with file_path.open("rb") as file:
        analysis = msgpack.unpack(file)
    return cast(Analysis, analysis)


class SimType(Enum):
    EVOL = auto()
    FIXED = auto()
    RANDOM = auto()


def collect_avg_analyses(sim_jobs: list[SimJob]) -> pd.DataFrame:
    avg_analyses = []
    for sim_job in sim_jobs:
        analyses = []
        for run_idx in range(sim_job.run_options.n_runs):
            analysis = read_analysis(sim_job.sim_dir, run_idx)
            analysis = cast(dict, analysis)
            for bin, ele in enumerate(analysis["dist_n_agents"]):
                analysis[f"dist_n_agents_{bin}"] = ele
            analysis.pop("dist_n_agents")
            analysis["avg_strat_phe_0"] = analysis["avg_strat_phe"][0]
            analysis.pop("avg_strat_phe")
            for bin, ele in enumerate(analysis["dist_strat_phe"][0]):
                analysis[f"dist_strat_phe_0_{bin}"] = ele
            analysis.pop("dist_strat_phe")
            analysis["dist_phe_0"] = analysis["dist_phe"][0]
            analysis.pop("dist_phe")
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

        avg_analysis["prob_mut"] = sim_job.config["model"]["prob_mut"]
        avg_analysis["n_agents"] = sim_job.config["init"]["n_agents"]

        strat_phe = sim_job.config["init"].get("strat_phe")
        if strat_phe is not None:
            avg_analysis["strat_phe_0"] = strat_phe[0]
            if sim_job.config["model"]["prob_mut"] > 0.0:
                avg_analysis["sim_type"] = SimType.EVOL
            else:
                avg_analysis["sim_type"] = SimType.FIXED
        else:
            avg_analysis["sim_type"] = SimType.RANDOM

        avg_analyses.append(avg_analysis)

    print("analyses collected")

    return pd.concat(avg_analyses, ignore_index=True)
