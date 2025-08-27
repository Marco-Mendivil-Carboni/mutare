import subprocess
from pathlib import Path

bin = Path("target/release/mutare")


def mutare_create(sim_dir):
    return subprocess.run([str(bin), "--sim-dir", str(sim_dir), "create"])


def mutare_resume(sim_dir: Path, run_idx: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(bin), "--sim-dir", str(sim_dir), "resume", "--run-idx", str(run_idx)]
    )


def mutare_analyze(sim_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run([str(bin), "--sim-dir", str(sim_dir), "analyze"])


def mutare_clean(sim_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run([str(bin), "--sim-dir", str(sim_dir), "clean"])
