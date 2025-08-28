import toml
from copy import deepcopy
from pathlib import Path

DEFAULT_CONFIG = {
    "n_env": 2,
    "n_phe": 3,
    "prob_env": [[0.999, 0.001], [0.001, 0.999]],
    "prob_rep": [[0.0036, 0.0035, 0.0032], [0.0015, 0.0031, 0.0034]],
    "prob_dec": [[0.0023, 0.0021, 0.0021], [0.0022, 0.0014, 0.0017]],
    "n_agt_init": 1024,
    "prob_phe_init": [1 / 3, 1 / 3, 1 / 3],
    "std_dev_mut": 0.01,
    "steps_per_save": 1024,
    "saves_per_file": 1024,
}


def create_config(overrides: dict | None = None) -> dict:
    config = deepcopy(DEFAULT_CONFIG)
    if overrides:
        for key, value in overrides.items():
            if key in config:
                config[key] = value
            else:
                raise KeyError(f"Unknown config key: {key}")
    return config


def save_config(config: dict, sim_dir: str):
    filepath = Path(sim_dir).joinpath("config.toml")
    with open(filepath, "w") as file:
        toml.dump(config, file)
