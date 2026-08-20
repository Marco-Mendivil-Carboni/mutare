#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

import shutil
import sys
from pathlib import Path

if len(sys.argv) < 2:
    sys.exit("Please specify a destination directory")

dest_dir = sys.argv[1]

for sim_type in ["asymmetric", "incremental", "symmetric"]:
    src = Path(f"sims/{sim_type}/plots")
    dest = Path(f"{dest_dir}/{sim_type}")
    shutil.copytree(src, dest, dirs_exist_ok=True)
