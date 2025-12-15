#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
import subprocess
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual import on, work
from textual.containers import Horizontal, Grid, Vertical, Container
from textual.widgets import (
    Checkbox,
    Label,
    ProgressBar,
    DirectoryTree,
    Button,
    Static,
    Log,
    Header,
    Footer,
)

from sims_configs import SIMS_DIR, SIMS_CONFIGS

MAKE_ALL_SIMS = Path(__file__).resolve().parent / "make_all_sims.py"
LOG_FILE = SIMS_DIR / "output.log"


def sims_running() -> bool:
    try:
        subprocess.check_output(["pgrep", "-f", str(MAKE_ALL_SIMS)])
        return True
    except subprocess.CalledProcessError:
        return False


def start_sims(notify: bool) -> bool:
    if sims_running():
        return False

    command = [str(MAKE_ALL_SIMS)]
    if notify:
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

    return True


def stop_sims() -> bool:
    if not sims_running():
        return False

    subprocess.run(["pkill", "-f", str(MAKE_ALL_SIMS)])

    return True


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
            Label("Status:"), self.status_text, id="status-panel", classes="panel"
        )
        self.progress_panel = Container(Label("Progress:"), classes="panel")
        self.log_text = Log(max_lines=1024)
        self.log_panel = Container(Label("Log:"), self.log_text, classes="panel")

        yield Container(
            self.status_panel, self.progress_panel, self.log_panel, id="panel-grid"
        )

        yield Footer()

    def on_mount(self):
        self.set_interval(1, self.refresh_panels)
        self._last_log_mtime = 0

    def refresh_panels(self):
        status_text = (
            "[$success]RUNNING[/]" if sims_running() else "[$error]NOT RUNNING[/]"
        )

        self.status_text.update(f"{status_text}")

        if LOG_FILE.exists():
            log_mtime = LOG_FILE.stat().st_mtime
            if log_mtime != self._last_log_mtime:
                self._last_log_mtime = log_mtime
                self.log_text.clear()
                self.log_text.write(LOG_FILE.read_text())

    @work
    async def action_start(self) -> None:
        if await self.push_screen_wait(DialogScreen("Start simulations?")):
            start_sims(
                await self.push_screen_wait(
                    DialogScreen("Send Telegram notifications?")
                )
            )
            self.notify("simulations started")

    @work
    async def action_stop(self) -> None:
        if await self.push_screen_wait(DialogScreen("Stop simulations?")):
            stop_sims()
            self.notify("simulations stopped")


if __name__ == "__main__":
    SimsManager().run()
