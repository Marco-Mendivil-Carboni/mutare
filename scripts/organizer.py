from multiprocessing import Pool
from pathlib import Path
import sys
import os
import fcntl
from typing import TypedDict, List

from config import Config, save_config
from runner import run_sim, RunOptions
from results import print_all_results


class SimTask(TypedDict):
    sim_dir: Path
    config: Config
    run_options: RunOptions


def make_sim(sim_task: SimTask) -> None:
    lock_file_path = sim_task["sim_dir"] / ".lock"
    with open(lock_file_path, "w") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"Another process is already using {sim_task['sim_dir']}")
            sys.exit(1)
        try:
            sim_task["sim_dir"].mkdir(parents=True, exist_ok=True)
            save_config(sim_task["config"], sim_task["sim_dir"])
            run_sim(sim_task["sim_dir"], sim_task["run_options"])
            print_all_results(sim_task["sim_dir"])
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def make_sims(sim_tasks: List[SimTask]):
    n_cpus = os.cpu_count() or 4
    n_processes = max(1, n_cpus - 4)

    with Pool(processes=n_processes) as pool:
        pool.map(make_sim, sim_tasks)
