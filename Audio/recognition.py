import os
import pyaudio
import json
from vosk import KaldiRecognizer, Model
from sys import platform

from LogSystem import recognition_logger

class VoiceOutputExeption(Exception):
    """
    Class for handling exceptions
    """
    pass


class ModelError(VoiceOutputExeption):
    """
    Raises if model is not initialized
    """
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class StreamParametersError(VoiceOutputExeption):
    """
    Raises if recognizer parameters were specified incorrectly
    """
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class Voice:
    """
    Class for recognizing user's voice
    All models taken from: https://alphacephei.com/vosk/models

    Usage example

    voice = Voice()
    voice.start_stream()
    while True:
        for word in voice.listen():
            print(word)

    """

    def __init__(self, lang="ru", big_model=False):
        # if platform == "linux" or platform == "linux2":
        #     # on some linux systems, jack_control is disabled on boot, and audio input is not working properly
        #     # if there is another audio input driver controller, it should be enabled itself
        #     os.system("jack_control start")
        self.rate = 16000
        self.init_model(lang, big_model)
        self.init_audio(16000)
        self.init_recognizer()

    def listen(self):
        """
        Generator for handling user input.
        Reads data from stream and uses recognizer to analyze the data

        """
        data = self.stream.read(4000, exception_on_overflow=False)
        # checking if data is valid
        if self.recognizer.AcceptWaveform(data) and len(data) > 1 and self.stream.is_active():
            # using json to load results of user input's analyzing
            answer = json.loads(self.recognizer.Result())
            # if user said something - it yields
            if answer['text']:
                # recognition_logger.info("Data readed and analyzed")
                yield answer['text']

    def init_model(self, model_lang="ru", big_model: bool = False):
        """
        :param model_lang: choose model's language: ru/en
        :param big_model: choose if the model is going to be big or not. ->

        Big models can take up to 8 Gb of RAM on your device, so using them might not be optimal for you
        Small models are mainly used for Android/IOS apps, they are much easier to handle,
        but they are worse at voice detection.

        """
        # default model path
        model_path = f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Speech-models/vosk-model-small-ru-0.22"

        # choosing model depending on user's choice
        if model_lang == "ru":
            model_path = f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Speech-models/vosk-model{'-small' if not big_model else ''}-ru-{'0.42' if big_model else '0.22'}"
        elif model_lang == "en":
            model_path = f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Speech-models/vosk-model{'-small' if not big_model else ''}-en-us-{'0.22' if big_model else '0.15'}"
        # initializing the model

        self.model = Model(model_path)
        recognition_logger.info("Model initialized")

    def init_audio(self, rate):
        """
        Function for initializing pyaudio stream
        :param rate: the quality of audio coming from your microphone into the system.
         rate from 16000 to 48000 doesn't really change model's behavior
        """

        p = pyaudio.PyAudio()
        self.rate = rate

        try:
            # the number of frames per buffer should preferably be half the rate value
            self.stream = p.open(format=pyaudio.paInt16, rate=rate, channels=1, frames_per_buffer=int(rate / 2), input=True)
            recognition_logger.info("stream created")
        except TypeError:
            raise StreamParametersError("Stream parameters (rate) are corrupted. Failed to open stream")

    def init_recognizer(self):
        """
        Function for initializing recognizer
        """
        try:
            self.recognizer = KaldiRecognizer(self.model, self.rate)
            recognition_logger.info("Recognizer initialized")
        except AttributeError:
            recognition_logger.error("Model error")
            raise ModelError("There was an error initializing this model")


    def start_stream(self):
        """
        Start voice input
        """
        self.stream.start_stream()
        recognition_logger.info("stream started")

    def stop_stream(self):
        """
        Stop voice input
        """
        self.stream.stop_stream()
        recognition_logger.info("stream stopped")


    def is_enabled(self):
        """
        Function for checking if the voice input is active
        """
        return self.stream.is_active()

