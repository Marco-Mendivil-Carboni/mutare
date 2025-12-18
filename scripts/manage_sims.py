#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
import subprocess
from shutil import rmtree
import psutil
import time
from textual import on, work
from textual.worker import Worker, WorkerState, get_current_worker, WorkerCancelled
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container
from textual.widgets import (
    Header,
    Label,
    ProgressBar,
    Collapsible,
    Button,
    Static,
    Log,
    Footer,
)

from utils.exec import create_sim_jobs

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


def yield_or_raise(worker: Worker):
    if worker.is_cancelled:
        raise WorkerCancelled
    time.sleep(0)


def scan_sims_dir() -> tuple[int, int, set[Path]]:
    worker = get_current_worker()

    n_expected_msgpack_files = 0
    n_missing_msgpack_files = 0
    unexpected_entries = set()

    for sims_config in SIMS_CONFIGS:
        yield_or_raise(worker)
        sim_jobs = create_sim_jobs(sims_config)
        base_dir = sims_config.init_sim_job.base_dir
        run_options = sims_config.init_sim_job.run_options

        yield_or_raise(worker)
        sim_dirs = {sim_job.sim_dir for sim_job in sim_jobs}

        expected_base_dir_entry_names = {sim_dir.name for sim_dir in sim_dirs}.union(
            {"plots"}
        )
        run_dir_names = {f"run-{run_idx:04}" for run_idx in range(run_options.n_runs)}
        expected_sim_dir_entry_names = run_dir_names.union(
            {".lock", "config.toml", "output.log"}
        )
        expected_run_dir_entry_names = {
            f"output-{file_idx:04}.msgpack" for file_idx in range(run_options.n_files)
        }.union({"checkpoint.msgpack", "analysis.msgpack"})

        n_expected_msgpack_files += (
            len(sim_dirs) * run_options.n_runs * (run_options.n_files + 2)
        )

        yield_or_raise(worker)
        base_dir_entry_names = {path.name for path in base_dir.iterdir()}
        unexpected_entries |= {
            base_dir / entry_name
            for entry_name in base_dir_entry_names - expected_base_dir_entry_names
        }

        for sim_dir in sim_dirs:
            run_dirs = {sim_dir / run_dir_name for run_dir_name in run_dir_names}

            yield_or_raise(worker)
            sim_dir_entry_names = {path.name for path in sim_dir.iterdir()}
            unexpected_entries |= {
                sim_dir / entry_name
                for entry_name in sim_dir_entry_names - expected_sim_dir_entry_names
            }

            for run_dir in run_dirs:
                yield_or_raise(worker)
                run_dir_entry_names = {path.name for path in run_dir.iterdir()}
                unexpected_entries |= {
                    run_dir / entry_name
                    for entry_name in run_dir_entry_names - expected_run_dir_entry_names
                }

                n_missing_msgpack_files += len(
                    expected_run_dir_entry_names - run_dir_entry_names
                )

    return n_expected_msgpack_files, n_missing_msgpack_files, unexpected_entries


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
        self.progress_bar = ProgressBar(show_eta=False)
        self.progress_label = Label("0 / 0")

        self.unexpected_label = Label("")
        self.rescan_button = Button("Rescan", id="rescan", variant="primary")
        self.progress_panel = Container(
            Label("Progress:"),
            self.progress_bar,
            self.progress_label,
            self.rescan_button,
            Collapsible(self.unexpected_label, title="Unexpected entries"),
            classes="panel",
        )

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
        self.progress_panel.loading = True
        self.log_panel.loading = True

        self.sims_dir_paths = None
        self._last_log_mtime = 0

        self.set_interval(1.0, self.refresh_panels)
        self.run_scan_sims_dir()

    def refresh_panels(self):
        n_pids = len(sims_running())
        self.status_text.update(
            f"[$success]RUNNING[/] processes: {n_pids}"
            if n_pids > 0
            else "[$error]NOT RUNNING[/]"
        )
        self.status_panel.loading = False

        if (self.background_worker is not None) and (
            self.background_worker.state == WorkerState.SUCCESS
        ):
            if self.background_worker.result is not None:
                n_expected_files, n_missing_files, unexpected_paths = (
                    self.background_worker.result
                )
                self.progress_bar.total = n_expected_files
                self.progress_bar.progress = n_expected_files - n_missing_files
                self.progress_label.update(
                    f"{self.progress_bar.progress} / {self.progress_bar.total}"
                )
                self.unexpected_label.update(
                    "\n".join([str(path) for path in unexpected_paths])
                )
                self.progress_panel.loading = False

        if LOG_FILE.exists():
            log_mtime = LOG_FILE.stat().st_mtime
            if log_mtime != self._last_log_mtime:
                self._last_log_mtime = log_mtime
                self.log_text.clear()
                self.log_text.write(LOG_FILE.read_text())
        self.log_panel.loading = False

    @on(Button.Pressed, "#rescan")
    def rescan_pressed(self) -> None:
        self.progress_panel.loading = True
        self.run_scan_sims_dir()

    def run_scan_sims_dir(self) -> None:
        self.background_worker = self.run_worker(
            scan_sims_dir, exclusive=True, thread=True
        )

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
