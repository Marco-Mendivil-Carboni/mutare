#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
import subprocess
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.containers import Horizontal, Grid, Vertical, Container
from textual.widgets import (
    Checkbox,
    Label,
    ProgressBar,
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


def start_sims(notify: bool, clean: bool) -> bool:
    if sims_running():
        return False

    command = [str(MAKE_ALL_SIMS)]
    if notify:
        command.append("--notify")
    if clean:
        command.append("--clean")

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


class StartSimsScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        self.label = Label("Start Simulations", classes="title")

        self.notify_chk = Checkbox("Send Telegram notifications?")
        self.clean_chk = Checkbox("Prune stale simulation directories?")

        self.start_btn = Button("Start", id="start", variant="success")
        self.cancel_btn = Button("Cancel", id="cancel", variant="error")

        yield Vertical(
            self.label,
            self.notify_chk,
            self.clean_chk,
            Horizontal(self.start_btn, self.cancel_btn, classes="buttons"),
            classes="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed):
        button_id = event.button.id
        if button_id == "start":
            start_sims(self.notify_chk.value, self.clean_chk.value)
            self.app.pop_screen()
        elif button_id == "cancel":
            self.app.pop_screen()


class SimsManager(App):
    CSS_PATH = "manage_sims.tcss"

    BINDINGS = [
        ("s", "start", "Start simulations"),
        ("k", "stop", "Stop simulations"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        self.status_panel = Static(id="status_panel")
        self.progress_panel = Static()
        self.log_panel = Log()

        yield Container(
            self.status_panel, self.progress_panel, self.log_panel, id="panels"
        )

        yield Footer()

    def on_mount(self):
        self.set_interval(1, self.refresh_panels)

    def refresh_panels(self):
        if sims_running():
            status = "RUNNING"
        else:
            status = "NOT RUNNING"

        self.status_panel.update(f"Status: {status}")
        self.progress_panel.update("...")
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text().splitlines(keepends=True)[-64:]
            self.log_panel.clear()
            for line in lines:
                self.log_panel.write(line)

    def action_start(self) -> None:
        self.push_screen(StartSimsScreen())

    def action_stop(self) -> None:
        stop_sims()


if __name__ == "__main__":
    SimsManager().run()
