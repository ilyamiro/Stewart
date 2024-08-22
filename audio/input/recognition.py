import logging
import os
import sys
import json

from vosk import KaldiRecognizer, Model
import pyaudio

from logs import get_logger

# file directory
DIR = os.path.dirname(os.path.abspath(__file__))

logger = get_logger("audio input")


class STT:
    def __init__(self):
        self.pyaudio_instance = pyaudio.PyAudio()
        logger.info("PyAudio instance created")

        self.stream = self.pyaudio_instance.open(rate=16000, channels=1, format=pyaudio.paInt16, input=True,
                                                 frames_per_buffer=8000)
        logger.debug("PyAudio stream instance successfully opened for input")

        self.model = Model(f"{DIR}/models/vosk-model-small-ru-0.22")
        self.recognizer = KaldiRecognizer(self.model, 16000)

        logger.debug("Vosk recognition system initialized")

    def listen(self):
        data = self.stream.read(4000, exception_on_overflow=False)
        if self.recognizer.AcceptWaveform(data) and len(data) > 1 and self.stream.is_active():
            answer = json.loads(self.recognizer.Result())
            if answer["text"]:
                logger.info(f"Text recognized in input stream: {answer['text']}")
                yield answer["text"]




