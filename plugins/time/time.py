import threading
import time
import random
from datetime import datetime 

from num2words import num2words
from playsound import playsound

from audio import tts
from utils.text import *

stopwatch_enabled = False
stopwatch_start = None
stopwatch_end = None



def tell_date(**_):
    now = datetime.now()
    date = f"Сегодня {num2words(now.day, lang='ru', ordinal=True, gender='n')} {obj.get('months').get(now.strftime('%B').lower())}" + random.choice(
        ["", f" {num2words(now.year, lang='ru', ordinal=True, case='р')} года"])
    tts.say(date)


def tell_time(**_):
    hour = datetime.now().hour
    minute = datetime.now().minute
    tts.say(
        f"Сейчас {num2words(hour, lang='ru')} час+{get_hour_suffix(hour)} и {num2words(minute, gender='f', lang='ru')} минут{get_minute_suffix(minute)}")


def timer(**kwargs):
    pace = find_num_in_list(kwargs["command"])
    tts.say(random.choice(
        [f"Запустил таймер на {num2words(pace, lang='ru', gender='f', )} минут{get_minute_suffix(pace)}, сэр",
         f"Таймер на {num2words(pace, lang='ru', gender='f', )} минут{get_minute_suffix(pace)} запущен",
         f"Таймер на {num2words(pace, lang='ru', gender='f')} минут{get_minute_suffix(pace)} был запущен"]))
    timer_thread = threading.Timer(pace * 60, timers_up, args=[random.choice(
        [f"Ваш таймер на {num2words(pace, lang='ru', gender='f')} минут{get_minute_suffix(pace)} закончился!",
         f"Ваше время вышло, сэр, таймер на {num2words(pace, lang='ru', gender='f')} минут{get_minute_suffix(pace)} закончился!"])])
    timer_thread.start()


def timers_up(line: str):
    tts.say(line)
    time.sleep(3)
    playsound(f"{CWD}/data/src/ringtones/beep.wav")


def stopwatch(**kwargs):
    global stopwatch_enabled, stopwatch_start, stopwatch_end
    if kwargs["parameters"]["way"] == "start":
        stopwatch_start = datetime.datetime.now()
        stopwatch_enabled = True
    if kwargs["parameters"]["way"] == "stop" and stopwatch_start and stopwatch_enabled:
        stopwatch_enabled = False
        stopwatch_end = datetime.datetime.now()
        passed = stopwatch_end - self.stopwatch_start
        hour, minute, second = passed.seconds // 3600, (passed.seconds % 3600) // 60, passed.seconds % 60
        tts.say(
            f"Прошло {num2words(hour, lang='ru') if hour != 0 else ''} {'час' + get_hour_suffix(hour) if hour != 0 else ''}, {num2words(minute, lang='ru') if minute != 0 else ''} {'минут' + get_minute_suffix(minute) if minute != 0 else ''} {num2words(second, lang='ru') if second != 0 else ''} {'секунд' + get_second_suffix(second) if second != 0 else ''}")
    elif kwargs["parameters"]["way"] == "stop" and not stopwatch_enabled:
        tts.say(random.choice(["Секундомер не запущен", "Секундомер выключен"]))
