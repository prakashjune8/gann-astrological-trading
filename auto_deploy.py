import PyInstaller.__main__
import customtkinter
import os
import subprocess
import sys

def build_and_launch():
    print("Initiating build sequence for Gann Celestial Tracker...")
    customtkinter_path = os.path.dirname(customtkinter.__file__)
    
    # PyInstaller build command
    PyInstaller.__main__.run([
        'main.py', # Ensure this matches the primary script name
        '--name=GannCelestialTracker',
        '--windowed',
        '--onedir',
        '--noconfirm',
        '--clean',
        f'--add-data={customtkinter_path};customtkinter/',
        '--hidden-import=astroquery',
        '--hidden-import=astropy'
    ])
    
    # Path to the newly built executable
    exe_path = os.path.join(os.getcwd(), 'dist', 'GannCelestialTracker', 'GannCelestialTracker.exe')
    
    if os.path.exists(exe_path):
        print(f"Build successful. Launching application from: {exe_path}")
        subprocess.Popen([exe_path])
    else:
        print("Error: Executable not found. Build may have failed.")
        sys.exit(1)

if __name__ == "__main__":
    build_and_launch()
