#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

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
    "std_dev_mut": 0.01,
    "steps_per_save": 4096,
    "saves_per_file": 64,
}


def create_config(overrides=None):
    config = deepcopy(DEFAULT_CONFIG)
    if overrides:
        for key, value in overrides.items():
            if key in config:
                config[key] = value
            else:
                raise KeyError(f"Unknown config key: {key}")
    return config


def save_config(config, filepath):
    with open(filepath, "w") as file:
        toml.dump(config, file)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise ValueError("You must provide one argument (directory)")

    config_file = Path(sys.argv[1]) / "config.toml"

    save_config(DEFAULT_CONFIG, config_file)
