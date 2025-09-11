from multiprocessing import Pool, cpu_count
from pathlib import Path
import fcntl
import sys
from enum import Enum, auto
from typing import TypedDict, List

from .config import Config, save_config
from .runner import run_sim, RunOptions, StopRequested, print_log_msg


class SimJob(TypedDict):
    sim_dir: Path
    config: Config
    run_options: RunOptions


class JobResult(Enum):
    FINISHED = auto()
    STOPPED = auto()
    FAILED = auto()


def execute_sim_job(sim_job: SimJob) -> JobResult:
    sim_dir = sim_job["sim_dir"]

    try:
        print_log_msg(f"{sim_dir} job started")

        sim_dir.mkdir(parents=True, exist_ok=True)

        with open(sim_dir / ".lock", "w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)

            save_config(sim_job["config"], sim_dir)

            run_sim(sim_dir, sim_job["run_options"])

        print_log_msg(f"{sim_dir} job finished")
        return JobResult.FINISHED

    except StopRequested:
        print_log_msg(f"{sim_dir} job stopped")
        return JobResult.STOPPED

    except Exception as exception:
        print_log_msg(f"{sim_dir} job failed")
        print_log_msg(f"exception: {exception}")
        return JobResult.FAILED


def execute_sim_jobs(sim_jobs: List[SimJob]) -> None:
    with Pool(processes=max(1, cpu_count() // 2)) as pool:
        job_results = pool.map(execute_sim_job, sim_jobs)

    if job_results.count(JobResult.FAILED) > 0:
        sys.exit(1)

    if job_results.count(JobResult.STOPPED) > 0:
        sys.exit(0)
