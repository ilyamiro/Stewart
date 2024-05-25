# Standard library imports
import json
import os
import random
import subprocess
import signal
import sys
import time
import threading
import datetime
import webbrowser
from multiprocessing import Pipe, Process, Queue

# Third-party imports
from playsound import playsound
from pyrogram import Client, filters
import clipman
import pyautogui
from num2words import num2words
import g4f
import psutil
from pymouse import PyMouse
import screen_brightness_control as sbc
from pynput.keyboard import Controller

# Local/project-specific imports
from audio import tts
from audio import stt as STT
from utils.sys import config_load, run, config_dump
from utils.text import *
from utils.some import half_hour_passed
from .data import Tree
from .data.scripts.telegram import start_bot

# Environment variables setup
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame.mixer

CWD = os.path.dirname(os.path.abspath(__file__))


def _init():
    clipman.init()
    pygame.mixer.init()


_init()


class Core:
    def __init__(self):
        # Start-up Music
        playsound(f"{CWD}/data/src/ringtones/startup.wav", block=False)

        # Threads Initialization
        self.music_thread = None
        self.recognition_thread = None
        self.telegram_thread = None

        # Stopwatch Initialization
        self.stopwatch_end = None
        self.stopwatch_enabled = None
        self.stopwatch_start = None

        # Configuration Loading
        self.config = config_load(f"{CWD}/config.json")
        self.answers = config_load(f"{CWD}/data/json/answers.json")
        self.obj = config_load(f"{CWD}/data/json/obj.json")

        # System Initialization
        self.sys()

        # Chatbot History Initialization
        self.gpt_history = []
        self.gpt_start = []  # Reserved for future prompt
        self.message_history = []

        # Command Loading
        self.tree = Tree()
        self._load_commands()
        self._load_commands_repeat()

        # STT Initialization
        self.tts = tts
        self.stt = STT()
        self.keyboard = Controller()
        self.mouse = PyMouse()

        # Telegram User script Pipe connection
        self.core_pipe, self.telegram_pipe = Pipe()
        self.last_message = None

        self.tg_userbot = Process(target=start_bot, args=(self.telegram_pipe,))
        self.tg_userbot.start()

        self.telegram_thread = threading.Thread(target=self.monitor)
        self.telegram_thread.start()

        # STT Grammar Recognition
        self._create_grammar_recognition()
        self.stt_grammar = self.stt.grammar_recognition(f"{CWD}/data/grammar.txt")

        # STT Current Grammar
        self.stt.current = self.stt_grammar

        # Voice Assistant Ready Message
        self.tts.say("Конфигурация ядра успешно завершена. Голосовой ассистент готов к работе")

    def monitor(self):
        while True:
            self.last_message = self.core_pipe.recv()
            self.tts.say(
                f"У вас одно новое сообщение от {self.last_message.from_user.first_name} {self.last_message.from_user.last_name}")

    def _load_commands(self):
        with open(f"{CWD}/data/json/commands.json", "r", encoding="utf-8") as file:
            commands = json.load(file).get("commands")
            for command in commands:
                equiv = command.get('equivalents', {})
                if equiv:
                    for eq in equiv:
                        equiv[equiv.index(eq)] = tuple(eq)
                self._add_command(
                    tuple(command['command']),
                    command['action'],
                    command.get('parameters'),
                    command.get('responses', []),
                    command.get('synonyms', {}),
                    equiv
                )

    def _load_commands_repeat(self):
        with open(f"{CWD}/data/json/commands.json", "r", encoding="utf-8") as file:
            commands_repeat = json.load(file).get("repeat")
            for repeat in commands_repeat:
                for key in repeat.get("links"):
                    self._add_command(
                        (*repeat.get("command"), key),
                        repeat.get("action"),
                        {repeat.get("parameter"): repeat.get("links").get(key)},
                        self.answers.get("confirmative"),
                        repeat.get("synonyms"),
                    )

    def _create_grammar_recognition(self):
        with open(f"{CWD}/data/grammar.txt", "w") as file:
            file.write('["')
            file.write(" ".join(self.config.get("triggers")))
            file.write(
                " одну две один два три четыре пять шесть семь восемь девять десять одиннадцать двенадцать тринадцать четырнадцать пятнадцать шестнадцать семнадцать восемнадцать девятнадцать двадцать тридцать сорок пятьдесят шестьдесят семьдесят восемьдесят девяносто сто минуты минуту минут час часа часов секунд секунда")
            file.write(self.tree.recognizer_string)
            file.write('"]')

    @staticmethod
    def sys():
        if sys.platform == "linux":
            run("xhost", "+local:$USER")

    def start(self):
        self.recognition_thread = threading.Thread(target=self.recognition)
        self.recognition_thread.start()

    def recognition(self):
        # if condition is True, while cycle goes without not, if False - with not,
        while True:
            for word in self.stt.listen():
                print(word)
                result = self._remove_trigger_word(word)
                if result != "blank":
                    self.handle(result)

    def _add_command(self, command: tuple, handler: str, parameters: dict = None, synthesize: list = None,
                     synonyms: dict = None, equivalents: list = None):
        if not synonyms:
            synonyms = {}
        if not synthesize:
            synthesize = []
        if not parameters:
            parameters = {}
        if not equivalents:
            equivalents = []
        self.tree.add_commands(
            {command: {"handler": handler, "parameters": parameters, "synthesize": synthesize, "synonyms": synonyms,
                       "equivalents": equivalents}})

    def _remove_trigger_word(self, request):
        for trigger in self.config.get("triggers"):
            if trigger in request:
                request = " ".join(request.split(trigger)[1:])[1:]
                return request
        return "blank"

    def history_update(self, command):
        self.message_history.append(command)

        if len(self.message_history) > 2:
            self.message_history.pop(0)

    def handle(self, request):
        self.history_update(request)
        if not request:
            self.tts.say(random.choice(self.answers.get("default")))
        else:
            total = self._multihandle(request)
            if len(total) == 1:
                result = self.tree.find_command(total[0])
                if result:
                    res = list(result)
                    res.extend([total[0], request])
                    self._synth_handle(res)
            elif len(total) > 1:
                self.tts.say(random.choice(self.answers.get("confirmative")))
                for command in total:
                    result = self.tree.find_command(command)
                    if result:
                        res = list(result)
                        res.extend([command, request])
                        self._just_handle(res)
            elif not total:
                if self.config.get("gpt"):
                    answer = self.answer_gpt(request)
                    self.tts.say(answer)

    def _synth_handle(self, request):
        @self._synthesis_dec(request[2])
        def do():
            self._just_handle(request)

        do()

    def _just_handle(self, request):
        if request[0]:
            thread = threading.Thread(target=getattr(self, request[0]),
                                      kwargs={"parameters": request[1], "command": request[3],
                                              "request": request[4]})
            thread.start()

    def _synthesis_dec(self, to_say):
        def decorator(func):
            def wrapper():
                if to_say:
                    self.tts.say(random.choice([*to_say, random.choice(self.answers.get("confirmative"))]))
                func()

            return wrapper

        return decorator

    def _multihandle(self, request):
        list_of_commands, current_command = [], []
        split_request = request.split()
        for word in split_request:
            if word in self.tree.first_words:
                if current_command:
                    list_of_commands.append(current_command)
                if word in ["найди", "найти", "напиши", "запиши", "скажи"]:
                    current_command = split_request[split_request.index(word):]
                    list_of_commands.append(current_command)
                    current_command = []
                    break
                current_command = [word]
            else:
                if current_command and word != "и":
                    current_command.append(word)
                elif not current_command and word != "и":
                    pass
        if current_command:
            list_of_commands.append(current_command)
        return list_of_commands

    @staticmethod
    def subprocess(**kwargs):
        subprocess.run(
            kwargs["parameters"]["command"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

    def quote(self, **kwargs):
        random_ = random.choice(list(quotes.keys()))
        self.tts.say(f"Как говорил {random_}, {quotes[random_]}")

    @staticmethod
    def hotkey(**kwargs):
        pyautogui.hotkey(*kwargs["parameters"]["hotkey"])

    @staticmethod
    def key(**kwargs):
        pyautogui.press(kwargs["parameters"]["key"])

    @staticmethod
    def webbrowser(**kwargs):
        webbrowser.open(kwargs["parameters"]["url"])

    @staticmethod
    def system(**kwargs):
        os.system(kwargs.get("parameters").get("command"))

    def switch_recognizer(self, **kwargs):
        restricted = kwargs.get("parameters").get("restricted")
        self.stt.current = self.stt_grammar if restricted else self.stt.recognizer

    def answer_gpt(self, query):
        answer = g4f.ChatCompletion.create(
            messages=[*self.gpt_start, *self.gpt_history, {"role": "user", "content": query}],
            provider=g4f.Provider.You,
            stream=False,
            model=g4f.models.default
        )
        self.gpt_history.extend([{"role": "user", "content": query}, {"role": "system", "content": answer}])
        if len(self.gpt_history) >= 10:
            self.gpt_history.pop(0)
            self.gpt_history.pop(0)

        answer = numbers_to_strings(answer)
        return answer

    @staticmethod
    def brightness(**kwargs):
        num = find_num_in_list(kwargs["command"])
        if num:
            if kwargs["parameters"]["command"] == "set":
                sbc.set_brightness(num)
            else:
                sbc.set_brightness(
                    sbc.get_brightness()[0] + (+num if kwargs["parameters"]["command"] == "up" else -num))
        else:
            sbc.set_brightness(sbc.get_brightness()[0] + (+25 if kwargs["parameters"]["command"] == "up" else -25))

    def combination(self, **kwargs):
        for command in kwargs["parameters"]["combination"]:
            getattr(self, command["name"])(parameters=command["parameters"])

    def read_tg(self, **kwargs):
        if half_hour_passed(self.last_message.date):
            self.tts.say(
                random.choice(["В последний час новых сообщений не поступало, сэр", "Список входящих пуст, сэр"]))
        else:
            self.tts.say(
                f"... {self.last_message.from_user.first_name} {self.last_message.from_user.last_name or ''} пишет. {self.last_message.text}",
                prosody=89)

    def click(self, **kwargs):
        num = find_num_in_list(kwargs["command"])
        if num:
            self.mouse.click(*self.mouse.position(), n=num)
        else:
            self.mouse.click(*self.mouse.position())

    def neuro_switch(self, **kwargs):
        if kwargs["parameters"]["way"] == "on":
            self.config["gpt"] = True
            self.stt.current = self.stt.recognizer
        if kwargs["parameters"]["way"] == "off":
            self.config["gpt"] = False
        config_dump(f"{CWD}/config.json", self.config)

    @staticmethod
    def play_audio(**kwargs):
        path = kwargs.get("parameters").get("path")
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()

    @staticmethod
    def kill_audio(**kwargs):
        pygame.mixer.music.stop()

    @staticmethod
    def volume(**kwargs):
        num = find_num_in_list(kwargs["command"])
        current = os.popen('amixer get Master | grep -oP "\[\d+%\]"').read()
        current = int(current.split()[0][1:-2])
        if num:
            if kwargs["parameters"]["command"] == "set":
                os.system(f"amixer set 'Master' {num}% /dev/null 2>&1")
            else:
                os.system(
                    f"amixer set 'Master' {current + num if kwargs['parameters']['command'] == 'up' else current - num}% > /dev/null 2>&1")
        else:
            os.system(
                f'amixer set "Master" {current + 25 if kwargs["parameters"]["command"] == "up" else current - 25}% > /dev/null 2>&1')

    def stopwatch(self, **kwargs):
        if kwargs["parameters"]["way"] == "start":
            self.stopwatch_start = datetime.datetime.now()
            self.stopwatch_enabled = True
        if kwargs["parameters"]["way"] == "stop" and self.stopwatch_start and self.stopwatch_enabled:
            self.stopwatch_enabled = False
            self.stopwatch_end = datetime.datetime.now()
            passed = self.stopwatch_end - self.stopwatch_start
            hour, minute, second = passed.seconds // 3600, (passed.seconds % 3600) // 60, passed.seconds % 60
            self.tts.say(
                f"Прошло {num2words(hour, lang='ru') if hour != 0 else ''} {'час' + get_hour_suffix(hour) if hour != 0 else ''}, {num2words(minute, lang='ru') if minute != 0 else ''} {'минут' + get_minute_suffix(minute) if minute != 0 else ''} {num2words(second, lang='ru') if second != 0 else ''} {'секунд' + get_second_suffix(second) if second != 0 else ''}")
        elif kwargs["parameters"]["way"] == "stop" and not self.stopwatch_enabled:
            self.tts.say(random.choice(["Секундомер не запущен", "Секундомер выключен"]))

    def timer(self, **kwargs):
        timer = find_num_in_list(kwargs["command"])
        self.tts.say(random.choice(
            [f"Запустил таймер на {num2words(timer, lang='ru', gender='f', )} минут{get_minute_suffix(timer)}, сэр",
             f"Таймер на {num2words(timer, lang='ru', gender='f', )} минут{get_minute_suffix(timer)} запущен",
             f"Таймер на {num2words(timer, lang='ru', gender='f')} минут{get_minute_suffix(timer)} был запущен"]))
        timer_thread = threading.Timer(timer * 60, self.timers_up, args=[random.choice(
            [f"Ваш таймер на {num2words(timer, lang='ru', gender='f')} минут{get_minute_suffix(timer)} закончился!",
             f"Ваше время вышло, сэр, таймер на {num2words(timer, lang='ru', gender='f')} минут{get_minute_suffix(timer)} закончился!"])])
        timer_thread.start()

    def timers_up(self, line: str):
        self.tts.say(line)
        time.sleep(3)
        playsound(f"{CWD}/data/src/ringtones/beep.wav")

    @staticmethod
    def move(**kwargs):
        way = kwargs["parameters"]["way"]
        num = find_num_in_list(kwargs["command"])
        match way:
            case "up":
                pyautogui.moveRel(yOffset=-num if num else -500, xOffset=0)
            case "down":
                pyautogui.moveRel(yOffset=num if num else 500, xOffset=0)
            case "right":
                pyautogui.moveRel(xOffset=num if num else 500, yOffset=0)

            case "left":
                pyautogui.moveRel(xOffset=-num if num else -500, yOffset=0)

    @staticmethod
    def num_key(**kwargs):
        num = find_num_in_list(kwargs["command"])
        if num:
            pyautogui.press(kwargs["parameters"]["key"], presses=num)
        else:
            pyautogui.press(kwargs["parameters"]["key"])

    @staticmethod
    def num_hotkey(**kwargs):
        num = find_num_in_list(kwargs["command"])
        if num:
            for i in range(num):
                pyautogui.hotkey(*kwargs["parameters"]["hotkey"])
        else:
            pyautogui.press(*kwargs["parameters"]["hotkey"])

    @staticmethod
    def end(**kwargs):
        time.sleep(3)
        os.kill(os.getpid(), signal.SIGINT)

    def clear_neuro(self, **kwargs):
        self.gpt_history = []

    @staticmethod
    def wait(**kwargs):
        time.sleep(kwargs["parameters"]["time"])

    @staticmethod
    def write(**kwargs):
        to_write = " ".join(kwargs["command"][1:])
        clipman.copy(to_write)
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "v")

    @staticmethod
    def delete_text(**kwargs):
        if kwargs["parameters"]["way"] == "one":
            pyautogui.hotkey("ctrl", "backspace")
        else:
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")

    def cpu_load(self, **kwargs):
        self.tts.say(f"Ваш процессор загружен на {num2words(psutil.cpu_percent(0.2), lang='ru')} процента, сэр")

    def battery_percentage(self, **kwargs):
        self.tts.say(
            f"Ваша батарея заряжена на {num2words(int(psutil.sensors_battery().percent), lang='ru')} процентов. " + random.choice(
                ["Кабель зарядки подключен", "Питание от сети активно",
                 "Зарядное устройство подключено"]) if psutil.sensors_battery().power_plugged else "" + ", сэр")

    def ram_load(self, **kwargs):
        self.tts.say(
            f"Ваша оперативная память загружена на {num2words(psutil.virtual_memory().percent, lang='ru')} процента, сэр")

    def power_off(self, **kwargs):
        if kwargs["parameters"]["way"] == "off":
            num = find_num_in_list(kwargs["command"])
            if num:
                self.tts.say(
                    f"Выключение компьютера произойдет через {num2words(num, lang='ru')} минут{get_minute_suffix(num)}, сэр")
                os.system(f'shutdown -h +{num} /dev/null 2>&1')
            else:
                msg = "Выключение компьютера произойдет через одну минуту, сэр"
                os.system(f'sudo shutdown -h +1 /dev/null 2>&1')
                self.tts.say(msg)
        elif kwargs["parameters"]["way"] == "now":
            thread = threading.Timer(2.5, os.system, args=["sudo shutdown now"])
            thread.start()
        else:
            self.tts.say("Выключение компьютера отменено")
            os.system("sudo shutdown -c /dev/null 2>&1")

    def power_reload(self, **kwargs):
        if kwargs["parameters"]["way"] == "off":
            num = find_num_in_list(kwargs["command"])
            if num:
                self.tts.say(
                    f"Перезагрузка компьютера произойдет через {num2words(num, lang='ru')} минут{get_minute_suffix(num)}, сэр")
                os.system(f'shutdown -r -h +{num} /dev/null 2>&1')
            else:
                msg = "Перезагрузка компьютера произойдет через одну минуту, сэр"
                os.system(f'sudo shutdown -r -h +1 /dev/null 2>&1')
                self.tts.say(msg)
        elif kwargs["parameters"]["way"] == "now":
            thread = threading.Timer(2.5, os.system, args=["sudo shutdown -r now"])
            thread.start()
        else:
            self.tts.say("Перезагрузка компьютера отменена")
            os.system("sudo shutdown -c /dev/null 2>&1")

    def capslock(self, **kwargs):
        if get_capslock_state():
            self.tts.say("Капслок уже включен, сэр")
        else:
            self.tts.say("Выполнил, сэр")
            pyautogui.press("capslock")

    def repeat(self, **kwargs):
        self.handle(self.message_history[-2])

    def find_link(self, **kwargs):
        search = "+".join(kwargs["command"][2:])

        url = "https://html.duckduckgo.com/html/?"
        params = {'q': search}

        self.tts.say(f"Вот, что мне удалось найти по запросу {search}")

        def fetch_first_link(a, symbol):
            params['q'] = params['q'].format(symbol)
            res = a.get(url, params=params)
            soup = BeautifulSoup(res.text, "lxml")
            return soup.select_one(".result__title > a.result__a").get("href")

        with requests.Session() as s:
            s.headers[
                'User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36'
            webbrowser.open(fetch_first_link(s, 'reliance'))

    def find_info(self, **kwargs):
        self.tts.say("Ищу источники информации, сэр")
        search = "+".join(kwargs["command"][2:])

        url = "https://html.duckduckgo.com/html/?"
        params = {'q': search}

        def fetch_first_link(a, symbol):
            params['q'] = params['q'].format(symbol)
            res = a.get(url, params=params)
            soup = BeautifulSoup(res.text, "lxml")
            # return soup.select_one(".result__title > a.result__a").get("href")
            found = soup.select(".result__title > a.result__a", limit=5)
            return found[0]

        with requests.Session() as s:
            s.headers[
                'User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36'
            link = str(fetch_first_link(s, 'reliance').get("href"))
            subprocess.run(["node", f"{CWD}/data/scripts/node.js", link])

            with open("text.txt", "r", encoding="utf-8") as file:
                self.tts.say("Нашел источник, анализирую")
                answer = g4f.ChatCompletion.create(
                    messages=[{"role": "user",
                               "content": f"Коротко просуммируй все сказанное далее: {file.read().split()[:90]}"}],
                    provider=g4f.Provider.You,
                    stream=False,
                    model=g4f.models.default
                )
                self.tts.say(numbers_to_strings(answer))

    def find_video(self, **kwargs):
        search = "+".join(kwargs["command"][2:])
        html = urllib.request.urlopen(f"https://www.youtube.com/results?search_query={quote(search)}")
        video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
        if video_ids:
            webbrowser.open("https://www.youtube.com/watch?v=" + video_ids[0], autoraise=True)
        else:
            self.tts.say("Я не смог найти подходящее видео, или произошла ошибка, сэр")

    def find(self, **kwargs):
        to_find = " ".join(kwargs["command"][1:])

        def _find(query, site):
            self.tts.say("Вот что мне удалось найти по запросу" + to_find)
            webbrowser.open(site + query, autoraise=True)

        def remove_word(word, text):
            for _ in text.split():
                if word in _:
                    return text.replace(_, "")

        if "яндекс" in to_find:
            to_find = remove_word("яндекс", to_find)
            _find(to_find, "https://yandex.ru/search/?text=")
        elif "ютуб" in to_find:
            to_find = remove_word("ютуб", to_find)
            _find(to_find, "https://www.youtube.com/results?search_query=")
        else:
            _find(to_find, "https://duckduckgo.com/?q=")

    @staticmethod
    def scroll(**kwargs):
        match kwargs["parameters"]["way"]:
            case "up":
                mouse.wheel(1)
            case "down":
                mouse.wheel(-1)

    def say_same(self, **kwargs):
        self.tts.say(" ".join(kwargs["command"][1:]))

    def random_number(self, **kwargs):
        num = find_num_in_list(kwargs["command"])
        if isinstance(num, tuple):
            self.tts.say(num2words(random.randint(min(num), max(num)), lang='ru') + ", сэр")
        else:
            self.tts.say("Назовите два числ+а, сэр")

    def tell_date(self, **kwargs):
        now = datetime.datetime.now()
        date = f"Сегодня {num2words(now.day, lang='ru', ordinal=True, gender='n')} {self.obj.get('months').get(now.strftime('%B').lower())}" + random.choice(
            ["", f" {num2words(now.year, lang='ru', ordinal=True, case='р')} года"])
        self.tts.say(date)

    def tell_time(self, **kwargs):
        hour = datetime.datetime.now().hour
        minute = datetime.datetime.now().minute
        self.tts.say(
            f"Сейчас {num2words(hour, lang='ru')} час+{get_hour_suffix(hour)} и {num2words(minute, gender='f', lang='ru')} минут{get_minute_suffix(minute)}")
