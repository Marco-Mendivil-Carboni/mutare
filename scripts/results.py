import msgpack
import json
from pathlib import Path
from typing import Generator


def read_results(sim_dir: Path, run_idx: int) -> Generator[dict, None, None]:
    results = sim_dir.joinpath(f"run-{run_idx:04}/results.msgpack")
    with results.open("rb") as file:
        results = msgpack.unpack(file)
    return results


def print_results(sim_dir: Path, run_idx: int) -> None:
    print(json.dumps(read_results(sim_dir, run_idx), indent=2))
