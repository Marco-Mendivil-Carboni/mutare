import subprocess
from pathlib import Path
from signal import signal, SIGTERM
import sys
from typing import List, Optional
from types import FrameType

# Set up signal handling to stop gracefully

stop_requested = False


def request_stop(signum: int, _: Optional[FrameType]) -> None:
    global stop_requested
    print(f"Received signal {signum}: requesting stop")
    stop_requested = True


signal(SIGTERM, request_stop)

# Build the binary in release mode

subprocess.run(["cargo", "build", "--release"])

# Helper functions to run the binary

bin_path = Path("target/release/mutare")


def run_bin(sim_dir: Path, extra_args: List[str]) -> None:
    if stop_requested:
        print("Exiting due to stop request")
        sys.exit(0)
    try:
        subprocess.run(
            [str(bin_path), "--sim-dir", str(sim_dir)] + extra_args,
            check=True,
        )
    except subprocess.CalledProcessError as error:
        print(f"Exiting due to failed command: {error.cmd}")
        sys.exit(error.returncode)


def make_sim(sim_dir: Path, n_runs: int, n_files: int, clean: bool = False) -> None:
    if clean:
        run_bin(sim_dir, ["clean"])

    while len(list(sim_dir.glob("run-*"))) < n_runs:
        run_bin(sim_dir, ["create"])

    analyze = False

    for run_idx in range(n_runs):
        run_dir = sim_dir.joinpath(f"run-{run_idx:04}")

        while len(list(run_dir.glob("trajectory-*.msgpack"))) < n_files:
            run_bin(sim_dir, ["resume", "--run-idx", str(run_idx)])
            analyze = True

        if not (run_dir / "results.msgpack").exists():
            analyze = True

    if analyze:
        run_bin(sim_dir, ["analyze"])
