import msgpack

file_path = "analysis.bin"

with open(file_path, "rb") as f:
    unpacker = msgpack.Unpacker(f, raw=False)
    for obj in unpacker:
        name, report = obj
        print(name)
        print(report)
