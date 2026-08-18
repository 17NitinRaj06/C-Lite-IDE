#!/usr/bin/env python3
"""Generate version_info.txt for PyInstaller from version.txt"""

import os
import sys

# Read version from version.txt
version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "version.txt")
try:
    with open(version_file, "r", encoding="utf-8") as f:
        version = f.read().strip()
except Exception as e:
    print(f"ERROR: Could not read version from {version_file}: {e}")
    sys.exit(1)

if not version:
    print("ERROR: Version is empty")
    sys.exit(1)

# Parse version components
try:
    parts = version.split(".")
    ver_major = int(parts[0])
    ver_minor = int(parts[1])
    ver_patch = int(parts[2])
except (ValueError, IndexError) as e:
    print(f"ERROR: Invalid version format '{version}': {e}")
    sys.exit(1)

ver_build = 0

# Generate version_info.txt content
content = f'''VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({ver_major}, {ver_minor}, {ver_patch}, {ver_build}),
    prodvers=({ver_major}, {ver_minor}, {ver_patch}, {ver_build}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904b0',
          [
            StringStruct(u'CompanyName', u'C-Lite'),
            StringStruct(u'FileDescription', u'C-Lite IDE - Turbo C compatible IDE for C/C++ students'),
            StringStruct(u'FileVersion', u'{version}'),
            StringStruct(u'InternalName', u'C-Lite IDE'),
            StringStruct(u'OriginalFilename', u'C-Lite IDE.exe'),
            StringStruct(u'ProductName', u'C-Lite IDE'),
            StringStruct(u'ProductVersion', u'{version}'),
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''

# Write to build/version_info.txt
output_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build", "version_info.txt")
os.makedirs(os.path.dirname(output_file), exist_ok=True)
with open(output_file, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Generated {output_file} with version {version}")