#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
import subprocess
from shutil import rmtree
import psutil
from dataclasses import dataclass
from signal import SIGUSR1
import time
from textual import on, work
from textual.worker import Worker, get_current_worker, WorkerCancelled
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Grid, ItemGrid
from textual.widgets import Label, Button, ProgressBar, Log, Footer

from mutare_tools import create_sim_jobs

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

    def check_dir_entry_names(
        dir: Path, expected_dir_entry_names: set[str]
    ) -> set[str]:
        dir_entry_names = (
            {path.name for path in dir.iterdir()} if dir.is_dir() else set()
        )
        progress_info.extra_entries |= {
            dir / entry_name
            for entry_name in dir_entry_names - expected_dir_entry_names
        }
        return dir_entry_names

    expected_sims_dir_entry_names = {"output.log"}

    for sims_config in SIMS_CONFIGS:
        yield_or_raise(worker)
        sim_jobs = create_sim_jobs(sims_config)
        base_dir = sims_config.init_sim_job.base_dir
        n_runs = sims_config.init_sim_job.n_runs
        n_files = sims_config.init_sim_job.n_files

        expected_sims_dir_entry_names |= {base_dir.name}

        yield_or_raise(worker)
        sim_dirs = {sim_job.sim_dir for sim_job in sim_jobs}

        sim_dir_names = {sim_dir.name for sim_dir in sim_dirs}
        expected_base_dir_entry_names = sim_dir_names | {"plots"}
        run_dir_names = {f"run-{run_idx:04}" for run_idx in range(n_runs)}
        expected_sim_dir_entry_names = run_dir_names | {"config.toml"}
        expected_run_dir_entry_names = {
            f"output-{file_idx:04}.msgpack" for file_idx in range(n_files)
        } | {"checkpoint.msgpack", "analysis.msgpack", ".lock", "output.log"}

        progress_info.n_expected_msgpacks += len(sim_dirs) * n_runs * (n_files + 2)

        yield_or_raise(worker)
        check_dir_entry_names(base_dir, expected_base_dir_entry_names)

        for sim_dir in sim_dirs:
            run_dirs = {sim_dir / run_dir_name for run_dir_name in run_dir_names}

            yield_or_raise(worker)
            check_dir_entry_names(sim_dir, expected_sim_dir_entry_names)

            for run_dir in run_dirs:
                yield_or_raise(worker)
                run_dir_entry_names = check_dir_entry_names(
                    run_dir, expected_run_dir_entry_names
                )

                progress_info.n_missing_msgpacks += len(
                    expected_run_dir_entry_names
                    - {".lock", "output.log"}
                    - run_dir_entry_names
                )

    check_dir_entry_names(SIMS_DIR, expected_sims_dir_entry_names)

    return progress_info


class Header(Container):
    pass


class Panel(Container):
    pass


class PanelTitle(Container):
    pass


class SubPanel(Container):
    pass


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
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        ("s", "start", "Start simulations"),
        ("p", "pause", "Pause simulations"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(Label("Simulations Manager"))

        self.status_text = Label()
        self.status_panel = Panel(
            PanelTitle(Label("Status:")), SubPanel(self.status_text)
        )

        self.update_progress = Button(
            "Update", id="update-progress", variant="primary", compact=True
        )
        self.progress_bar = ProgressBar(show_eta=False)
        self.progress_text = Label()
        self.extra_text = Label()
        self.delete_extra = Button(
            "Delete", id="delete-extra", variant="error", compact=True
        )
        self.progress_panel = Panel(
            PanelTitle(Label("Progress:"), self.update_progress),
            SubPanel(self.progress_bar, self.progress_text),
            SubPanel(self.extra_text, self.delete_extra),
        )

        self.log_text = Log()
        self.log_panel = Panel(PanelTitle(Label("Log:")), SubPanel(self.log_text))

        yield ItemGrid(
            Grid(self.status_panel, self.progress_panel, id="inner-panel-grid"),
            self.log_panel,
            min_column_width=32,
            id="main-panel-grid",
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
                f"[dim]{n_expected_msgpacks} expected msgpacks[/]\n"
                + f"[dim]{n_missing_msgpacks} missing msgpacks[/]"
            )

            if extra_entries:
                n_entries = len(extra_entries)
                lines = [f"{n_entries} extra entries:"]
                MAX_ENTRY_LINES = 4
                for entry in list(extra_entries)[:MAX_ENTRY_LINES]:
                    lines.append(f"  · [dim]{entry.relative_to(SIMS_DIR)}[/]")
                if n_entries > MAX_ENTRY_LINES:
                    lines[-1] = "  · [dim]...[/]"
                self.extra_text.update("\n".join(lines))
                self.delete_extra.disabled = False
            else:
                self.extra_text.update("No extra entries")
                self.delete_extra.disabled = True

            self.progress_panel.loading = False

        if LOG_FILE.exists():
            log_mtime = LOG_FILE.stat().st_mtime
            if log_mtime != self._last_log_mtime:
                self._last_log_mtime = log_mtime
                self.log_text.clear()
                MAX_LOG_LINES = 1_024
                with LOG_FILE.open() as log_file:
                    for log_line in log_file.readlines()[-MAX_LOG_LINES:]:
                        self.log_text.write(log_line)
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

            if await self.push_screen_wait(
                DialogScreen("Remove previous analysis files?")
            ):
                for file in SIMS_DIR.rglob("analysis.msgpack"):
                    file.unlink()

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
    async def action_pause(self) -> None:
        if await self.push_screen_wait(DialogScreen("Pause simulations?")):
            pids = sims_running()

            if not pids:
                self.notify("No simulations are running", severity="warning")
                return

            for pid in pids:
                try:
                    psutil.Process(pid).send_signal(SIGUSR1)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            self.notify("Simulations paused")
            return


if __name__ == "__main__":
    SimsManager().run()
