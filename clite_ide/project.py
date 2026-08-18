"""Project management: new/open/save projects and single-file mode."""

import json
import os

PROJECT_FILE = "project.json"

DEFAULT_MAIN = """\
#include <stdio.h>
#include <conio.h>

int main()
{
    printf("Hello, World!\\n");
    printf("Press any key to exit...\\n");
    getch();
    return 0;
}
"""


def project_exists(directory):
    return os.path.isfile(os.path.join(directory, PROJECT_FILE))


class Project:
    def __init__(self, directory, name=None, files=None, extra_flags=None):
        self.directory = os.path.abspath(directory)
        self.name = name or os.path.basename(self.directory)
        self.files = list(files or [])
        self.extra_flags = list(extra_flags or [])

    # ---- paths ----
    def src_dir(self):
        return os.path.join(self.directory, "src")

    def include_dir(self):
        return os.path.join(self.directory, "include")

    def assets_dir(self):
        return os.path.join(self.directory, "assets")

    def build_dir(self):
        return os.path.join(self.directory, "build")

    def exe_path(self):
        return os.path.join(self.build_dir(), self.name + ".exe")

    # ---- persistence ----
    def save(self):
        data = {
            "name": self.name,
            "version": 1,
            "files": self.files,
            "extra_flags": self.extra_flags,
        }
        with open(os.path.join(self.directory, PROJECT_FILE), "w",
                  encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    @staticmethod
    def load(directory):
        with open(os.path.join(directory, PROJECT_FILE), "r",
                  encoding="utf-8") as fh:
            data = json.load(fh)
        return Project(directory,
                       name=data.get("name"),
                       files=data.get("files", []),
                       extra_flags=data.get("extra_flags", []))

    # ---- source discovery ----
    def source_files(self):
        """Return .c/.cpp files belonging to the project."""
        src = self.src_dir()
        files = []
        for f in self.files:
            p = os.path.join(self.directory, f)
            if os.path.isfile(p):
                files.append(p)
        if os.path.isdir(src):
            for name in sorted(os.listdir(src)):
                if name.lower().endswith((".c", ".cpp", ".cc", ".cxx")):
                    p = os.path.join(src, name)
                    if p not in files:
                        files.append(p)
        return files

    def file_tree(self):
        """Return a tree of [name, is_dir, children] entries for the
        project directory (excluding build output)."""
        tree = []
        skip = {"build"}
        for name in sorted(os.listdir(self.directory)):
            if name in skip:
                continue
            p = os.path.join(self.directory, name)
            if os.path.isdir(p):
                tree.append([name, True, self._dir_tree(p)])
            else:
                tree.append([name, False, []])
        return tree

    def _dir_tree(self, path):
        out = []
        try:
            entries = sorted(os.listdir(path))
        except OSError:
            return out
        for name in entries:
            p = os.path.join(path, name)
            if os.path.isdir(p):
                out.append([name, True, self._dir_tree(p)])
            else:
                out.append([name, False, []])
        return out


def create_project(directory, name):
    os.makedirs(os.path.join(directory, "src"), exist_ok=True)
    os.makedirs(os.path.join(directory, "include"), exist_ok=True)
    os.makedirs(os.path.join(directory, "assets"), exist_ok=True)
    os.makedirs(os.path.join(directory, "build"), exist_ok=True)
    main_path = os.path.join(directory, "src", "main.c")
    if not os.path.isfile(main_path):
        with open(main_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(DEFAULT_MAIN)
    project = Project(directory, name=name, files=["src/main.c"])
    project.save()
    return project