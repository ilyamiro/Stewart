from pyrogram import Client, filters
import json
import os
from datetime import datetime, timedelta
import threading

CWD = os.path.dirname(os.path.abspath(__file__))


def start_bot(child_pipe):
    with open(f"{CWD}/private.json", "r", encoding="utf-8") as file:
        tg_config = json.load(file)

    app = Client("stewart_monitor", tg_config.get("id"), tg_config.get("hash"))

    def recieve_answer(conn):
        while True:
            text, _id = conn.recv()
            app.send_message(chat_id=int(_id), text=text)

    thread = threading.Thread(target=recieve_answer, args=(child_pipe,))
    thread.start()

    @app.on_message(filters.private & (~filters.me))
    def text_message(client, message):
        current_time = datetime.now()

        if not not message.voice:
            client.download_media(message=message.voice, file_name=f"{CWD}/downloads/audio.ogg", block=False)

        try:
            previous_message = next(client.get_chat_history(chat_id=message.chat.id, limit=1, offset_id=message.id,))
        except StopIteration:
            # The generator is empty, so there is no previous message
            previous_message = None

        if previous_message:
            if (current_time - previous_message.date) > timedelta(minutes=5) and previous_message.from_user.id == message.from_user.id:
                child_pipe.send(message)
        else:
            child_pipe.send(message)

    app.run()
