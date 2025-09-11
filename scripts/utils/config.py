import toml
from pathlib import Path
import hashlib
import json
from typing import TypedDict, List, cast


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


def config_file_path(sim_dir: Path) -> Path:
    return sim_dir / "config.toml"


def save_config(config: Config, sim_dir: Path) -> None:
    with config_file_path(sim_dir).open("w") as file:
        toml.dump(config, file)


def load_config(sim_dir: Path) -> Config:
    with config_file_path(sim_dir).open("r") as file:
        config = toml.load(file)
    return cast(Config, config)


def hash_sim_dir(sim_base_dir: Path, config: Config) -> Path:
    config_str = json.dumps(config, sort_keys=True)
    config_hash = hashlib.md5(config_str.encode()).hexdigest()[:16]

    sim_dir = sim_base_dir / config_hash

    config_file = config_file_path(sim_dir)
    if config_file.exists():
        if load_config(sim_dir) != config:
            raise ValueError(f"config mismatch with {config_file}")
    else:
        sim_dir.mkdir(parents=True, exist_ok=True)
        save_config(config, sim_dir)

    return sim_dir
