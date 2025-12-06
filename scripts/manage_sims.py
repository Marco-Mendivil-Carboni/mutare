#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
import subprocess
import sys

MAIN_SCRIPT = Path("scripts/make_all_sims.py").resolve()
LOG_FILE = Path("sims/output.log").resolve()


def sims_running() -> bool:
    try:
        subprocess.check_output(["pgrep", "-f", str(MAIN_SCRIPT)])
        return True
    except subprocess.CalledProcessError:
        return False


def ask_bool(question: str) -> bool:
    while True:
        ans = input(question + " [y/n]: ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'.")


def start_sims():
    if sims_running():
        print("Simulations are already running.")
        return

    print("Start simulations:")
    notify = ask_bool("Send Telegram notifications?")
    clean = ask_bool("Prune stale simulation directories?")
    command = [str(MAIN_SCRIPT)]
    if notify:
        command.append("--notify")
    if clean:
        command.append("--clean")
    with LOG_FILE.open("w") as log_file:
        subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    print("Started simulations in the background.")


def stop_sims():
    if not sims_running():
        print("No simulations are running.")
        return

    subprocess.run(["pkill", "-f", str(MAIN_SCRIPT)])

    print("Simulations stopped.")


def check_status():
    print("Simulations status:")
    if sims_running():
        print("Simulations are currently RUNNING.")
    else:
        print("Simulations are NOT running.")
    if LOG_FILE.exists():
        print("Last log file lines:")
        subprocess.run(["tail", str(LOG_FILE)])
    else:
        print("No log file found.")


def manage_sims():
    while True:
        print("""
---------------------------
    Simulations Manager
---------------------------
  +1) Start simulations
  +2) Stop simulations
  +3) Check status
  +4) Exit
""")
        choice = input("Choose an option [1-4]: ").strip()
        if choice == "1":
            start_sims()
        elif choice == "2":
            stop_sims()
        elif choice == "3":
            check_status()
        elif choice == "4":
            sys.exit(0)
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    manage_sims()
