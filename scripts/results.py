import msgpack
import json
from pathlib import Path
from typing import TypedDict, List, cast


class SummaryStats(TypedDict):
    mean: float
    std_dev: float
    sem: float
    is_eq: bool


class Results(TypedDict):
    prob_env: List[SummaryStats]
    avg_prob_phe: List[SummaryStats]
    n_agt_diff: List[SummaryStats]


def read_results(sim_dir: Path, run_idx: int) -> Results:
    file_path = sim_dir.joinpath(f"run-{run_idx:04}/results.msgpack")
    with file_path.open("rb") as file:
        results = msgpack.unpack(file)
    return cast(Results, results)


def print_results(sim_dir: Path, run_idx: int) -> None:
    print(json.dumps(read_results(sim_dir, run_idx), indent=2), flush=True)
