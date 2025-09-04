import subprocess
from pathlib import Path
from signal import signal, SIGTERM
from typing import TypedDict, List, Optional
from types import FrameType


class StopRequested(Exception):
    pass


stop_requested = False


def request_stop(signum: int, _: Optional[FrameType]) -> None:
    global stop_requested
    print(f"Received signal {signum}: requesting stop")
    stop_requested = True


# Set signal handler to stop gracefully
signal(SIGTERM, request_stop)

# Build the binary in release mode
subprocess.run(["cargo", "build", "--release"], check=True)


def run_bin(sim_dir: Path, extra_args: List[str]) -> None:
    if stop_requested:
        raise StopRequested()
    with open(sim_dir / "output.log", "w", buffering=1) as output_file:
        subprocess.run(
            ["target/release/mutare", "--sim-dir", str(sim_dir)] + extra_args,
            stdout=output_file,
            stderr=output_file,
            check=True,
        )


class RunOptions(TypedDict):
    clean: bool
    n_runs: int
    n_files: int
    analyze: bool


def run_sim(sim_dir: Path, run_options: RunOptions) -> None:
    if run_options["clean"]:
        run_bin(sim_dir, ["clean"])

    n_runs = len(list(sim_dir.glob("run-*")))
    while n_runs < run_options["n_runs"]:
        run_bin(sim_dir, ["create"])
        n_runs += 1

    for run_idx in range(run_options["n_runs"]):
        run_dir = sim_dir / f"run-{run_idx:04}"

        n_files = len(list(run_dir.glob("trajectory-*")))
        while n_files < run_options["n_files"]:
            run_bin(sim_dir, ["resume", "--run-idx", str(run_idx)])
            n_files += 1

    if run_options["analyze"]:
        run_bin(sim_dir, ["analyze"])
