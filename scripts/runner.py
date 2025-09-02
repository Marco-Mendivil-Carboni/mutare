import subprocess
from pathlib import Path
from signal import signal, SIGTERM
import sys
import os
from tempfile import NamedTemporaryFile
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


def exit_if_stop_requested() -> None:
    if stop_requested:
        print("Exiting due to stop request")
        sys.exit(0)


# Build the binary in release mode

subprocess.run(["cargo", "build", "--release"])

# Helper functions to run the binary

bin_path = Path("target/release/mutare")


def run_command(sim_dir: Path, extra_args: List[str]) -> None:
    with NamedTemporaryFile(mode="w+", suffix=".log", dir=".") as tmp_file:
        try:
            subprocess.run(
                [str(bin_path), "--sim-dir", str(sim_dir)] + extra_args,
                stdout=tmp_file,
                stderr=subprocess.STDOUT,
                check=True,
            )
        except subprocess.CalledProcessError as error:
            tmp_file.flush()
            tmp_file.seek(0)
            print(f"Command failed. output:\n{tmp_file.read()}")
            sys.exit(error.returncode)


def make_sim(sim_dir: Path, n_runs: int, n_files: int, clean: bool = False) -> None:
    if clean:
        run_command(sim_dir, ["clean"])

    while len(list(sim_dir.glob("run-*"))) < n_runs:
        run_command(sim_dir, ["create"])

    new_sim = False
    for run_idx in range(n_runs):
        run_dir = sim_dir.joinpath(f"run-{run_idx:04}")
        while len(list(run_dir.glob("trajectory-*.msgpack"))) < n_files:
            exit_if_stop_requested()
            run_command(sim_dir, ["resume", "--run-idx", str(run_idx)])
            new_sim = True

    if new_sim:
        run_command(sim_dir, ["analyze"])
