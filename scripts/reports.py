import msgpack
import json
from pathlib import Path
from typing import Generator


def read_msgpacks(file_path: Path) -> Generator[dict, None, None]:
    with file_path.open("rb") as file:
        unpacker = msgpack.Unpacker(file, raw=False)
        for obj in unpacker:
            yield obj


def print_reports(sim_dir: Path, run_idx: int) -> None:
    report = sim_dir.joinpath(f"run-{run_idx:04}/reports.msgpack")
    for obj in read_msgpacks(report):
        print(json.dumps(obj, indent=2))
