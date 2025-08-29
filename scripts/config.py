import toml
from copy import deepcopy
from pathlib import Path

DEFAULT_CONFIG = {
    "model": {
        "n_env": 2,
        "n_phe": 2,
        "prob_trans_env": [[0.999, 0.001], [0.001, 0.999]],
        "prob_rep": [[0.0016, 0.0], [0.0, 0.0004]],
        "prob_dec": [[0.0, 0.0010], [0.0010, 0.0]],
        "prob_mut": 0.0002,
        "std_dev_mut": 0.08,
    },
    "init": {
        "n_agt": 1024,
        "prob_phe": [0.5, 0.5],
    },
    "output": {
        "steps_per_save": 1024,
        "saves_per_file": 512,
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
