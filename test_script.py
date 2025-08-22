import msgpack
import json

config = {
    "n_env": 2,
    "n_phe": 2,
    "prob_env": [
        [0.99, 0.01],
        [0.01, 0.99],
    ],
    "prob_rep": [
        [0.04, 0.0],
        [0.0, 0.03],
    ],
    "prob_dec": [
        [0.0, 0.02],
        [0.02, 0.0],
    ],
    "n_agt_init": 1024,
    "std_dev_mut": 0.01,
    "steps_per_save": 4096,
    "saves_per_file": 64,
}

with open("simulations/config.msgpack", "wb") as f:
    msgpack.dump(config, f)

file_path = "simulations/run-0000/reports.msgpack"

with open(file_path, "rb") as f:
    unpacker = msgpack.Unpacker(f, raw=False)
    for obj in unpacker:
        print(json.dumps(obj, indent=2))
