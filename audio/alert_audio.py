"""Audio Notification & Natural Voice Synthesis Engine.

Supports:
1. Crisp professional trading audio chimes generated via Windows Winsound / WAV generator.
2. Spoken voice announcements using Windows SAPI / PowerShell / Edge TTS.
3. Modular mute and channel control.
"""
from __future__ import annotations

import math
import os
import struct
import subprocess
import threading
import wave
from typing import Optional


class AlertAudioEngine:
    """Delivers crisp trading tones and natural spoken announcements."""

    def __init__(self, sounds_dir: Optional[str] = None):
        if sounds_dir is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sounds_dir = os.path.join(base, "audio", "sounds")
        self.sounds_dir = sounds_dir
        os.makedirs(self.sounds_dir, exist_ok=True)
        self.chime_path = os.path.join(self.sounds_dir, "pivot_chime.wav")
        self._ensure_chime_sound()

    def _ensure_chime_sound(self):
        """Generates a pleasant two-tone harmonic audio chime (A4 + E5) if not already present."""
        if os.path.exists(self.chime_path) and os.path.getsize(self.chime_path) > 100:
            return

        sample_rate = 44100
        duration_s = 0.55
        n_samples = int(sample_rate * duration_s)

        # Frequencies: 440 Hz (A4) and 659.25 Hz (E5, perfect 5th harmonic)
        f1, f2 = 440.0, 659.25
        data = bytearray()

        for i in range(n_samples):
            t = float(i) / sample_rate
            # Exponential decay envelope
            envelope = math.exp(-6.0 * t / duration_s)
            val = 0.5 * math.sin(2.0 * math.pi * f1 * t) + 0.5 * math.sin(2.0 * math.pi * f2 * t)
            sample = int(val * envelope * 24000.0)
            data.extend(struct.pack("<h", sample))

        with wave.open(self.chime_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(data)

    def play_chime_async(self):
        """Plays the professional harmonic chime non-blockingly."""
        def _play():
            try:
                import winsound
                winsound.PlaySound(self.chime_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass
        threading.Thread(target=_play, daemon=True).start()

    def speak_text_async(self, message: str):
        """Speaks the message using Windows native SAPI speech synthesis in the background."""
        def _speak():
            try:
                # Clean message for command line
                clean_msg = message.replace('"', '').replace("'", "")
                ps_script = f"""
                Add-Type -AssemblyName System.Speech
                $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
                $synth.Rate = 1
                $synth.Speak('{clean_msg}')
                $synth.Dispose()
                """
                subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                    capture_output=True,
                    timeout=10
                )
            except Exception:
                pass
        threading.Thread(target=_speak, daemon=True).start()

    def trigger_alert(self, mode: str, text_message: str):
        """Triggers alert based on active mode ('CHIME', 'VOICE', 'BOTH', 'MUTE')."""
        m = mode.upper().strip()
        if m == "MUTE":
            return
        elif m == "CHIME":
            self.play_chime_async()
        elif m == "VOICE":
            self.speak_text_async(text_message)
        elif m == "BOTH":
            self.play_chime_async()
            # Slight delay before speaking so chime is heard
            threading.Timer(0.6, lambda: self.speak_text_async(text_message)).start()
