import msgpack
import json

file_path = "Simulations/run-0000/results.bin"

with open(file_path, "rb") as f:
    unpacker = msgpack.Unpacker(f, raw=False)
    for obj in unpacker:
        print(json.dumps(obj, indent=2))
