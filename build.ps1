# Skill 5 - build a standalone Windows executable (dist\GannCelestialTimer.exe)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name GannCelestialTimer `
    --collect-all customtkinter `
    --add-data "holidays.json;." `
    main.py
Write-Host "Built: $PSScriptRoot\dist\GannCelestialTimer.exe"
