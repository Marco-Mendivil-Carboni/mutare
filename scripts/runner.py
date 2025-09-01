from subprocess import run
from pathlib import Path
from signal import signal, SIGTERM
from sys import exit
from typing import List, Optional
from types import FrameType

# Signal handling to stop gracefully

stop_requested = False


def request_stop(signum: int, frame: Optional[FrameType]) -> None:
    global stop_requested
    print(f"Received signal {signum}, requesting stop...")
    stop_requested = True


signal(SIGTERM, request_stop)

# Helper exit functions


def exit_if_stopped() -> None:
    if stop_requested:
        print("Exiting due to stop request")
        exit(0)


def exit_if_failed(returncode: int) -> None:
    if returncode != 0:
        print(f"Exiting due to return code {returncode}")
        exit(returncode)


# Build the Rust project in release mode

run(["cargo", "build", "--release"])

# Path to the mutare binary

bin = Path("target/release/mutare")

# Helper mutare functions


def mutare_base_args(sim_dir: Path) -> List[str]:
    return [str(bin), "--sim-dir", str(sim_dir)]


def mutare_create(sim_dir: Path) -> None:
    process = run(mutare_base_args(sim_dir) + ["create"])
    exit_if_failed(process.returncode)


def mutare_resume(sim_dir: Path, run_idx: int) -> None:
    run_idx_args = ["--run-idx", str(run_idx)]
    process = run(mutare_base_args(sim_dir) + ["resume"] + run_idx_args)
    exit_if_failed(process.returncode)


def mutare_analyze(sim_dir: Path) -> None:
    process = run(mutare_base_args(sim_dir) + ["analyze"])
    exit_if_failed(process.returncode)


def mutare_clean(sim_dir: Path) -> None:
    process = run(mutare_base_args(sim_dir) + ["clean"])
    exit_if_failed(process.returncode)


def mutare_make_sim(sim_dir: Path, n_runs: int, n_files: int) -> None:
    mutare_clean(sim_dir)

    for run_idx in range(n_runs):
        exit_if_stopped()
        mutare_create(sim_dir)

        for _ in range(n_files):
            exit_if_stopped()
            mutare_resume(sim_dir, run_idx)

    exit_if_stopped()
    mutare_analyze(sim_dir)
