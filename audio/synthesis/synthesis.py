import threading
import os

from voicesynth import Model, Synthesizer

CWD = os.path.dirname(os.path.abspath(__file__))


class tts:
    def __init__(self):
        self.model = Model("v4_ru", f"{CWD}/models/v4_ru.pt")
        self.model.set_speaker("eugene")

        self.synthesizer = Synthesizer(self.model)

        self.working = True

    def say(self, text, prosody: int = 94):
        """
        Say some text
        """
        if self.working:
            thread = threading.Thread(target=self.synthesizer.say, kwargs={"text": text, "path": f"{CWD}/audio.wav", "prosody_rate": prosody})
            thread.start()

    def turn_off(self):
        self.working = False

    def turn_on(self):
        self.working = True

    def switch(self):
        self.working = not self.working

