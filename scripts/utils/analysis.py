import msgpack
from pathlib import Path
import pandas as pd
from enum import Enum, auto
from typing import Any

from .exec import SimJob

OBSERVABLES = [
    "time",
    "time_step",
    "n_agents",
    "growth_rate",
    "n_extinct",
    "avg_strat_phe",
    "std_dev_strat_phe",
    "dist_strat_phe",
    "dist_phe",
]

SCALAR_OBS = [
    "time",
    "time_step",
    "n_agents",
    "growth_rate",
    "n_extinct",
    "std_dev_strat_phe",
]

MAX_ROWS = 4096

ANALYSIS = [
    "dist_n_agents",
    "growth_rate",
    "extinct_rate",
    "avg_strat_phe",
    "std_dev_strat_phe",
    "dist_strat_phe",
    "dist_phe",
]


def collect_run_time_series(sim_job: SimJob, run_idx: int) -> pd.DataFrame:
    run_time_series = []
    run_dir = sim_job.sim_dir / f"run-{run_idx:04}"
    for file_idx in range(sim_job.run_options.n_files):
        file_path = run_dir / f"output-{file_idx:04}.msgpack"
        with file_path.open("rb") as file:
            output = msgpack.Unpacker(file)
            for message in output:
                obs = {key: message[idx] for idx, key in enumerate(OBSERVABLES)}
                row = {key: obs.get(key) for key in SCALAR_OBS}
                row.update({"avg_strat_phe_0": obs["avg_strat_phe"][0]})
                row.update({"dist_phe_0": obs["dist_phe"][0]})
                run_time_series.append(row)
                if len(run_time_series) >= MAX_ROWS:
                    return pd.DataFrame(run_time_series)
    return pd.DataFrame(run_time_series)


def read_analysis(sim_dir: Path, run_idx: int) -> dict[str, Any]:
    file_path = sim_dir / f"run-{run_idx:04}" / "analysis.msgpack"
    with file_path.open("rb") as file:
        message: Any = msgpack.unpack(file)
    return {key: message[idx] for idx, key in enumerate(ANALYSIS)}


class SimType(Enum):
    RANDOM = auto()
    FIXED = auto()
    EVOL = auto()


def collect_avg_analyses(sim_jobs: list[SimJob]) -> pd.DataFrame:
    avg_analyses = []
    for sim_job in sim_jobs:
        analyses = []
        for run_idx in range(sim_job.run_options.n_runs):
            analysis = read_analysis(sim_job.sim_dir, run_idx)
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
