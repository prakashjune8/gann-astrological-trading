"""Standalone Windows Application Builder & Automated Desktop Shortcut Creator.

Compiles Gann Celestial Tracker Pro into a high-performance standalone binary
using PyInstaller and creates an automated desktop shortcut.
"""
from __future__ import annotations

import os
import subprocess
import sys


def build_application():
    print("==========================================================")
    print("  BUILDING GANN CELESTIAL TRACKER PRO (STANDALONE .EXE)")
    print("==========================================================")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist")
    build_dir = os.path.join(base_dir, "build")

    # Command parameters for PyInstaller
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=GannCelestialTrackerPro",
        "--noconsole",
        "--onedir",
        "--clean",
        "--noconfirm",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--add-data={os.path.join(base_dir, 'core')};core",
        f"--add-data={os.path.join(base_dir, 'ui')};ui",
        f"--add-data={os.path.join(base_dir, 'audio')};audio",
        f"--add-data={os.path.join(base_dir, 'reporting')};reporting",
        os.path.join(base_dir, "run_app.py")
    ]

    print("Running PyInstaller compilation...")
    res = subprocess.run(cmd, cwd=base_dir)
    if res.returncode == 0:
        print("\n[SUCCESS] Binary compiled successfully!")
        exe_path = os.path.join(dist_dir, "GannCelestialTrackerPro", "GannCelestialTrackerPro.exe")
        print(f"Executable path: {exe_path}")
        create_desktop_shortcut(exe_path, base_dir)
    else:
        print(f"\n[ERROR] PyInstaller failed with exit code: {res.returncode}")


def create_desktop_shortcut(exe_path: str, working_dir: str):
    """Creates a Windows desktop shortcut (.lnk) via PowerShell."""
    print("\nCreating Windows Desktop shortcut...")
    ps_cmd = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Desktop = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
    $Shortcut = $WshShell.CreateShortcut((Join-Path $Desktop "Gann Celestial Tracker Pro.lnk"))
    $Shortcut.TargetPath = "{exe_path}"
    $Shortcut.WorkingDirectory = "{working_dir}"
    $Shortcut.Description = "Launch Gann Celestial Tracker Pro"
    $Shortcut.Save()
    Write-Host "Desktop shortcut created successfully!"
    """
    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
    print(res.stdout.strip() or res.stderr.strip())


if __name__ == "__main__":
    build_application()
