import os
import platform
import re
import subprocess
import tempfile
import wave


class VoiceUnavailableError(RuntimeError):
    """Raised when a requested voice capability is unavailable."""


class VoiceManager:
    """Speech input/output boundary for the desktop JARVIS experience.

    Optional audio libraries are imported lazily so a missing microphone or TTS
    package can never prevent the desktop app from starting. On Windows, speech
    output also has a dependency-free System.Speech fallback.
    """

    def __init__(self):
        self.rate = int(os.getenv("JARVIS_TTS_RATE", "178"))
        self.volume = float(os.getenv("JARVIS_TTS_VOLUME", "1.0"))
        self.language = os.getenv("JARVIS_STT_LANGUAGE", "en-IN")
        self.max_speech_chars = int(os.getenv("JARVIS_TTS_MAX_CHARS", "900"))

    @staticmethod
    def clean_text(text):
        value = str(text or "").strip()
        if not value:
            return ""

        value = re.sub(r"```.*?```", " Code is shown on screen. ", value, flags=re.S)
        value = re.sub(r"`([^`]+)`", r"\1", value)
        value = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", value)
        value = re.sub(r"https?://\S+", "", value)
        value = re.sub(r"[*_#>|]", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    def speech_text(self, text):
        value = self.clean_text(text)
        if len(value) <= self.max_speech_chars:
            return value
        clipped = value[: self.max_speech_chars].rsplit(" ", 1)[0].strip()
        return clipped + ". I have put the rest of the response on screen."

    def speak(self, text):
        value = self.speech_text(text)
        if not value:
            return False

        # Prefer pyttsx3 when installed because it works offline and exposes
        # system voices. Initialize it per call; many speech drivers are thread
        # affine and should not be constructed on the Qt UI thread.
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", max(0.0, min(self.volume, 1.0)))
            engine.say(value)
            engine.runAndWait()
            engine.stop()
            return True
        except Exception:
            pass

        if platform.system() == "Windows":
            return self._speak_windows(value)

        raise VoiceUnavailableError(
            "Text-to-speech is unavailable. Install pyttsx3 or configure a supported system voice."
        )

    @staticmethod
    def _speak_windows(text):
        powershell = "powershell.exe"
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$speaker.Speak($env:JARVIS_TTS_TEXT)"
        )
        environment = os.environ.copy()
        environment["JARVIS_TTS_TEXT"] = text

        try:
            result = subprocess.run(
                [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,
                shell=False,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise VoiceUnavailableError(f"Windows speech failed: {error}") from error

        if result.returncode != 0:
            raise VoiceUnavailableError("Windows System.Speech could not synthesize audio.")
        return True

    def listen(self, duration=6):
        """Record one utterance and return recognized text.

        SpeechRecognition uses Google's recognizer for this first usable voice
        milestone. The audio capture itself is local. A local/offline STT
        adapter can replace this implementation later without changing the UI.
        """
        try:
            import sounddevice as sd
            import speech_recognition as sr
        except ImportError as error:
            raise VoiceUnavailableError(
                "Voice input dependencies are missing. Run pip install -r requirements.txt."
            ) from error

        recognizer = sr.Recognizer()
        sample_rate = 16000

        try:
            recording = sd.rec(
                int(float(duration) * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
            )
            sd.wait()
        except Exception as error:
            raise VoiceUnavailableError(f"Microphone capture failed: {error}") from error

        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = handle.name
        handle.close()

        try:
            with wave.open(temp_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(recording.tobytes())

            with sr.AudioFile(temp_path) as source:
                audio = recognizer.record(source)

            try:
                return recognizer.recognize_google(audio, language=self.language).strip()
            except sr.UnknownValueError:
                return ""
            except sr.RequestError as error:
                raise VoiceUnavailableError(
                    f"Speech recognition service is unavailable: {error}"
                ) from error
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass
