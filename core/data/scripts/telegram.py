from pyrogram import Client, filters
import json
import os
from datetime import datetime, timedelta

CWD = os.path.dirname(os.path.abspath(__file__))


def start_bot(child_pipe):
    with open(f"{CWD}/private.json", "r", encoding="utf-8") as file:
        tg_config = json.load(file)

    app = Client("stewart_monitor", tg_config.get("id"), tg_config.get("hash"))

    @app.on_message(filters.private & filters.text)
    def handle_new_message(client, message):
        current_time = datetime.now()

        try:
            previous_message = next(client.get_chat_history(chat_id=message.chat.id, limit=1, offset_id=message.id))
        except StopIteration:
            # The generator is empty, so there is no previous message
            previous_message = None

        if previous_message:
            if (current_time - previous_message.date) > timedelta(minutes=5) and previous_message.from_user.id == message.from_user.id:
                child_pipe.send(message)
        else:
            child_pipe.send(message)

    # Run the client until it's stopped
    app.run()
