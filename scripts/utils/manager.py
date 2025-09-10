from multiprocessing import Pool, cpu_count
from pathlib import Path
import fcntl
import os
import sys
from enum import Enum, auto
from typing import TypedDict, List

from .config import Config, save_config
from .runner import run_sim, RunOptions, StopRequested
from .results import print_all_results


class SimJob(TypedDict):
    sim_dir: Path
    config: Config
    run_options: RunOptions


class JobResult(Enum):
    FINISHED = auto()
    STOPPED = auto()
    FAILED = auto()


def execute_sim_job(sim_job: SimJob) -> JobResult:
    pid = os.getpid()
    sim_dir = sim_job["sim_dir"]

    try:
        print(f"[{pid}] {sim_dir} job started", flush=True)

        sim_dir.mkdir(parents=True, exist_ok=True)

        with open(sim_dir / ".lock", "w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)

            save_config(sim_job["config"], sim_dir)

            run_sim(sim_dir, sim_job["run_options"])

        print(f"[{pid}] {sim_dir} job finished", flush=True)
        if sim_job["run_options"]["analyze"]:
            print_all_results(sim_dir)
        return JobResult.FINISHED

    except StopRequested:
        print(f"[{pid}] {sim_dir} job stopped", flush=True)
        return JobResult.STOPPED

    except Exception as exception:
        print(f"[{pid}] {sim_dir} job failed", flush=True)
        print(f"[{pid}] exception: {exception}", flush=True)
        return JobResult.FAILED


def execute_sim_jobs(sim_jobs: List[SimJob]) -> None:
    with Pool(processes=max(1, cpu_count() // 2)) as pool:
        job_results = pool.map(execute_sim_job, sim_jobs)

    if job_results.count(JobResult.FAILED) > 0:
        sys.exit(1)

    if job_results.count(JobResult.STOPPED) > 0:
        sys.exit(0)
