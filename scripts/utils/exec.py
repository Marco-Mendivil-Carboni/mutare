import subprocess
import multiprocessing as mp
from pathlib import Path
from copy import deepcopy
import os
from datetime import datetime
from signal import signal, SIGTERM
import fcntl
import sys
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional
from types import FrameType

from .config import Config, hash_sim_dir


def print_process_msg(message: str) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    print(f"[{timestamp} PID:{os.getpid()}] {message}", flush=True)


class StopRequested(Exception):
    pass


stop_requested = False


def request_stop(signum: int, _: Optional[FrameType]) -> None:
    print_process_msg(f"received signal {signum}: requesting stop")

    global stop_requested
    stop_requested = True


def set_signal_handler():
    print_process_msg("setting signal handler")
    signal(SIGTERM, request_stop)


def build_bin():
    print_process_msg("building binary")
    subprocess.run(["cargo", "build", "--release"], check=True, capture_output=True)


def run_bin(sim_dir: Path, extra_args: List[str]) -> None:
    if stop_requested:
        raise StopRequested()

    with open(sim_dir / "output.log", "w", buffering=1) as output_file:
        args = ["target/release/mutare", "--sim-dir", str(sim_dir)] + extra_args
        subprocess.run(args, stdout=output_file, stderr=subprocess.STDOUT, check=True)


@dataclass
class RunOptions:
    clean: bool
    n_runs: int
    n_files: int
    analyze: bool


def run_sim(sim_dir: Path, run_options: RunOptions) -> None:
    if run_options.clean:
        print_process_msg("cleaning all runs")
        run_bin(sim_dir, ["clean"])

    n_runs = len(list(sim_dir.glob("run-*")))
    while n_runs < run_options.n_runs:
        print_process_msg(f"creating run {n_runs}")
        run_bin(sim_dir, ["create"])
        n_runs += 1

    for run_idx in range(run_options.n_runs):
        run_dir = sim_dir / f"run-{run_idx:04}"

        n_files = len(list(run_dir.glob("output-*")))
        while n_files < run_options.n_files:
            print_process_msg(f"resuming run {run_idx} file {n_files}")
            run_bin(sim_dir, ["resume", "--run-idx", str(run_idx)])
            n_files += 1

    if run_options.analyze:
        print_process_msg("analyzing all runs")
        run_bin(sim_dir, ["analyze"])


@dataclass
class SimJob:
    base_dir: Path
    config: Config
    run_options: RunOptions

    def __post_init__(self):
        self.sim_dir = hash_sim_dir(self.base_dir, self.config)
        self.config = deepcopy(self.config)
        self.run_options = deepcopy(self.run_options)


class JobResult(Enum):
    FINISHED = auto()
    STOPPED = auto()
    FAILED = auto()


def execute_sim_job(sim_job: SimJob) -> JobResult:
    try:
        print_process_msg(f"starting job:\n{sim_job}")

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

    print_process_msg("starting process pool")

    with mp.Pool(processes=max(1, mp.cpu_count() // 2)) as pool:
        job_results = pool.map(execute_sim_job, sim_jobs)

    print_process_msg("process pool finished")

    if job_results.count(JobResult.FAILED) > 0:
        print_process_msg("some job failed")
        sys.exit(1)

    if job_results.count(JobResult.STOPPED) > 0:
        print_process_msg("some job was stopped")
        sys.exit(0)
