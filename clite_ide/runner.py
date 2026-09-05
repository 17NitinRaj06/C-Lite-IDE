"""Process runner: launches compiled executables, streams output to the
terminal and provides stop/process-kill control."""

import os
import subprocess
import threading
import time
import tkinter as tk

CREATE_NO_WINDOW = 0x08000000


class Runner:
    def __init__(self, app):
        self.app = app
        self.process = None
        self.start_time = 0.0
        self._stop_requested = False
        self._run_lock = threading.Lock()
        self._timer_id = None

    def is_running(self):
        return self.process is not None and self.process.poll() is None

    def run(self, exe_path, cwd, on_exit):
        """Launch exe; streams output to the app terminal.

        The process is created on a background thread so a slow first-run
        startup (e.g. antivirus scanning a freshly built executable) never
        freezes the UI."""
        # Guard: only one run at a time
        if not self._run_lock.acquire(blocking=False):
            self.app.root.after(0, self.app.terminal.note_error,
                                "A program is already running. Stop it first.")
            return

        # Stop any previously running process
        if self.is_running():
            self._do_stop()

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
                self._run_lock.release()
                return

            if self._stop_requested:
                try:
                    proc.terminate()
                except OSError:
                    pass
                self._run_lock.release()
                return

            self.process = proc
            self.app.root.after(0, terminal.set_process, proc)
            self.app.root.after(0, terminal.entry.focus_set)

            # Wire up run_timeout
            timeout = self.app.settings.get("run_timeout", 0)
            if timeout and timeout > 0:
                def _timeout_kill():
                    if self.process and self.process.poll() is None:
                        terminal.note_error(
                            "Timed out after %ds — killed." % timeout)
                        self._do_stop()
                self._timer_id = self.app.root.after(
                    timeout * 1000, _timeout_kill)

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
                if self._timer_id is not None:
                    try:
                        self.app.root.after_cancel(self._timer_id)
                    except (tk.TclError, ValueError):
                        pass
                    self._timer_id = None
                self.app.root.after(
                    0, terminal._flush)
                self.app.root.after(
                    0, terminal.end_run, code)
                self.app.root.after(0, self.app.set_running_state, False)
                self.app.root.after(0, self.app.on_run_finished, code,
                                    elapsed)
                self._run_lock.release()

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
        """Public stop entry point."""
        self._stop_requested = True
        self._do_stop()

    def _do_stop(self):
        """Actually kill the running process."""
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