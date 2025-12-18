#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
import subprocess
from shutil import rmtree
import psutil
from dataclasses import dataclass
import time
from textual import on, work
from textual.worker import Worker, get_current_worker, WorkerCancelled
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.containers import Horizontal, Vertical, Grid
from textual.widgets import Header, Label, Button, ProgressBar, Log, Footer

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


@dataclass
class ProgressInfo:
    n_expected_msgpacks: int
    n_missing_msgpacks: int
    extra_entries: set[Path]


def yield_or_raise(worker: Worker):
    if worker.is_cancelled:
        raise WorkerCancelled
    time.sleep(0)


def scan_sims_dir() -> ProgressInfo:
    worker = get_current_worker()

    progress_info = ProgressInfo(0, 0, set())

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

        progress_info.n_expected_msgpacks += (
            len(sim_dirs) * run_options.n_runs * (run_options.n_files + 2)
        )

        yield_or_raise(worker)
        base_dir_entry_names = {path.name for path in base_dir.iterdir()}
        progress_info.extra_entries |= {
            base_dir / entry_name
            for entry_name in base_dir_entry_names - expected_base_dir_entry_names
        }

        for sim_dir in sim_dirs:
            run_dirs = {sim_dir / run_dir_name for run_dir_name in run_dir_names}

            yield_or_raise(worker)
            sim_dir_entry_names = {path.name for path in sim_dir.iterdir()}
            progress_info.extra_entries |= {
                sim_dir / entry_name
                for entry_name in sim_dir_entry_names - expected_sim_dir_entry_names
            }

            for run_dir in run_dirs:
                yield_or_raise(worker)
                run_dir_entry_names = {path.name for path in run_dir.iterdir()}
                progress_info.extra_entries |= {
                    run_dir / entry_name
                    for entry_name in run_dir_entry_names - expected_run_dir_entry_names
                }

                progress_info.n_missing_msgpacks += len(
                    expected_run_dir_entry_names - run_dir_entry_names
                )

    return progress_info


class DialogScreen(ModalScreen[bool]):
    def __init__(self, question: str) -> None:
        self.question = question
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Grid(
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

        self.status_text = Label()
        self.status_panel = Vertical(
            Label("Status:", classes="title"), self.status_text, classes="panel"
        )

        self.progress_bar = ProgressBar(show_eta=False)
        self.progress_text = Label()
        self.extra_text = Label()
        self.main_progress_info = Horizontal(
            self.progress_bar,
            self.progress_text,
            Button("Update", id="update-progress", variant="primary"),
            id="main-progress-info",
        )
        self.extra_progress_info = Horizontal(
            self.extra_text,
            Button("Delete", id="delete-extra", variant="error"),
            classes="sub-panel",
        )
        self.progress_panel = Vertical(
            Label("Progress:", classes="title"),
            self.main_progress_info,
            self.extra_progress_info,
            classes="panel",
        )

        self.log_text = Log(max_lines=1024)
        self.log_panel = Vertical(
            Label("Log:", classes="title"),
            self.log_text,
            id="log-panel",
            classes="panel",
        )

        yield Grid(
            self.status_panel, self.log_panel, self.progress_panel, id="panel-grid"
        )

        yield Footer()

    def on_mount(self):
        self.status_panel.loading = True

        self.update_progress_info()

        self.log_panel.loading = True
        self._last_log_mtime = 0.0

        self.set_interval(1.0, self.refresh_panels)

    def update_progress_info(self) -> None:
        self.progress_panel.loading = True
        self._background_worker = self.run_worker(
            scan_sims_dir, exclusive=True, thread=True
        )

    def refresh_panels(self):
        n_pids = len(sims_running())
        self.status_text.update(
            "[bold $success]RUNNING[/]\n" + f"[dim]{n_pids} active process(es)[/]"
            if n_pids > 0
            else "[bold $error]NOT RUNNING[/]"
        )
        self.status_panel.loading = False

        if self._background_worker.result:
            progress_info = self._background_worker.result
            n_expected_msgpacks = progress_info.n_expected_msgpacks
            n_missing_msgpacks = progress_info.n_missing_msgpacks
            extra_entries = progress_info.extra_entries

            self.progress_bar.total = n_expected_msgpacks
            self.progress_bar.progress = n_expected_msgpacks - n_missing_msgpacks
            self.progress_text.update(
                f"[dim]{n_expected_msgpacks} expected_msgpacks[/]\n"
                + f"[dim]{n_missing_msgpacks} missing msgpacks[/]"
            )

            show_extra_info = bool(extra_entries)
            self.extra_progress_info.display = show_extra_info
            if show_extra_info:
                MAX_SHOW = 1
                lines = [f"\t[dim]{path}[/]" for path in list(extra_entries)[:MAX_SHOW]]
                if len(extra_entries) > MAX_SHOW:
                    lines.append(
                        f"[dim]... and {len(extra_entries) - MAX_SHOW} more[/]"
                    )
                self.extra_text.update("\n".join(lines))

            self.progress_panel.loading = False

        if LOG_FILE.exists():
            log_mtime = LOG_FILE.stat().st_mtime
            if log_mtime != self._last_log_mtime:
                self._last_log_mtime = log_mtime
                self.log_text.clear()
                self.log_text.write(LOG_FILE.read_text())
        self.log_panel.loading = False

    @on(Button.Pressed, "#update-progress")
    def update_progress_pressed(self) -> None:
        self.update_progress_info()

    @on(Button.Pressed, "#delete-extra")
    @work
    async def delete_extra_pressed(self) -> None:
        if self._background_worker.result:
            extra_entries = self._background_worker.result.extra_entries
            if extra_entries:
                if await self.push_screen_wait(
                    DialogScreen(f"Delete {len(extra_entries)} extra entries?")
                ):
                    for entry in extra_entries:
                        if entry.is_dir():
                            rmtree(entry)
                        else:
                            entry.unlink()
                    self.update_progress_info()

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
