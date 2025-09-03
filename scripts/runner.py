import subprocess
from pathlib import Path
from signal import signal, SIGTERM
import sys
import contextlib
from typing import TypedDict, List, Optional
from types import FrameType

# Set up signal handling to stop gracefully

stop_requested = False


def request_stop(signum: int, _: Optional[FrameType]) -> None:
    global stop_requested
    print(f"Received signal {signum}: requesting stop")
    stop_requested = True


signal(SIGTERM, request_stop)

# Build the binary in release mode

subprocess.run(["cargo", "build", "--release"], check=True)

# Define helper function to run the binary


def run_bin(sim_dir: Path, extra_args: List[str]) -> None:
    if stop_requested:
        print("Exiting due to stop request")
        sys.exit(0)
    try:
        subprocess.run(
            ["target/release/mutare", "--sim-dir", str(sim_dir)] + extra_args,
            check=True,
        )
    except subprocess.CalledProcessError as error:
        print(f"Exiting due to failed command: {error.cmd}")
        sys.exit(error.returncode)


class RunOptions(TypedDict):
    n_runs: int
    n_files: int
    clean: bool


def run_sim(sim_dir: Path, run_options: RunOptions) -> None:
    with (
        open(sim_dir / "output.log", "w", buffering=1) as output_file,
        contextlib.redirect_stdout(output_file),
        contextlib.redirect_stderr(output_file),
    ):
        if run_options["clean"]:
            run_bin(sim_dir, ["clean"])

        while len(list(sim_dir.glob("run-*"))) < run_options["n_runs"]:
            run_bin(sim_dir, ["create"])

        analyze = False

        for run_idx in range(run_options["n_runs"]):
            run_dir = sim_dir / f"run-{run_idx:04}"

            while len(list(run_dir.glob("trajectory-*"))) < run_options["n_files"]:
                run_bin(sim_dir, ["resume", "--run-idx", str(run_idx)])
                analyze = True

            if not (run_dir / "results.msgpack").exists():
                analyze = True

        if analyze:
            run_bin(sim_dir, ["analyze"])
