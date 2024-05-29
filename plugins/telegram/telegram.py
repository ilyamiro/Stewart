# Standard library imports
import os
import json
import threading
import multiprocessing

from datetime import datetime, timedelta

# Third-party imports
from pyrogram import Client, filters
from playsound import playsound

# Local/project-specific imports
from audio import tts
from utils.sys import *
from utils.some import *

CWD = os.path.dirname(os.path.abspath(__file__))


class TelegramMonitor:
    def __init__(self):
        self.last_tg_message = None
        self.app = None
        self.tg_config = self.load_tg_config()

    @staticmethod
    def load_tg_config():
        with open(f"{CWD}/private.json", "r", encoding="utf-8") as file:
            return json.load(file)

    def start_bot(self):
        self.app = Client("stewart_monitor", self.tg_config.get("id"), self.tg_config.get("hash"))

        @self.app.on_message(filters.private & (~filters.me))
        def text_message(client, message):
            current_time = datetime.now()

            if not not message.voice:
                client.download_media(message=message.voice, file_name=f"{CWD}/downloads/audio.ogg", block=False)

            try:
                previous_message = next(
                    client.get_chat_history(chat_id=message.chat.id, limit=1, offset_id=message.id, ))
            except StopIteration:
                previous_message = None

            if previous_message:
                if (current_time - previous_message.date) > timedelta(
                        minutes=5) and previous_message.from_user.id == message.from_user.id:
                    self.last_tg_message = message
                    self.say()
            else:
                self.last_tg_message = message
                self.say()

        self.app.run()

    def send(self, *msg):
        text, _id = msg
        self.app.send_message(chat_id=int(_id), text=text)

    def say(self):
        tts.say(
            f"У вас одно новое сообщение от {self.last_tg_message.from_user.first_name} {self.last_tg_message.from_user.last_name}")


monitor = TelegramMonitor()


def __get_telegram__():
    return monitor.start_bot


def read_tg(**_):
    if half_hour_passed(monitor.last_tg_message.date):
        tts.say(
            random.choice(["В последний час новых сообщений не поступало, сэр", "Список входящих пуст, сэр"]))
    else:
        if monitor.last_tg_message.voice:
            while True:
                if os.path.exists(f"{CWD}/downloads/audio.ogg"):
                    playsound(f"{CWD}/downloads/audio.ogg")
                    break
                time.sleep(0.5)
        else:
            tts.say(
                f"... {monitor.last_tg_message.from_user.first_name} {monitor.last_tg_message.from_user.last_name or ''} пишет. {monitor.last_tg_message.text}",
                prosody=90)


def reply_tg(**kwargs):
    reply = " ".join(kwargs["command"][1:])
    monitor.send((reply, monitor.last_tg_message.chat.id))


def send_tg(**kwargs):
    reply = " ".join(kwargs["command"][2:])
    monitor.send((reply, kwargs.get("parameters").get("id")))
