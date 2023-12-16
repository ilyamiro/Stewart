# code author: @ilyamiro.workemail@gmail.com

import os
import time
from LogSystem.Loggers import synthesis_logger

import pygame
import torch


class SynthesizerError(Exception):
    """
    Base class for exceptions related to the Synthesizer.
    """
    pass


class SpeakerInvalid(SynthesizerError):
    """
    Exception raised when speaker isn't on the list of available ones
    """

    def __init__(self, message="Speaker should be one of these: eugene; kseniya; baya; xenia; aidar; random;"):
        self.message = message
        super().__init__(self.message)


class SynthesisError(SynthesizerError):
    """
    When the synthesizer fails to say the text
    """

    def __init__(self, message="There was an error synthesizing this text"):
        self.message = message
        super().__init__(self.message)


class PlayingError(SynthesizerError):
    """
    When the synthesizer fails to say the text
    """

    def __init__(self, message="There was an error while playing the synthesized audio"):
        self.message = message
        super().__init__(self.message)


class Synthesizer:
    """
    Class for synthesizing Stewart voice
    Based on silero-tts v4 model from https://github.com/snakers4/silero-models
    """

    def __init__(self, speaker="eugene"):
        """
        Synthesizer initializing
        :param speaker: One of eugene; kseniya; baya; xenia; aidar; random;
        """
        # initialize pygame for playing audio
        self.audio_init()

        # initialize sample rate and the speaker_voice

        self.sample_rate = 48000
        self.speaker = speaker

        # initialization for torch package
        self.device = torch.device("cpu")
        torch.set_num_threads(32)

        # downloading model from source
        self.local_file = "model.pt"
        self.download_model()

        # creating model
        self.model = torch.package.PackageImporter(
            f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Audio/model.pt").load_pickle("tts_models",
                                                                                                   "model")
        self.model.to(self.device)
        synthesis_logger.info("Model has beed set")

        # setting audio state checker for synthesizer
        self.audio = PlayChecker()

        self.music_playing = False
        self.music_stopped = True

    def download_model(self, url="https://models.silero.ai/models/tts/ru/v4_ru.pt"):
        """
        Function for downloading voice model
        :param url: address for downloading voice model
        """
        # downloading model from source
        if not os.path.isfile(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Audio/model.pt"):
            synthesis_logger.info("Downloading synthesis model")
            torch.hub.download_url_to_file(url, self.local_file)

    @staticmethod
    def audio_init():
        """
        Function for initializing pygame audio player

        """
        pygame.init()
        pygame.mixer.init()
        synthesis_logger.debug("Audio initialized")

    def say(self, text: str) -> None:
        """
        Function for saying something
        :param text: text for saying
        :return: None
        """
        self.synthesize(text)
        # playing audio from file using pygame.
        # playsound() could be used instead, but it doesn't really imply stop() func, while pygame does
        try:
            pygame.mixer.music.load(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Audio/audio.wav")
            pygame.mixer.music.play()
        except pygame.error:
            synthesis_logger.error("Audio playing error")

    def synthesize(self, text: str) -> None:
        if self.music_stopped:
            # synthesizing voice
            try:
                self.model.save_wav(ssml_text=f"<speak><prosody rate='100%'>{text}</prosody></speak>",
                                    speaker=self.speaker,

                                    sample_rate=self.sample_rate,
                                    audio_path=f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Audio/audio.wav")  # ssml text supports a lot of parameters, such as intonation, pauses etc.
            except AssertionError:
                raise SpeakerInvalid
            except Exception:
                raise SynthesisError

    @staticmethod
    def is_saying() -> bool:
        """
        Function for checking if synthesized audio is being played
        :return: checks if stewart is saying something. Returns True if yes, else False
        """
        return pygame.mixer.music.get_busy()

    def change_speaker(self, speaker: str):
        """
        Function for changing voice model's speaker
        :param speaker: speaker name. One of eugene; kseniya; baya; xenia; aidar; random;
        """
        self.speaker = speaker

    def change_sample_rate(self, rate: int):
        """
        Function for changing voice model's rate
        :param rate: rate of a synthesizer model

        """
        self.sample_rate = rate


class PlayChecker:
    @staticmethod
    def set_volume(volume: float):
        """
        Function for setting the volume of the voice synthesizer.
        :param volume: A float value between 0.0 and 1.0.
        """
        pygame.mixer.music.set_volume(volume)

    @staticmethod
    def pause_audio():
        """
        Function to pause the voice synthesizer playback.
        """
        pygame.mixer.music.pause()

    @staticmethod
    def resume_audio():
        """
        Function to resume the voice synthesizer playback.
        """
        pygame.mixer.music.unpause()

    @staticmethod
    def stop():
        """
        Function to stop the voice synthesizer playback.
        """
        pygame.mixer.music.stop()

    @staticmethod
    def play_default():
        pygame.mixer.music.unload()
        pygame.mixer.music.load(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Audio/audio.wav")
        pygame.mixer.music.play()
