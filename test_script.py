import msgpack
import json

file_path = "simulations/run-0000/results.msgpack"

with open(file_path, "rb") as f:
    unpacker = msgpack.Unpacker(f, raw=False)
    for obj in unpacker:
        print(json.dumps(obj, indent=2))
