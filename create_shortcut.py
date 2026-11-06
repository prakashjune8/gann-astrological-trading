"""Configures both Windows Desktop shortcuts directly to the compiled executable."""
import os
import subprocess

desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
exe_path = r"D:\ephemeris\dist\GannCelestialTrackerPro.exe"
working_dir = r"D:\ephemeris"
icon_path = r"D:\ephemeris\assets\app_icon.ico"

ps = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Desktop = "{desktop}"

$targets = @("Gann Celestial Tracker.lnk", "Gann Celestial Tracker Pro.lnk")
foreach ($t in $targets) {{
    $scPath = Join-Path $Desktop $t
    $sc = $WshShell.CreateShortcut($scPath)
    $sc.TargetPath = "{exe_path}"
    $sc.WorkingDirectory = "{working_dir}"
    $sc.IconLocation = "{icon_path}"
    $sc.Description = "Launch Gann Celestial Tracker Pro"
    $sc.Save()
    Write-Host "Configured shortcut: $scPath -> Target: $($sc.TargetPath)"
}}
"""

res = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
print(res.stdout.strip() or res.stderr.strip())
