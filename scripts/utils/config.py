import toml
from pathlib import Path
import numpy as np
from scipy.linalg import expm
import hashlib
import json
from dataclasses import dataclass
from typing import TypedDict, List, NotRequired, cast


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
    steps_per_file: int
    steps_per_save: NotRequired[int]


class Config(TypedDict):
    model: ModelParams
    init: InitParams
    output: OutputParams


@dataclass
class NormModelParams:
    n_env: int
    n_phe: int
    rate_trans_env: List[List[float]]
    rate_rep: List[List[float]]
    rate_dec: List[List[float]]
    rate_mut: float
    std_dev_mut: float
    time_step: float

    def to_model_params(self) -> ModelParams:
        return {
            "n_env": self.n_env,
            "n_phe": self.n_phe,
            "prob_trans_env": cast(
                List[List[float]],
                expm(np.array(self.rate_trans_env) * self.time_step).tolist(),
            ),
            "prob_rep": (
                1.0 - np.exp(-np.array(self.rate_rep) * self.time_step)
            ).tolist(),
            "prob_dec": (
                1.0 - np.exp(-np.array(self.rate_dec) * self.time_step)
            ).tolist(),
            "prob_mut": float(1.0 - np.exp(-self.rate_mut * self.time_step)),
            "std_dev_mut": self.std_dev_mut,
        }


def config_file_path(sim_dir: Path) -> Path:
    return sim_dir / "config.toml"


def save_config(config: Config, sim_dir: Path) -> None:
    with config_file_path(sim_dir).open("w") as file:
        toml.dump(config, file)


def load_config(sim_dir: Path) -> Config:
    with config_file_path(sim_dir).open("r") as file:
        config = toml.load(file)
    return cast(Config, config)


def hash_sim_dir(base_dir: Path, config: Config) -> Path:
    config_str = json.dumps(config, sort_keys=True)
    config_hash = hashlib.sha256(config_str.encode()).hexdigest()

    sim_dir = base_dir / config_hash

    config_file = config_file_path(sim_dir)
    if config_file.exists():
        if load_config(sim_dir) != config:
            raise ValueError(f"config mismatch with {config_file}")
    else:
        sim_dir.mkdir(parents=True, exist_ok=True)
        save_config(config, sim_dir)

    return sim_dir
