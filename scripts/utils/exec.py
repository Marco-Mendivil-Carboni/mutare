import subprocess
import multiprocessing as mp
from pathlib import Path
from copy import deepcopy
import os
from datetime import datetime
from signal import signal, SIGTERM
import fcntl
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional
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


def run_bin(sim_dir: Path, extra_args: list[str]) -> None:
    if stop_requested:
        raise StopRequested()

    with open(sim_dir / "output.log", "w", buffering=1) as output_file:
        args = ["target/release/mutare", "--sim-dir", str(sim_dir)] + extra_args
        subprocess.run(args, stdout=output_file, stderr=subprocess.STDOUT, check=True)


@dataclass
class RunOptions:
    n_runs: int
    n_files: int


def run_sim(sim_dir: Path, run_options: RunOptions) -> None:
    analyze = False

    n_runs = len(list(sim_dir.glob("run-*")))
    while n_runs < run_options.n_runs:
        print_process_msg(f"creating run {n_runs}")
        run_bin(sim_dir, ["create"])
        n_runs += 1

    for run_idx in range(run_options.n_runs):
        run_dir = sim_dir / f"run-{run_idx:04}"

        if not (run_dir / "analysis.msgpack").exists():
            analyze = True

        n_files = len(list(run_dir.glob("output-*")))
        while n_files < run_options.n_files:
            print_process_msg(f"resuming run {run_idx} file {n_files}")
            run_bin(sim_dir, ["resume", "--run-idx", str(run_idx)])
            analyze = True
            n_files += 1

    if analyze:
        print_process_msg("analyzing all runs")
        run_bin(sim_dir, ["analyze"])


@dataclass
class SimJob:
    base_dir: Path
    config: Config
    run_options: RunOptions

    def __post_init__(self):
        self.config = deepcopy(self.config)
        self.run_options = deepcopy(self.run_options)

    @property
    def sim_dir(self) -> Path:
        return hash_sim_dir(self.base_dir, self.config)


def create_sim_jobs(
    init_sim_job: SimJob,
    strat_phe_0_values: list[float],
    prob_mut_values: list[float],
    n_agents_values: list[int],
) -> list[SimJob]:
    base_dir = init_sim_job.base_dir
    run_options = init_sim_job.run_options

    sim_jobs = [init_sim_job]

    if init_sim_job.config["model"]["n_phe"] == 2:
        for strat_phe_0 in strat_phe_0_values:
            config = deepcopy(init_sim_job.config)
            strat_phe = [strat_phe_0, 1 - strat_phe_0]
            config["init"]["strat_phe"] = strat_phe
            sim_jobs.append(SimJob(base_dir, config, run_options))
            config["model"]["prob_mut"] = 0.0
            sim_jobs.append(SimJob(base_dir, config, run_options))

    for prob_mut in prob_mut_values:
        if prob_mut == init_sim_job.config["model"]["prob_mut"]:
            continue
        config = deepcopy(init_sim_job.config)
        config["model"]["prob_mut"] = prob_mut
        sim_jobs.append(SimJob(base_dir, config, run_options))

    for n_agents in n_agents_values:
        if n_agents == init_sim_job.config["init"]["n_agents"]:
            continue
        config = deepcopy(init_sim_job.config)
        config["init"]["n_agents"] = n_agents
        sim_jobs.append(SimJob(base_dir, config, run_options))

    return sim_jobs


class JobResult(Enum):
    FINISHED = auto()
    STOPPED = auto()
    FAILED = auto()


def execute_sim_job(sim_job: SimJob) -> JobResult:
    try:
        print_process_msg(f"starting job: {sim_job.sim_dir}")

        with open(sim_job.sim_dir / ".lock", "w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)

            run_sim(sim_job.sim_dir, sim_job.run_options)

        print_process_msg("job finished")
        return JobResult.FINISHED

    except StopRequested:
        print_process_msg("job stopped")
        return JobResult.STOPPED

    except Exception as exception:
        print_process_msg(f"job failed: {exception}")
        return JobResult.FAILED


def execute_sim_jobs(sim_jobs: list[SimJob]) -> None:
    set_signal_handler()

    build_bin()

    print_process_msg("starting process pool")

    with mp.Pool(processes=max(1, mp.cpu_count() // 2)) as pool:
        job_results = pool.map(execute_sim_job, sim_jobs)

    print_process_msg("process pool finished")

    if job_results.count(JobResult.FAILED) > 0:
        raise RuntimeError("some job failed")

    if job_results.count(JobResult.STOPPED) > 0:
        raise RuntimeError("some job was stopped")
