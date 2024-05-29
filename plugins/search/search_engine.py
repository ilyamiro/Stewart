from utils.text import *
from utils.sys import *

import subprocess
import urllib
import requests
import re
import g4f

from bs4 import BeautifulSoup
import webbrowser

from audio import tts


def find_link(self, **kwargs):
    search = "+".join(kwargs["command"][2:])

    url = "https://html.duckduckgo.com/html/?"
    params = {'q': search}

    tts.say(f"Вот, что мне удалось найти по запросу {search}")

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
    tts.say("Ищу источники информации, сэр")
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
            tts.say("Нашел источник, анализирую")
            answer = g4f.ChatCompletion.create(
                messages=[{"role": "user",
                           "content": f"Коротко просуммируй все сказанное далее: {file.read().split()[:90]}"}],
                provider=g4f.Provider.You,
                stream=False,
                model=g4f.models.default
            )
            tts.say(numbers_to_strings(answer))


def find_video(self, **kwargs):
    search = "+".join(kwargs["command"][2:])
    html = urllib.request.urlopen(f"https://www.youtube.com/results?search_query={quote(search)}")
    video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
    if video_ids:
        webbrowser.open("https://www.youtube.com/watch?v=" + video_ids[0], autoraise=True)
    else:
        tts.say("Я не смог найти подходящее видео, или произошла ошибка, сэр")


def find(self, **kwargs):
    to_find = " ".join(kwargs["command"][1:])

    def _find(query, site):
        tts.say("Вот что мне удалось найти по запросу" + to_find)
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
