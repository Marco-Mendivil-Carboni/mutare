#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

import shutil
import sys
from pathlib import Path

if len(sys.argv) < 2:
    sys.exit("Error: Please specify a version")

version = sys.argv[1]

for sim_type in ["asymmetric", "incremental", "symmetric"]:
    src = Path(f"sims/{sim_type}/plots")
    dest = Path(f"docs/paper/figures/{version}/{sim_type}")
    shutil.copytree(src, dest, dirs_exist_ok=True)
