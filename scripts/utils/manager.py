import multiprocessing as mp
from pathlib import Path
import fcntl
import sys
from dataclasses import dataclass
from enum import Enum, auto
from typing import List

from .config import Config, hash_sim_dir
from .runner import (
    print_process_msg,
    StopRequested,
    set_signal_handler,
    build_bin,
    RunOptions,
    run_sim,
)


@dataclass
class SimJob:
    sim_dir: Path
    run_options: RunOptions

    @classmethod
    def from_config(cls, base_dir: Path, config: Config, run_options: RunOptions):
        return cls(sim_dir=hash_sim_dir(base_dir, config), run_options=run_options)


class JobResult(Enum):
    FINISHED = auto()
    STOPPED = auto()
    FAILED = auto()


def execute_sim_job(sim_job: SimJob) -> JobResult:
    try:
        print_process_msg(f"job started: {sim_job.sim_dir}")

        with open(sim_job.sim_dir / ".lock", "w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)

            run_sim(sim_job.sim_dir, sim_job.run_options)

        print_process_msg("job finished")
        return JobResult.FINISHED

    except StopRequested:
        print_process_msg("job stopped")
        return JobResult.STOPPED

    except Exception as exception:
        print_process_msg(f"job failed:\n{exception}")
        return JobResult.FAILED


def execute_sim_jobs(sim_jobs: List[SimJob]) -> None:
    set_signal_handler()

    build_bin()

    with mp.Pool(processes=max(1, mp.cpu_count() // 2)) as pool:
        job_results = pool.map(execute_sim_job, sim_jobs)

    print("simulation jobs have terminated")

    if job_results.count(JobResult.FAILED) > 0:
        sys.exit(1)

    if job_results.count(JobResult.STOPPED) > 0:
        sys.exit(0)
