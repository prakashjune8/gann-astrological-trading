import subprocess

ps = """
$Wsh = New-Object -ComObject WScript.Shell
$Desk = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
$Path = Join-Path $Desk 'Gann Celestial Tracker Pro.lnk'
$S = $Wsh.CreateShortcut($Path)
$S.TargetPath = 'd:\\ephemeris\\LAUNCH_APP.bat'
$S.WorkingDirectory = 'd:\\ephemeris'
$S.Description = 'Launch Gann Celestial Tracker Pro'
$S.Save()
Write-Host "Created shortcut at: $Path"
"""

res = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
print(res.stdout.strip() or res.stderr.strip())
