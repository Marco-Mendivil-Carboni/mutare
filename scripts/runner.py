from subprocess import run
from pathlib import Path
from signal import signal, SIGTERM
from sys import exit
from typing import List, Optional
from types import FrameType

# Set up signal handling to stop gracefully

stop_requested = False


def request_stop(signum: int, _: Optional[FrameType]) -> None:
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


# Build the binary in release mode

run(["cargo", "build", "--release"])

# Helper functions to run the binary

bin = Path("target/release/mutare")


def mutare_base_args(sim_dir: Path) -> List[str]:
    return [str(bin), "--sim-dir", str(sim_dir)]


def run_mutare_command(sim_dir: Path, extra_args: List[str]) -> None:
    process = run(mutare_base_args(sim_dir) + extra_args)
    exit_if_failed(process.returncode)


def run_mutare_create(sim_dir: Path) -> None:
    run_mutare_command(sim_dir, ["create"])


def run_mutare_resume(sim_dir: Path, run_idx: int) -> None:
    run_mutare_command(sim_dir, ["resume", "--run-idx", str(run_idx)])


def run_mutare_analyze(sim_dir: Path) -> None:
    run_mutare_command(sim_dir, ["analyze"])


def run_mutare_clean(sim_dir: Path) -> None:
    run_mutare_command(sim_dir, ["clean"])


def make_sim(sim_dir: Path, n_runs: int, n_files: int, clean: bool = False) -> None:
    if clean:
        run_mutare_clean(sim_dir)

    while len(list(sim_dir.glob("run-*"))) < n_runs:
        run_mutare_create(sim_dir)

    new_sim = False
    for run_idx in range(n_runs):
        run_dir = sim_dir.joinpath(f"run-{run_idx:04}")
        while len(list(run_dir.glob("trajectory-*.msgpack"))) < n_files:
            exit_if_stopped()
            run_mutare_resume(sim_dir, run_idx)
            new_sim = True

    if new_sim:
        run_mutare_analyze(sim_dir)
