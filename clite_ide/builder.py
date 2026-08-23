"""Compiler integration: builds gcc command lines and parses output."""

import os
import re
import subprocess
import threading
import time

from . import INCLUDE_DIR, RUNTIME_DIR, RUNTIME_SOURCES, RUNTIME_LINK_LIBS
from .settings import (find_gcc, gcc_version, toolchain_bin,
                       toolchain_root, compiler_source)

RE_PROBLEM = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):(?P<col>\d+):\s+"
    r"(?P<sev>error|fatal error|warning):\s+(?P<msg>.+)$")

RE_REFERENCE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):\s+(?P<msg>.+)$")

RE_FUNCTION_CONTEXT = re.compile(r"^(.+?): In function .+:$")
RE_LINKER_ERR = re.compile(r"(collect2\.exe:.*error|ld returned|undefined reference)")


class BuildResult:
    def __init__(self):
        self.success = False
        self.exe_path = None
        self.problems = []      # list of dicts
        self.full_output = ""
        self.compiler_missing = False
        self.command = None     # full gcc command line (list)
        self.exit_code = None   # compiler process return code
        self.elapsed = None     # seconds spent in the compiler process


class Builder:
    def __init__(self, app):
        self.app = app
        self.settings = app.settings
        self._runtime_objs_ok = False
        self._runtime_objs_dir = None

    # ------------------------------------------------------------------

    def gcc_path(self):
        return find_gcc(self.settings.get("compiler_path", ""))

    def toolchain_include(self, gcc=None):
        """-I directories: the toolchain's own headers plus the IDE's."""
        gcc = gcc or self.gcc_path()
        dirs = [INCLUDE_DIR, RUNTIME_DIR]
        root = toolchain_root(gcc)
        if root:
            inc = os.path.join(root, "include")
            if os.path.isdir(inc):
                dirs.append(inc)
        return dirs

    def toolchain_lib_dir(self, gcc=None):
        gcc = gcc or self.gcc_path()
        root = toolchain_root(gcc)
        if root:
            lib = os.path.join(root, "lib")
            if os.path.isdir(lib):
                return lib
        return None

    def runtime_env(self):
        """Environment for child processes, with the toolchain bin dir on
        PATH so its runtime DLLs (libgcc_s_dw2-1.dll, libstdc++-6.dll,
        ...) are found by compiled executables."""
        env = dict(os.environ)
        bindir = toolchain_bin(self.gcc_path())
        if bindir:
            env["PATH"] = bindir + os.pathsep + env.get("PATH", "")
        return env

    def gcc_driver(self, sources):
        for s in sources:
            if s.lower().endswith((".cpp", ".cc", ".cxx", ".c++")):
                return True
        return False

    def _driver_path(self, sources):
        gcc = self.gcc_path()
        if not gcc:
            return None
        if self.gcc_driver(sources):
            gxx = os.path.join(os.path.dirname(gcc), "g++.exe")
            if os.path.isfile(gxx):
                return gxx
        return gcc

    # ------------------------------------------------------------------

    def ensure_runtime_objects(self, build_dir):
        """Compile the runtime .c files to .o files once (reused across
        builds so repeated compiles are fast)."""
        rt_dir = os.path.join(build_dir, "runtime")
        os.makedirs(rt_dir, exist_ok=True)
        gcc = self.gcc_path()
        if not gcc:
            return None
        objs = []
        for src in RUNTIME_SOURCES:
            src_path = os.path.join(RUNTIME_DIR, src)
            obj_path = os.path.join(rt_dir, os.path.splitext(src)[0] + ".o")
            need = (not os.path.isfile(obj_path) or
                    os.path.getmtime(src_path) > os.path.getmtime(obj_path))
            if need:
                cmd = [gcc, "-c", src_path, "-o", obj_path,
                       "-I", INCLUDE_DIR, "-I", RUNTIME_DIR,
                       "-std=gnu99", "-O0"]
                for inc in self.toolchain_include(gcc)[2:]:
                    cmd += ["-I", inc]
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                      env=self.runtime_env())
                if proc.returncode != 0:
                    return None
            objs.append(obj_path)
        self._runtime_objs_ok = True
        self._runtime_objs_dir = rt_dir
        return objs

    def build_command(self, sources, out_exe, build_dir):
        driver = self._driver_path(sources)
        if not driver:
            return None
        cmd = [driver]
        cmd += sources
        objs = self.ensure_runtime_objects(build_dir)
        if objs:
            cmd += objs
        for inc in self.toolchain_include(driver):
            cmd += ["-I", inc]
        std = "-std=gnu++17" if self.gcc_driver(sources) else "-std=gnu99"
        cmd += [std, "-O0", "-g", "-Wall"]
        extra = (self.settings.get("extra_flags", "") or "").strip()
        if extra:
            cmd += extra.split()
        cmd += ["-o", out_exe]
        libdir = self.toolchain_lib_dir(driver)
        if libdir:
            cmd += ["-L", libdir]
        cmd += RUNTIME_LINK_LIBS
        return cmd

    # ------------------------------------------------------------------

    def compile(self, sources, out_exe, build_dir, on_finish, on_command=None):
        def work():
            result = BuildResult()
            driver = self._driver_path(sources)
            if not driver:
                result.compiler_missing = True
                result.full_output = "Compiler not found. The bundled " \
                                     "MinGW GCC is missing or corrupt - " \
                                     "reinstall the application, or set " \
                                     "a GCC path in View > Settings."
                self.app.root.after(0, lambda: on_finish(result))
                return

            cmd = self.build_command(sources, out_exe, build_dir)
            if not cmd:
                result.compiler_missing = True
                result.full_output = "Compiler not found."
                self.app.root.after(0, lambda: on_finish(result))
                return
            result.command = list(cmd)
            if on_command:
                self.app.root.after(
                    0, lambda c=result.command: on_command(list(c)))

            start = time.time()
            try:
                proc = subprocess.run(
                    cmd, capture_output=True, text=True,
                    encoding="utf-8", errors="replace",
                    env=self.runtime_env(),
                    creationflags=subprocess.CREATE_NO_WINDOW)
            except OSError as exc:
                result.elapsed = time.time() - start
                result.full_output = "Failed to start compiler: %s" % exc
                self.app.root.after(0, lambda: on_finish(result))
                return
            result.elapsed = time.time() - start

            output = (proc.stdout or "") + (proc.stderr or "")
            result.full_output = output
            result.exit_code = proc.returncode
            result.problems = self.parse_output(output)
            result.success = proc.returncode == 0 and not any(
                p["severity"] == "error" for p in result.problems)
            if result.success:
                result.exe_path = out_exe
                self._warm_exe(out_exe)
            self.app.root.after(0, lambda: on_finish(result))

        threading.Thread(target=work, daemon=True).start()

    # ------------------------------------------------------------------

    def _warm_exe(self, exe_path):
        """Trigger the antivirus first-run scan of a freshly built exe so
        the user's first Run is not slowed by it.  The process is created
        suspended and terminated without running any user code; this
        forces Windows Defender (and similar) to scan the image while the
        build is still in progress.  Runs on the build thread."""
        try:
            p = subprocess.Popen(
                [exe_path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=os.path.dirname(exe_path) or None,
                env=self.runtime_env(),
                creationflags=subprocess.CREATE_NO_WINDOW |
                0x4)  # CREATE_SUSPENDED
            try:
                p.terminate()
            except OSError:
                pass
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                try:
                    p.kill()
                except OSError:
                    pass
        except Exception:
            pass

    # ------------------------------------------------------------------

    def parse_output(self, output):
        problems = []
        lines = output.splitlines()
        in_function = ""
        for i, line in enumerate(lines):
            m = RE_FUNCTION_CONTEXT.match(line)
            if m:
                in_function = line
                continue
            m = RE_PROBLEM.match(line)
            if m:
                path = m.group("path").strip()
                sev = "error" if m.group("sev").startswith("error") \
                    else "warning"
                problems.append({
                    "severity": sev,
                    "message": m.group("msg"),
                    "file": os.path.abspath(path),
                    "line": int(m.group("line")),
                    "col": int(m.group("col")),
                })
                if sev == "warning" and "return type" in m.group("msg"):
                    problems.append({
                        "severity": "hint",
                        "message": "Turbo C compatibility: 'void main()' "
                                   "is non-standard C. Recommended: "
                                   "int main()",
                        "file": os.path.abspath(path),
                        "line": int(m.group("line")),
                        "col": int(m.group("col")),
                    })
                continue
            m = RE_REFERENCE.match(line)
            if m and ("undefined reference" in m.group("msg")
                      or "ld returned" in m.group("msg")
                      or "linker" in m.group("msg").lower()):
                path = m.group("path")
                problems.append({
                    "severity": "error",
                    "message": m.group("msg"),
                    "file": os.path.abspath(path) if os.path.sep in path
                    else "",
                    "line": int(m.group("line")),
                    "col": 1,
                })
                continue
            if RE_LINKER_ERR.search(line):
                problems.append({
                    "severity": "error",
                    "message": line.strip(),
                    "file": "",
                    "line": 1,
                    "col": 1,
                })
                continue
            if "warning:" in line and not m:
                pass
        return problems

    # ------------------------------------------------------------------

    def compiler_info(self):
        gcc, source = compiler_source(
            self.settings.get("compiler_path", ""))
        if not gcc:
            return "GCC: not found"
        label = {"bundled": " (bundled)",
                 "custom": " (settings)",
                 "path": " (PATH)",
                 "auto": ""}.get(source, "")
        return "GCC: " + (gcc_version(gcc) or
                          os.path.basename(gcc)) + label