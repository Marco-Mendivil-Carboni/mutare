import toml
from pathlib import Path
from typing import TypedDict, List


class ModelParams(TypedDict):
    n_env: int
    n_phe: int
    prob_trans_env: List[List[float]]
    prob_rep: List[List[float]]
    prob_dec: List[List[float]]
    prob_mut: float
    std_dev_mut: float


class InitParams(TypedDict):
    n_agt: int
    prob_phe: List[float]


class OutputParams(TypedDict):
    steps_per_save: int
    saves_per_file: int


class Config(TypedDict):
    model: ModelParams
    init: InitParams
    output: OutputParams


DEFAULT_CONFIG: Config = {
    "model": {
        "n_env": 2,
        "n_phe": 2,
        "prob_trans_env": [[0.990, 0.010], [0.008, 0.992]],
        "prob_rep": [[0.012, 0.000], [0.000, 0.008]],
        "prob_dec": [[0.000, 0.016], [0.012, 0.000]],
        "prob_mut": 0.0001,
        "std_dev_mut": 0.1,
    },
    "init": {
        "n_agt": 256,
        "prob_phe": [0.5, 0.5],
    },
    "output": {
        "steps_per_save": 4096,
        "saves_per_file": 256,
    },
}


def save_config(config: Config, sim_dir: Path) -> None:
    file_path = sim_dir / "config.toml"
    with file_path.open("w") as file:
        toml.dump(config, file)
