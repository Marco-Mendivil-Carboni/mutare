#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
import subprocess
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal
from textual.widgets import Checkbox, Button, Static, Label, Log, Header, Footer

MAIN_SCRIPT = Path("scripts/make_all_sims.py").resolve()
LOG_FILE = Path("sims/output.log").resolve()


def sims_running() -> bool:
    try:
        subprocess.check_output(["pgrep", "-f", str(MAIN_SCRIPT)])
        return True
    except subprocess.CalledProcessError:
        return False


def start_sims(notify: bool, clean: bool) -> bool:
    if sims_running():
        return False

    command = [str(MAIN_SCRIPT)]
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

    subprocess.run(["pkill", "-f", str(MAIN_SCRIPT)])

    return True


class StartSimsScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        yield Label("Start Simulations")
        with Vertical():
            self.notify_cb = Checkbox("Send Telegram notifications?")
            self.clean_cb = Checkbox("Prune stale simulation directories?")
            yield self.notify_cb
            yield self.clean_cb

        with Horizontal():
            yield Button("Start", id="start", variant="primary")
            yield Button("Cancel", id="cancel", variant="error")

    def on_button_pressed(self, event: Button.Pressed):
        button_id = event.button.id
        if button_id == "start":
            start_sims(self.notify_cb.value, self.clean_cb.value)
            self.app.pop_screen()
        elif button_id == "cancel":
            self.app.pop_screen()


class SimsManager(App):
    BINDINGS = [
        ("s", "start", "Start simulations"),
        ("k", "stop", "Stop simulations"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        self.status_panel = Static("Status: Loading...", id="status_panel")
        yield self.status_panel

        self.log_panel = Log(max_lines=10, id="log_panel")
        yield self.log_panel

        yield Footer()

    def on_mount(self):
        self.set_interval(1, self.refresh_status)

    def refresh_status(self):
        if sims_running():
            status = "RUNNING"
        else:
            status = "NOT RUNNING"

        self.status_panel.update(f"Status: {status}")

        if LOG_FILE.exists():
            lines = LOG_FILE.read_text().splitlines(keepends=True)[-10:]
            self.log_panel.clear()
            for line in lines:
                self.log_panel.write(line)

    def action_start(self) -> None:
        self.push_screen(StartSimsScreen())

    def action_stop(self) -> None:
        stop_sims()


if __name__ == "__main__":
    SimsManager().run()
