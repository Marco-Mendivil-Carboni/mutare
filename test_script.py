import msgpack
import json

file_path = "Simulations/analysis-000.bin"

with open(file_path, "rb") as f:
    unpacker = msgpack.Unpacker(f, raw=False)
    for obj in unpacker:
        print(json.dumps(obj, indent=2))
