import re
from num2words import num2words
from translate import Translator


def extract_number(input_string):
    match = re.search(r'\d+', input_string)
    if match:
        return int(match.group())
    else:
        return None


def kelvin_to_c(k):
    return int(k - 273.15)


def get_part_of_day(hour):
    if 3 <= hour < 12:
        return "доброе утро"
    elif 12 <= hour < 16:
        return "доброго дня"
    elif 16 <= hour < 23:
        return "доброго вечера"
    else:
        return "доброй ночи"


def get_hour_suffix(hour):
    if 11 < hour < 20:
        return "ов"
    else:
        last_digit = hour % 10
        if last_digit == 1:
            return ""
        elif 1 < last_digit < 5:
            return "а"
        else:
            return "ов"


def get_minute_suffix(minutes):
    if 10 < minutes < 20:
        return ""
    else:
        last_digit = minutes % 10
        if last_digit == 1:
            return "а"
        elif 1 < last_digit < 5:
            return "ы"
        else:
            return ""


def get_second_suffix(seconds):
    if 10 < seconds < 20:
        return ""
    else:
        last_digit = seconds % 10
        if last_digit == 1:
            return "а"
        elif 1 < last_digit < 5:
            return "ы"
        else:
            return ""


def get_currency_suffix(amount):
    last_two_digits = amount % 100
    last_digit = amount % 10

    if 10 < last_two_digits < 20:
        return "ей"
    elif last_digit == 1:
        return "ь"
    elif 1 < last_digit < 5:
        return "я"
    else:
        return "ей"


def get_degree_suffix(degrees):
    last_digit = degrees % 10

    if 10 < degrees < 20:
        return "ов"
    elif last_digit == 1:
        return ""
    elif 1 < last_digit < 5:
        return "а"
    else:
        return "ов"


def find_numbers_in_string(text: str):
    # Using regular expression to find all numbers in the string
    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", text)

    # Converting the numbers from string to their respective data types
    numbers = [int(num) if num.isdigit() else float(num) for num in numbers]

    for number in numbers:
        word = num2words(int(number), lang="ru")
        text = text.replace(str(number), word)

    return text


#
# print(find_numbers_in_string("Черепахи могут жить до 150 лет"))

def extract_english_words(input_string):
    # Define a regular expression pattern to match English words
    pattern = re.compile(r'\b[a-zA-Z]+\b')

    # Use findall to extract all matches
    english_words = pattern.findall(input_string)

    return english_words
