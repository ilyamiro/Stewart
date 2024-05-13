import threading

from voicesynth import Model, Synthesizer


class tts:
    def __init__(self):
        self.model = Model("v4_ru", "models/v4_ru.pt")
        self.model.set_speaker("eugene")
        self.synthesizer = Synthesizer(self.model)

    def say(self, text):
        thread = threading.Thread(target=self.synthesizer.say, kwargs={"text": text, "path": "audio.wav"})
        thread.start()


