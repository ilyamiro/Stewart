import threading
import time

from audio import tts

from utils.text import *



def timer(**kwargs):
    timer = find_num_in_list(kwargs["command"])
    tts.say(random.choice(
        [f"Запустил таймер на {num2words(timer, lang='ru', gender='f', )} минут{get_minute_suffix(timer)}, сэр",
         f"Таймер на {num2words(timer, lang='ru', gender='f', )} минут{get_minute_suffix(timer)} запущен",
         f"Таймер на {num2words(timer, lang='ru', gender='f')} минут{get_minute_suffix(timer)} был запущен"]))
    timer_thread = threading.Timer(timer * 60, self.timers_up, args=[random.choice(
        [f"Ваш таймер на {num2words(timer, lang='ru', gender='f')} минут{get_minute_suffix(timer)} закончился!",
         f"Ваше время вышло, сэр, таймер на {num2words(timer, lang='ru', gender='f')} минут{get_minute_suffix(timer)} закончился!"])])
    timer_thread.start()


def timers_up(line: str):
    tts.say(line)
    time.sleep(3)
    playsound(f"{CWD}/data/src/ringtones/beep.wav")

