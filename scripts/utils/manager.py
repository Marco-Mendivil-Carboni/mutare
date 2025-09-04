from multiprocessing import Pool
from pathlib import Path
import fcntl
import contextlib
from os import cpu_count
from typing import TypedDict, List

from .config import Config, save_config
from .runner import run_sim, RunOptions
from .results import print_all_results


class SimJob(TypedDict):
    sim_dir: Path
    config: Config
    run_options: RunOptions


def execute_sim_job(sim_job: SimJob) -> None:
    sim_job["sim_dir"].mkdir(parents=True, exist_ok=True)

    with open(sim_job["sim_dir"] / ".lock", "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (
            open(sim_job["sim_dir"] / "output.log", "w", buffering=1) as output_file,
            contextlib.redirect_stdout(output_file),
            contextlib.redirect_stderr(output_file),
        ):
            save_config(sim_job["config"], sim_job["sim_dir"])
            run_sim(sim_job["sim_dir"], sim_job["run_options"])
            print_all_results(sim_job["sim_dir"])


def execute_sim_jobs(sim_jobs: List[SimJob]):
    n_cpus = cpu_count() or 4
    n_processes = max(1, n_cpus - 4)

    with Pool(processes=n_processes) as pool:
        pool.map(execute_sim_job, sim_jobs)
