#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
import subprocess
from shutil import rmtree
import psutil
from textual import on, work
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container
from textual.widgets import Label, ProgressBar, Button, Static, Log, Header, Footer

from utils.exec import SimJob, create_sim_jobs

from sims_configs import SIMS_DIR, SIMS_CONFIGS

MAKE_ALL_SIMS = Path(__file__).resolve().parent / "make_all_sims.py"
LOG_FILE = SIMS_DIR / "output.log"


def sims_running() -> list[int]:
    pids = []
    for process in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = process.info["cmdline"]
            if cmdline and any(MAKE_ALL_SIMS.name in arg for arg in cmdline):
                pids.append(process.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return pids


def generate_expected_paths() -> set[Path]:
    expected_paths = {SIMS_DIR / "output.log"}
    for sims_config in SIMS_CONFIGS:
        sim_jobs = create_sim_jobs(sims_config)
        base_dir = sims_config.init_sim_job.base_dir
        expected_paths.add(base_dir)
        run_options = sims_config.init_sim_job.run_options
        sim_dirs = {sim_job.sim_dir.resolve() for sim_job in sim_jobs}
        for sim_dir in sim_dirs:
            expected_paths.add(sim_dir)
            for run_idx in range(run_options.n_runs):
                run_dir = sim_dir / f"run-{run_idx:04}"
                expected_paths.add(run_dir)
                expected_paths.add(run_dir / "analysis.msgpack")
                expected_paths.add(run_dir / "checkpoint.msgpack")
                for file_idx in range(run_options.n_files):
                    expected_paths.add(run_dir / f"output-{file_idx:04}.msgpack")
            expected_paths.add(sim_dir / ".lock")
            expected_paths.add(sim_dir / "config.toml")
            expected_paths.add(sim_dir / "output.log")
        expected_paths.add(base_dir / "plots")
        expected_paths.union(
            {path for path in (base_dir / "plots").rglob("*") if path.is_file()}
        )

    return expected_paths


class DialogScreen(ModalScreen[bool]):
    def __init__(self, question: str) -> None:
        self.question = question
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Container(
            Label(self.question),
            Button("Yes", id="yes", variant="success"),
            Button("No", id="no", variant="error"),
            id="dialog-box",
        )

    @on(Button.Pressed, "#yes")
    def handle_yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#no")
    def handle_no(self) -> None:
        self.dismiss(False)


class SimsManager(App):
    CSS_PATH = "manage_sims.tcss"

    BINDINGS = [
        ("s", "start", "Start simulations"),
        ("k", "stop", "Stop simulations"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        self.status_text = Static()
        self.status_panel = Container(
            Label("Status:"), self.status_text, classes="panel"
        )
        self.progress_panel = Container(Label("Progress:"), classes="panel")
        self.log_text = Log(max_lines=1024)
        self.log_panel = Container(
            Label("Log:"), self.log_text, id="log-panel", classes="panel"
        )

        yield Container(
            self.status_panel, self.log_panel, self.progress_panel, id="panel-grid"
        )

        yield Footer()

    def on_mount(self):
        self.status_panel.loading = True
        self.log_panel.loading = True
        self._last_log_mtime = 0
        # self.expected_paths = generate_expected_paths()
        self.set_interval(1, self.refresh_panels)

    def refresh_panels(self):
        n_pids = len(sims_running())
        self.status_text.update(
            f"[$success]RUNNING[/] processes: {n_pids}"
            if n_pids > 0
            else "[$error]NOT RUNNING[/]"
        )
        self.status_panel.loading = False

        if LOG_FILE.exists():
            log_mtime = LOG_FILE.stat().st_mtime
            if log_mtime != self._last_log_mtime:
                self._last_log_mtime = log_mtime
                self.log_text.clear()
                self.log_text.write(LOG_FILE.read_text())
        self.log_panel.loading = False

    @work
    async def action_start(self) -> None:
        if await self.push_screen_wait(DialogScreen("Start simulations?")):
            if sims_running():
                self.notify("Simulations are already running", severity="warning")
                return

            command = [str(MAKE_ALL_SIMS)]
            if await self.push_screen_wait(
                DialogScreen("Send Telegram notifications?")
            ):
                command.append("--notify")

            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with LOG_FILE.open("w") as log_file:
                subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )

            self.notify("Simulations started")
            return

    @work
    async def action_stop(self) -> None:
        if await self.push_screen_wait(DialogScreen("Stop simulations?")):
            pids = sims_running()

            if not pids:
                self.notify("No simulations are running", severity="warning")
                return

            for pid in pids:
                try:
                    psutil.Process(pid).terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            self.notify("Simulations stopped")
            return


if __name__ == "__main__":
    SimsManager().run()
