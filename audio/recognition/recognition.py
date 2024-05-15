import os
import sys
import json

from utils.sys import run

from vosk import KaldiRecognizer, Model
import pyaudio

CWD = os.path.dirname(os.path.abspath(__file__))


class stt:
    """
    Speech recognition class
    """

    def __init__(self):
        self.system()

        self.model = Model(f"{CWD}/vosk-models/vosk-model-small-ru-0.22")
        self.recognizer = KaldiRecognizer(self.model, 16000)

        p = pyaudio.PyAudio()
        self.stream = p.open(16000, 1, pyaudio.paInt16, True, frames_per_buffer=8000)

        self.stream.start_stream()

    def grammar_recognition(self, path: str) -> KaldiRecognizer:
        recognizer = KaldiRecognizer(self.model, 16000)
        with open(path, "r", encoding="utf-8") as file:
            recognizer.SetGrammar(file.readline())
        return recognizer

    @staticmethod
    def system():
        if sys.platform == "linux":
            run("jack_control", "start")

    def listen(self):
        """
        Generator for handling user input.
        Reads data from stream and uses recognizer to analyze the data

        """
        # Reading data from stream
        data = self.stream.read(4000, exception_on_overflow=False)
        # checking if data is valid
        if self.recognizer.AcceptWaveform(data) and len(data) > 1 and self.stream.is_active():
            # using json to load results of user input's analyzing
            answer = json.loads(self.recognizer.Result())
            # if user said something - it yields
            if answer['text']:
                yield answer['text']