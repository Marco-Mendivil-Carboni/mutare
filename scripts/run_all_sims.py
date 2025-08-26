#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from config import create_config, save_config
from runner import mutare_create, mutare_resume, mutare_analyze
from reports import print_reports
from pathlib import Path

sim_dir = Path("simulations")

sim_dir.mkdir(parents=True, exist_ok=True)

config = create_config()

save_config(config, sim_dir)

mutare_create(sim_dir)
mutare_create(sim_dir)

mutare_resume(sim_dir, 0)
mutare_resume(sim_dir, 0)

mutare_resume(sim_dir, 1)
mutare_resume(sim_dir, 1)

mutare_analyze(sim_dir)

print_reports(sim_dir, 0)
print_reports(sim_dir, 1)
