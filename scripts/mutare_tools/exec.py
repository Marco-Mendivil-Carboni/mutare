import subprocess
import multiprocessing as mp
from pathlib import Path
from copy import deepcopy
import psutil
import os
from datetime import datetime
from signal import signal, SIGUSR1
import fcntl
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional
from types import FrameType

from .config import Config, hash_sim_dir

N_CORES = psutil.cpu_count(logical=False)


def print_process_msg(message: str) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    print(f"[{timestamp} PID:{os.getpid()}] {message}", flush=True)


class PauseRequested(Exception):
    pass


pause_requested = False


def request_pause(signum: int, _: Optional[FrameType]) -> None:
    print_process_msg(f"received signal {signum}: requesting pause")

    global pause_requested
    pause_requested = True


def set_signal_handler():
    print_process_msg("setting signal handler")
    signal(SIGUSR1, request_pause)


def build_bin():
    print_process_msg("building binary")
    subprocess.run(["cargo", "build", "--release"], check=True, capture_output=True)


@dataclass
class SimRun:
    sim_dir: Path
    run_idx: int
    n_files: int

    @property
    def run_dir(self) -> Path:
        run_dir = self.sim_dir / f"run-{self.run_idx:04}"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir


class RunResult(Enum):
    FINISHED = auto()
    PAUSED = auto()
    FAILED = auto()


def exec_bin(sim_run: SimRun, sim_cmd: str) -> None:
    if pause_requested:
        raise PauseRequested()

    project_root = Path(__file__).resolve().parents[2]
    binary = str(project_root / "target" / "release" / "mutare")

    sim_dir = str(sim_run.sim_dir)
    run_idx = str(sim_run.run_idx)
    run_dir = sim_run.run_dir
    with open(run_dir / "output.log", "w", buffering=1) as output_file:
        args = [binary, "--sim-dir", sim_dir, "--run-idx", run_idx, sim_cmd]
        subprocess.run(args, stdout=output_file, stderr=subprocess.STDOUT, check=True)


def exec_sim_run(sim_run: SimRun):
    run_idx = sim_run.run_idx
    n_files = sim_run.n_files

    try:
        print_process_msg(f"starting run {run_idx}")

        run_dir = sim_run.run_dir
        with open(run_dir / ".lock", "w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)

            analyze = False

            if not (run_dir / "checkpoint.msgpack").exists():
                print_process_msg(f"creating run {run_idx}")
                exec_bin(sim_run, "create")
                analyze = True

            curr_n_files = len(list(run_dir.glob("output-*")))
            while curr_n_files < n_files:
                print_process_msg(f"resuming run {run_idx} ({curr_n_files})")
                exec_bin(sim_run, "resume")
                curr_n_files += 1
                analyze = True

            if not (run_dir / "analysis.msgpack").exists():
                analyze = True

            if analyze:
                print_process_msg(f"analyzing run {run_idx}")
                exec_bin(sim_run, "analyze")

        print_process_msg(f"run {run_idx} finished")
        return RunResult.FINISHED

    except PauseRequested:
        print_process_msg(f"run {run_idx} paused")
        return RunResult.PAUSED

    except Exception as exception:
        print_process_msg(f"run {run_idx} failed: {exception}")
        return RunResult.FAILED


@dataclass
class SimJob:
    base_dir: Path
    config: Config
    n_runs: int
    n_files: int

    def __post_init__(self):
        self.config = deepcopy(self.config)

    @property
    def sim_dir(self) -> Path:
        return hash_sim_dir(self.base_dir, self.config)


@dataclass
class SimsConfig:
    init_sim_job: SimJob
    strat_phe_0_i_values: list[float]
    prob_mut_values: list[float]
    n_agents_i_values: list[int]
    fixed_n_agents_i_values: list[int]


def create_sim_jobs(sims_config: SimsConfig) -> list[SimJob]:
    init_sim_job = sims_config.init_sim_job
    base_dir = sims_config.init_sim_job.base_dir
    n_runs = sims_config.init_sim_job.n_runs
    n_files = sims_config.init_sim_job.n_files

    sim_jobs = [init_sim_job]

    if init_sim_job.config["model"]["n_phe"] == 2:
        for strat_phe_0_i in sims_config.strat_phe_0_i_values:
            config = deepcopy(init_sim_job.config)
            strat_phe_i = [strat_phe_0_i, 1 - strat_phe_0_i]
            config["init"]["strat_phe"] = strat_phe_i
            sim_jobs.append(SimJob(base_dir, config, n_runs, n_files))
            config["model"]["prob_mut"] = 0.0
            sim_jobs.append(SimJob(base_dir, config, n_runs, n_files))
            for n_agents_i in sims_config.fixed_n_agents_i_values:
                if n_agents_i == init_sim_job.config["init"]["n_agents"]:
                    continue
                config["init"]["n_agents"] = n_agents_i
                sim_jobs.append(SimJob(base_dir, config, n_runs, n_files))

    for prob_mut in sims_config.prob_mut_values:
        if prob_mut == init_sim_job.config["model"]["prob_mut"]:
            continue
        config = deepcopy(init_sim_job.config)
        config["model"]["prob_mut"] = prob_mut
        sim_jobs.append(SimJob(base_dir, config, n_runs, n_files))

    for n_agents_i in sims_config.n_agents_i_values:
        if n_agents_i == init_sim_job.config["init"]["n_agents"]:
            continue
        config = deepcopy(init_sim_job.config)
        config["init"]["n_agents"] = n_agents_i
        sim_jobs.append(SimJob(base_dir, config, n_runs, n_files))

    return sim_jobs


def exec_sim_job(sim_job: SimJob) -> None:
    print_process_msg(f"starting job ({sim_job.sim_dir.name})")

    print_process_msg("starting process pool")

    sim_runs = [
        SimRun(sim_job.sim_dir, run_idx, sim_job.n_files)
        for run_idx in range(sim_job.n_runs)
    ]
    with mp.Pool(processes=N_CORES) as pool:
        run_results = pool.map(exec_sim_run, sim_runs)

    print_process_msg("process pool finished")

    if run_results.count(RunResult.FAILED) > 0:
        raise RuntimeError("some run failed")

    if run_results.count(RunResult.PAUSED) > 0:
        raise RuntimeError("some run was paused")

    print_process_msg(f"job ({sim_job.sim_dir.name}) finished")


def exec_sim_jobs(sim_jobs: list[SimJob]) -> None:
    set_signal_handler()

    build_bin()

    print_process_msg("starting jobs")

    for sim_job in sim_jobs:
        exec_sim_job(sim_job)

    print_process_msg("jobs finished")
