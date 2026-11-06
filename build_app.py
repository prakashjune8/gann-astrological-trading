"""Standalone Windows Application Builder & Automated Desktop Shortcut Creator.

Compiles Gann Celestial Tracker Pro into an institutional single-file executable (.exe)
using PyInstaller with complete asset bundling, CustomTkinter theme hooks, and zero-console mode.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def build_application():
    print("=" * 65)
    print("  BUILDING GANN CELESTIAL TRACKER PRO (STANDALONE .EXE)")
    print("=" * 65)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist")
    build_dir = os.path.join(base_dir, "build")
    assets_dir = os.path.join(base_dir, "assets")
    icon_path = os.path.join(assets_dir, "app_icon.ico")

    # Terminate any running instances to prevent Windows file locks (WinError 5 Access Denied)
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Process -Name *Gann* -ErrorAction SilentlyContinue | Stop-Process -Force"],
            capture_output=True
        )
    except Exception:
        pass

    # Ensure icon exists
    if not os.path.exists(icon_path):
        print("[WARN] assets/app_icon.ico not found, building default icon...")
        from PIL import Image, ImageDraw
        os.makedirs(assets_dir, exist_ok=True)
        img = Image.new("RGBA", (256, 256), (11, 15, 25, 255))
        draw = ImageDraw.Draw(img)
        draw.ellipse((10, 10, 246, 246), outline=(245, 158, 11, 255), width=6)
        draw.line((128, 40, 128, 216), fill=(0, 240, 255, 255), width=4)
        draw.line((40, 128, 216, 128), fill=(0, 240, 255, 255), width=4)
        img.save(icon_path, format="ICO")

    # Explicit data inclusions using Windows path separator ';'
    add_data_args = [
        f"--add-data={os.path.join(base_dir, 'user_preferences.json')};.",
        f"--add-data={os.path.join(base_dir, 'holidays_india.json')};.",
        f"--add-data={os.path.join(base_dir, '.cache')};.cache",
        f"--add-data={os.path.join(base_dir, 'audio', 'sounds')};audio/sounds",
        f"--add-data={os.path.join(base_dir, 'data')};data",
        f"--add-data={os.path.join(base_dir, 'assets')};assets",
        f"--add-data={os.path.join(base_dir, 'core')};core",
        f"--add-data={os.path.join(base_dir, 'ui')};ui",
        f"--add-data={os.path.join(base_dir, 'reporting')};reporting",
    ]

    # Command parameters for PyInstaller single-file release
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=GannCelestialTrackerPro",
        "--noconsole",
        "--onefile",
        "--clean",
        "--noconfirm",
        f"--icon={icon_path}",
        "--collect-all=customtkinter",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
    ] + add_data_args + [
        os.path.join(base_dir, "run_app.py")
    ]

    print(f"Target Executable: {os.path.join(dist_dir, 'GannCelestialTrackerPro.exe')}")
    print("Executing PyInstaller compilation with CustomTkinter asset hooks...")
    
    res = subprocess.run(cmd, cwd=base_dir)
    if res.returncode == 0:
        exe_path = os.path.join(dist_dir, "GannCelestialTrackerPro.exe")
        alt_exe = os.path.join(dist_dir, "GannCelestialTracker.exe")
        legacy_dir = r"D:\ANTIGRAVITY PROJECT FOLDER\ephemeris\dist\GannCelestialTracker"
        legacy_exe = os.path.join(legacy_dir, "GannCelestialTracker.exe")

        # Create binary alias copies for complete backwards compatibility
        import shutil
        try:
            shutil.copy2(exe_path, alt_exe)
            if os.path.exists(os.path.dirname(legacy_dir)):
                os.makedirs(legacy_dir, exist_ok=True)
                shutil.copy2(exe_path, legacy_exe)
        except Exception:
            pass

        exe_size_mb = os.path.getsize(exe_path) / (1024 * 1024) if os.path.exists(exe_path) else 0.0
        print("\n" + "=" * 65)
        print(" [SUCCESS] STANDALONE EXECUTABLE COMPILED SUCCESSFULLY!")
        print(f" Output Location: {exe_path}")
        print(f" Binary Size:     {exe_size_mb:.2f} MB")
        print("=" * 65)

        create_desktop_shortcut(exe_path, base_dir, icon_path)
    else:
        print(f"\n[ERROR] PyInstaller compilation failed with return code: {res.returncode}")
        sys.exit(res.returncode)


def create_desktop_shortcut(exe_path: str, working_dir: str, icon_path: str):
    """Creates/Updates both Windows desktop shortcuts (.lnk) via PowerShell."""
    print("\nUpdating Windows Desktop Shortcuts...")
    desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
    ps_cmd = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Desktop = "{desktop}"
    $names = @("Gann Celestial Tracker Pro.lnk", "Gann Celestial Tracker.lnk")
    foreach ($name in $names) {{
        $ShortcutPath = Join-Path $Desktop $name
        $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
        $Shortcut.TargetPath = "{exe_path}"
        $Shortcut.WorkingDirectory = "{working_dir}"
        $Shortcut.IconLocation = "{icon_path}"
        $Shortcut.Description = "Launch Gann Celestial Tracker Pro"
        $Shortcut.Save()
        Write-Host "Desktop shortcut configured: $ShortcutPath"
    }}
    """
    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
    out = res.stdout.strip() or res.stderr.strip()
    print(f"  {out}")


if __name__ == "__main__":
    build_application()
