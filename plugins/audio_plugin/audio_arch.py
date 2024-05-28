import os

from utils.text import *
from utils.sys import *

from audio import tts

# Environment variables setup
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame.mixer

pygame.mixer.init()


def say_same(**kwargs):
    tts.say(" ".join(kwargs["command"][1:]))


def play_audio(**kwargs):
    path = kwargs.get("parameters").get("path")
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()


def kill_audio(**kwargs):
    pygame.mixer.music.stop()


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
