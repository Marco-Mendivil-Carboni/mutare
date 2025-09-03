from multiprocessing import Pool
from pathlib import Path
import fcntl
from os import cpu_count
from typing import TypedDict, List

from config import Config, save_config
from runner import run_sim, RunOptions


class SimTask(TypedDict):
    sim_dir: Path
    config: Config
    run_options: RunOptions


def make_sim(sim_task: SimTask) -> None:
    sim_task["sim_dir"].mkdir(parents=True, exist_ok=True)

    with open(sim_task["sim_dir"] / ".lock", "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)

        save_config(sim_task["config"], sim_task["sim_dir"])
        run_sim(sim_task["sim_dir"], sim_task["run_options"])


def make_sims(sim_tasks: List[SimTask]):
    n_cpus = cpu_count() or 4
    n_processes = max(1, n_cpus - 4)

    with Pool(processes=n_processes) as pool:
        pool.map(make_sim, sim_tasks)
