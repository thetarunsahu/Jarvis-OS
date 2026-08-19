import speech_recognition as sr
import pyttsx3
import sounddevice as sd
import numpy as np
import wave
import tempfile
import os


class VoiceManager:

    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 175)
        self.engine.setProperty("volume", 1.0)

        self.recognizer = sr.Recognizer()

    def speak(self, text):

        if not text:
            return

        print(f"JARVIS VOICE: {text}")

        self.engine.say(text)
        self.engine.runAndWait()

    def listen(self, duration=5):

        print("JARVIS: Listening...")

        sample_rate = 16000

        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16"
        )

        sd.wait()

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        )

        temp_path = temp_file.name
        temp_file.close()

        try:

            with wave.open(temp_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(recording.tobytes())

            with sr.AudioFile(temp_path) as source:
                audio = self.recognizer.record(source)

            try:

                text = self.recognizer.recognize_google(audio)

                print(f"YOU: {text}")

                return text

            except sr.UnknownValueError:

                print("JARVIS: I couldn't understand that.")

                return ""

            except sr.RequestError as error:

                print(f"Speech recognition error: {error}")

                return ""

        finally:

            if os.path.exists(temp_path):
                os.remove(temp_path)