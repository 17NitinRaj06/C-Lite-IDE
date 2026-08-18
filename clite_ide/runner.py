"""Process runner: launches compiled executables, streams output to the
terminal and provides stop/process-kill control."""

import os
import subprocess
import threading
import time

CREATE_NO_WINDOW = 0x08000000


class Runner:
    def __init__(self, app):
        self.app = app
        self.process = None
        self.start_time = 0.0
        self._stop_requested = False

    def is_running(self):
        return self.process is not None and self.process.poll() is None

    def run(self, exe_path, cwd, on_exit):
        """Launch exe; streams output to the app terminal.

        The process is created on a background thread so a slow first-run
        startup (e.g. antivirus scanning a freshly built executable) never
        freezes the UI."""
        self.stop()
        self._stop_requested = False
        terminal = self.app.terminal
        terminal.begin_run("Running: %s" % os.path.basename(exe_path))
        self.app.set_running_state(True)
        self.start_time = time.time()

        def launch():
            try:
                proc = subprocess.Popen(
                    [exe_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=cwd,
                    bufsize=0,
                    env=self.app.builder.runtime_env(),
                    creationflags=CREATE_NO_WINDOW)
            except OSError as exc:
                self.app.root.after(
                    0, terminal.note_error,
                    "Failed to start program: %s" % exc)
                self.app.root.after(0, self.app.set_running_state, False)
                return

            if self._stop_requested:
                try:
                    proc.terminate()
                except OSError:
                    pass
                return

            self.process = proc
            self.app.root.after(0, terminal.set_process, proc)
            self.app.root.after(0, terminal.entry.focus_set)

            def read_output():
                try:
                    while True:
                        raw = proc.stdout.read(4096)
                        if not raw:
                            break
                        text = raw.decode("utf-8", errors="replace")
                        self.app.root.after(0, terminal.write, text)
                except (OSError, ValueError):
                    pass

            def wait_exit():
                code = proc.wait()
                elapsed = time.time() - self.start_time
                self.process = None
                self.app.root.after(
                    0, terminal.end_run, code)
                self.app.root.after(0, self.app.set_running_state, False)
                self.app.root.after(0, self.app.on_run_finished, code,
                                    elapsed)

            threading.Thread(target=read_output, daemon=True).start()
            threading.Thread(target=wait_exit, daemon=True).start()

        threading.Thread(target=launch, daemon=True).start()

    def write_stdin(self, line):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(
                    (line + "\n").encode("utf-8", errors="replace"))
                self.process.stdin.flush()
            except (BrokenPipeError, OSError, ValueError):
                pass

    def stop(self):
        self._stop_requested = True
        if not self.process:
            return
        proc = self.process
        try:
            if proc.poll() is None:
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    capture_output=True, timeout=5,
                    creationflags=CREATE_NO_WINDOW)
                try:
                    proc.kill()
                except OSError:
                    pass
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        self.process = None
        self.app.terminal.note_error("Program stopped.")