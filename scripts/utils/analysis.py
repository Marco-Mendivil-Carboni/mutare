import msgpack
from pathlib import Path
import pandas as pd
from enum import IntEnum, auto
from typing import Any

from .exec import SimJob, print_process_msg

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

SCALAR_OBSERVABLES = [
    obs
    for obs in OBSERVABLES
    if obs not in {"avg_strat_phe", "dist_strat_phe", "dist_phe"}
]

ANALYSIS = [
    "dist_n_agents",
    "growth_rate",
    "extinct_rate",
    "avg_strat_phe",
    "std_dev_strat_phe",
    "dist_strat_phe",
    "dist_phe",
]


class SimType(IntEnum):
    FIXED = auto()
    EVOL = auto()
    RANDOM = auto()


def add_sim_info(df_or_dict: pd.DataFrame | dict[str, Any], sim_job: SimJob) -> None:
    df_or_dict["prob_mut"] = sim_job.config["model"]["prob_mut"]
    df_or_dict["n_agents_i"] = sim_job.config["init"]["n_agents"]

    strat_phe_i = sim_job.config["init"].get("strat_phe")
    if strat_phe_i is not None:
        df_or_dict["strat_phe_0_i"] = strat_phe_i[0]
        if sim_job.config["model"]["prob_mut"] == 0.0:
            df_or_dict["sim_type"] = SimType.FIXED
        else:
            df_or_dict["sim_type"] = SimType.EVOL
    else:
        df_or_dict["sim_type"] = SimType.RANDOM


def collect_run_time_series(sim_job: SimJob, run_idx: int) -> pd.DataFrame:
    run_time_series = []
    run_dir = sim_job.sim_dir / f"run-{run_idx:04}"
    last_time = 0.0
    MAX_TIME = 65_536

    for file_idx in range(sim_job.run_options.n_files):
        file_path = run_dir / f"output-{file_idx:04}.msgpack"
        with file_path.open("rb") as file:
            output = msgpack.Unpacker(file)
            for message in output:
                if last_time >= MAX_TIME:
                    break

                obs = {key: message[idx] for idx, key in enumerate(OBSERVABLES)}
                row = {key: obs.get(key) for key in SCALAR_OBSERVABLES}
                row.update({"avg_strat_phe_0": obs["avg_strat_phe"][0]})
                row.update({"dist_phe_0": obs["dist_phe"][0]})
                add_sim_info(row, sim_job)
                run_time_series.append(row)
                last_time = obs["time"]

    print_process_msg("collected 'run_time_series'")

    return pd.DataFrame(run_time_series)


def read_analysis(sim_dir: Path, run_idx: int) -> dict[str, Any]:
    file_path = sim_dir / f"run-{run_idx:04}" / "analysis.msgpack"
    with file_path.open("rb") as file:
        message: Any = msgpack.unpack(file)
    return {key: message[idx] for idx, key in enumerate(ANALYSIS)}


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
            analysis["fitness"] = (
                analysis["growth_rate"]
                - sim_job.config["init"]["n_agents"] * analysis["extinct_rate"]
            )

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

        add_sim_info(avg_analysis, sim_job)

        avg_analyses.append(avg_analysis)

    print_process_msg("collected 'avg_analyses'")

    return pd.concat(avg_analyses, ignore_index=True)
