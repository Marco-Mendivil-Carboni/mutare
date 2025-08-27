import msgpack
import json
from pathlib import Path
from typing import Generator


def read_reports(sim_dir: Path, run_idx: int) -> Generator[dict, None, None]:
    reports = sim_dir.joinpath(f"run-{run_idx:04}/reports.msgpack")
    with reports.open("rb") as file:
        unpacker = msgpack.Unpacker(file, raw=False)
        for obj in unpacker:
            yield obj


def print_reports(sim_dir: Path, run_idx: int) -> None:
    for obj in read_reports(sim_dir, run_idx):
        print(json.dumps(obj, indent=2))
