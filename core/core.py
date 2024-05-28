# Standard library imports
import json
import logging
import os
import subprocess
import signal
import sys
import random
import time
import threading
import inspect
from multiprocessing import Pipe, Process

# Third-party imports
from playsound import playsound

import g4f
from pyrogram import Client

# Local/project-specific imports
from audio import tts
from audio import stt as STT
from utils.sys import config_load, run, config_dump
from utils.some import half_hour_passed
from tree import Tree
from core.data.connections.telegram.telegram import start_bot
from logs import log
from plugins import Loader

CWD = os.path.dirname(os.path.abspath(__file__))



class Core:
    def __init__(self):
        # Start-up Music
        playsound(f"{CWD}/data/src/ringtones/startup.wav", block=False)

        log.info("Start-up sound played")

        # Threads Initialization
        self.music_thread = None
        self.recognition_thread = None
        self.telegram_thread = None

        # Stopwatch Initialization
        self.trigger_required = True
        self.stopwatch_end = None
        self.stopwatch_enabled = None
        self.stopwatch_start = None

        # Configuration Loading
        self.config = config_load(f"{CWD}/config.json")
        self.answers = config_load(f"{CWD}/data/json/answers.json")

        log.info("Configuration files loaded")

        # System Initialization
        self.sys()

        # Chatbot History Initialization
        self.gpt_history = []
        self.gpt_start = []  # Reserved for future prompt
        self.message_history = []

        # Command Loading
        self.loader = Loader()
        self.architecture = self.loader.architecture

        self.load_default_commands()

        log.debug("Command Tree initialized and plugins loaded")

        self.stt = STT()

        log.debug("Speech to text initialized")

        # Telegram User script Pipe connection
        self.core_pipe, self.telegram_pipe = Pipe()
        self.last_tg_message = None

        self.tg_userbot = Process(target=start_bot, args=(self.telegram_pipe,))
        self.tg_userbot.start()

        self.telegram_thread = threading.Thread(target=self.monitor)
        self.telegram_thread.start()

        log.debug("Telegram user-bot pipes established, process started")

        # STT Grammar Recognition
        self._create_grammar_recognition()
        self.stt_grammar = self.stt.grammar_recognition(f"{CWD}/data/grammar.txt")
        self.stt.current = self.stt_grammar

        log.info("Restricted stt recognizer created. grammar.txt updated")

        # Voice Assistant Ready Message
        tts.say("Конфигурация ядра успешно завершена. Голосовой ассистент готов к работе")

        log.info("Voice assistant ready message played")


    def load_default_commands(self):
        with open(f"{CWD}/data/json/core_commands.json", "r", encoding="utf-8") as file:
            data = json.load(file)
            self.loader.load_commands(data.get("combination"))
            self.loader.load_commands(data.get("commands"))
            self.loader.load_commands_repeat(data.get("repeat"))
        self.tree = self.loader.get_tree()

    def monitor(self):
        while True:
            self.last_tg_message = self.core_pipe.recv()
            tts.say(
                f"У вас одно новое сообщение от {self.last_tg_message.from_user.first_name} {self.last_tg_message.from_user.last_name}")

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
                # if self.trigger_required:
                result = self.remove_trigger_word(word)
                if result != "blank":
                    # self.trigger_start()
                    self.handle(result)
                # else:
                #     self.handle(word)

    # def trigger_start(self):
    #     self.trigger_required = False
    #     thread = threading.Timer(30, self.trigger_count)
    #     thread.start()
    #
    # def trigger_count(self):
    #     self.trigger_required = True

    def remove_trigger_word(self, request):
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
            tts.say(random.choice(self.answers.get("default")))
        else:
            total = self._multihandle(request)
            if len(total) == 1:
                result = self.tree.find_command(total[0])
                print(result)
                if result:
                    res = list(result)
                    res.extend([total[0], request])
                    self._synth_handle(res)
            elif len(total) > 1:
                tts.say(random.choice(self.answers.get("confirmative")))
                for command in total:
                    result = self.tree.find_command(command)
                    if result:
                        res = list(result)
                        res.extend([command, request])
                        self._just_handle(res)
            elif not total:
                if self.config.get("gpt"):
                    answer = self.answer_gpt(request)
                    tts.say(answer)

    def _synth_handle(self, request):
        @self._synthesis_dec(request[2])
        def do():
            self._just_handle(request)

        do()

    def _just_handle(self, request):
        if request[0]:
            thread = threading.Thread(target=getattr(self.find_arch(request[0]), request[0]),
                                      kwargs={"parameters": request[1], "command": request[3],
                                              "request": request[4]})
            thread.start()

    def find_arch(self, name):
        for module in self.architecture:
            members = inspect.getmembers(module)
            functions = [member[0] for member in members if inspect.isfunction(member[1])]
            if name in functions:
                return module
        if name in dir(self):
            return self


    def _synthesis_dec(self, to_say):
        def decorator(func):
            def wrapper():
                if to_say:
                    tts.say(random.choice([*to_say, random.choice(self.answers.get("confirmative"))]))
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
                if word in ["найди", "найти", "запиши", "скажи", "ответь"]:
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

    def combination(self, **kwargs):
        for command in kwargs["parameters"]["combination"]:
            getattr(self.find_arch(command.get("name")), command.get("name"))(parameters=command["parameters"])

    def read_tg(self, **kwargs):
        if half_hour_passed(self.last_tg_message.date):
            tts.say(
                random.choice(["В последний час новых сообщений не поступало, сэр", "Список входящих пуст, сэр"]))
        else:
            if self.last_tg_message.voice:
                while True:
                    if os.path.exists(f"{CWD}/data/connections/telegram/downloads/audio.ogg"):
                        playsound(f"{CWD}/data/connections/telegram/downloads/audio.ogg")
                        break
                    time.sleep(0.5)
            else:
                tts.say(
                    f"... {self.last_tg_message.from_user.first_name} {self.last_tg_message.from_user.last_name or ''} пишет. {self.last_tg_message.text}",
                    prosody=89)

    def reply_tg(self, **kwargs):
        reply = " ".join(kwargs["command"][1:])
        self.core_pipe.send((reply, self.last_tg_message.chat.id))

    def send_tg(self, **kwargs):
        reply = " ".join(kwargs["command"][2:])
        self.core_pipe.send((reply, kwargs.get("parameters").get("id")))

    def neuro_switch(self, **kwargs):
        if kwargs["parameters"]["way"] == "on":
            self.config["gpt"] = True
            self.stt.current = self.stt.recognizer
        if kwargs["parameters"]["way"] == "off":
            self.config["gpt"] = False
        config_dump(f"{CWD}/config.json", self.config)

    def stopwatch(self, **kwargs):
        if kwargs["parameters"]["way"] == "start":
            self.stopwatch_start = datetime.datetime.now()
            self.stopwatch_enabled = True
        if kwargs["parameters"]["way"] == "stop" and self.stopwatch_start and self.stopwatch_enabled:
            self.stopwatch_enabled = False
            self.stopwatch_end = datetime.datetime.now()
            passed = self.stopwatch_end - self.stopwatch_start
            hour, minute, second = passed.seconds // 3600, (passed.seconds % 3600) // 60, passed.seconds % 60
            tts.say(
                f"Прошло {num2words(hour, lang='ru') if hour != 0 else ''} {'час' + get_hour_suffix(hour) if hour != 0 else ''}, {num2words(minute, lang='ru') if minute != 0 else ''} {'минут' + get_minute_suffix(minute) if minute != 0 else ''} {num2words(second, lang='ru') if second != 0 else ''} {'секунд' + get_second_suffix(second) if second != 0 else ''}")
        elif kwargs["parameters"]["way"] == "stop" and not self.stopwatch_enabled:
            tts.say(random.choice(["Секундомер не запущен", "Секундомер выключен"]))

    @staticmethod
    def end(**kwargs):
        time.sleep(3)
        os.kill(os.getpid(), signal.SIGINT)

    def clear_neuro(self, **kwargs):
        self.gpt_history = []

    @staticmethod
    def wait(**kwargs):
        time.sleep(kwargs["parameters"]["time"])

    def repeat(self, **kwargs):
        self.handle(self.message_history[-2])





