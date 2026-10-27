---
name: Skill_5_Desktop_App_Deployment
description: Package a Python CustomTkinter/PyQt5 (or Electron.js) desktop app into a standalone Windows executable with PyInstaller. Use when building or distributing the app.
---

# Skill 5 – Desktop App Deployment

## PyInstaller (Python / CustomTkinter)
```powershell
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name GannCelestialTimer `
    --collect-all customtkinter --add-data "holidays.json;." main.py
```
* `--collect-all customtkinter` is mandatory: CTk ships JSON themes/assets that PyInstaller misses.
* `--add-data "src;dest"` uses `;` on Windows, `:` on macOS/Linux.
* At runtime resolve bundled files via `getattr(sys, "_MEIPASS", base_dir)`; write user data
  (cache, editable holidays) to `%LOCALAPPDATA%\<App>` – never inside the bundle.
* Output: `dist\GannCelestialTimer.exe`. Test on a clean machine; Defender may flag unsigned one-file exes
  (use `--onedir` or code-signing if needed).

## PyQt5 variant
Same command without `--collect-all customtkinter` (PyInstaller has built-in Qt hooks).

## Electron variant
`npm i -D electron-builder` → `"build": {"win": {"target": "nsis"}}` → `npx electron-builder --win`.
