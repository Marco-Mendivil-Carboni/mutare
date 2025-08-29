import toml
from copy import deepcopy
from pathlib import Path

DEFAULT_CONFIG = {
    "model": {
        "n_env": 2,
        "n_phe": 3,
        "prob_trans_env": [[0.99, 0.01], [0.01, 0.99]],
        "prob_rep": [[0.036, 0.035, 0.032], [0.015, 0.031, 0.034]],
        "prob_dec": [[0.023, 0.021, 0.021], [0.022, 0.014, 0.017]],
        "prob_mut": 0.01,
        "std_dev_mut": 1 / 16,
    },
    "init": {
        "n_agt": 1024,
        "prob_phe": [1 / 3, 1 / 3, 1 / 3],
    },
    "output": {
        "steps_per_save": 1024,
        "saves_per_file": 1024,
    },
}


def create_config(overrides: dict | None = None) -> dict:
    config = deepcopy(DEFAULT_CONFIG)
    if overrides:
        for key, value in overrides.items():
            if key in config:
                config[key].update(value)
            else:
                raise KeyError(f"Unknown config key: {key}")
    return config


def save_config(config: dict, sim_dir: str):
    filepath = Path(sim_dir).joinpath("config.toml")
    with open(filepath, "w") as file:
        toml.dump(config, file)
