import toml
from copy import deepcopy
from pathlib import Path

DEFAULT_CONFIG = {
    "n_env": 2,
    "n_phe": 2,
    "prob_env": [[0.99, 0.01], [0.01, 0.99]],
    "prob_rep": [[0.04, 0.0], [0.0, 0.03]],
    "prob_dec": [[0.0, 0.02], [0.02, 0.0]],
    "n_agt_init": 1024,
    "prob_phe_init": [0.5, 0.5],
    "std_dev_mut": 0.01,
    "steps_per_save": 4096,
    "saves_per_file": 64,
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
