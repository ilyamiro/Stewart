from pyrogram import Client, filters
import json
import os

CWD = os.path.dirname(os.path.abspath(__file__))

with open(f"{CWD}/private.json", "r", encoding="utf-8") as file:
    tg_config = json.load(file)

app_tg = Client("stewart_monitor", tg_config.get("id"), tg_config.get("hash"))


@app_tg.on_message(filters.private)
def handle_new_message(client, message):
    # Get the user's first name and last name
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name or ""  # If last_name is None, use an empty string

    # Print a message
    print(f"You got a message from {first_name} {last_name}: '{message.text}'")


# Run the client until it's stopped
app_tg.run()