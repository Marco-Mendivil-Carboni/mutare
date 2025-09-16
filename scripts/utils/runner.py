import subprocess
from pathlib import Path
import os
from datetime import datetime
from signal import signal, SIGTERM
import json
from dataclasses import dataclass
from typing import List, Optional
from types import FrameType

from .results import read_results


def print_process_msg(message: str) -> None:
    print(f"[{datetime.now()}] [{os.getpid()}] {message}", flush=True)


class StopRequested(Exception):
    pass


stop_requested = False


def request_stop(signum: int, _: Optional[FrameType]) -> None:
    print_process_msg(f"received signal {signum}: requesting stop")

    global stop_requested
    stop_requested = True


def set_signal_handler():
    signal(SIGTERM, request_stop)


def build_bin():
    subprocess.run(["cargo", "build", "--release"], check=True)


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

        for run_idx in range(n_runs):
            results = json.dumps(read_results(sim_dir, run_idx), indent=4)
            print_process_msg(f"run {run_idx} results:\n{results}")
