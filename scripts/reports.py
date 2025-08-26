#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

import msgpack
import json

file_path = "simulations/run-0000/reports.msgpack"

with open(file_path, "rb") as f:
    unpacker = msgpack.Unpacker(f, raw=False)
    for obj in unpacker:
        print(json.dumps(obj, indent=2))
